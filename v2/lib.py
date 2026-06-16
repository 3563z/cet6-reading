"""
CET-6 Pipeline 共享库 v2
统一 HTML DATA 解析、答案验证、质量检查 — 所有脚本共用，避免重复造轮子。
"""
import json, re, os, sys
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Any

# ── 配置 ──
CONFIG = {
    'listening_targets': {
        'news':              (180, 220),
        'long_conversation': (260, 320),
        'passage':           (220, 280),
        'lecture':           (380, 450),
    },
    'reading_targets': {
        'tech':   (350, 450),
        'social': (350, 450),
        'long':   (500, 650),
    },
    'option_limits': {'listening': 8, 'reading': 18},
    'answer_range': (20, 35),       # 每字母百分比范围
    'overlap_max': 50,              # 正确项-原文最大重叠率
    'translation_cn': (180, 200),   # 中文字数
    'translation_en': (130, 160),   # 英文词数
    'writing_words':   (150, 200),
    'writing_paras':   3,
    'detail_max':      3,           # 每篇最多细节题
    'type_min':        3,           # 每篇最少题型种类
    'min_paras':       4,           # 阅读最少段落
    'template_patterns': [
        (r'has sparked (an ongoing|a heated) debate',     'has sparked debate'),
        (r'On the one hand.*On the other hand',             'On the one hand...'),
        (r'lies not in.*but in',                             'lies not in...but in'),
        (r'While both approaches have their merits',        'both have their merits'),
        (r'In (my view|conclusion), the future of.*lies in', 'future of...lies in'),
        (r'has (become|emerged as) a (hotly|widely) debated', 'become debated'),
    ],
    'voices': {
        'default': 'en-US-GuyNeural',
        'male':    'en-US-GuyNeural',
        'female':  'en-US-MichelleNeural',
    },
    'project_root': r'C:\Users\30943\cet6-daily',
    'audio_out_dir': 'repo_push/daily/audio',
    'SECTIONS': [
        ('news',              '{date}_1.mp3', 'default',  False),
        ('long_conversation', '{date}_2.mp3', None,       True),
        ('passage',           '{date}_3.mp3', 'default',  False),
        ('lecture',           '{date}_4.mp3', 'default',  False),
    ],
}


# ═══════════════════════════════════════════
# 1. HTML DATA 解析（用锚点定位，避注释）
# ═══════════════════════════════════════════

def parse_html(filepath: str) -> str:
    """读取 HTML 文件"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()


def extract_data(html: str) -> Dict:
    """
    从 HTML 模板提取 DATA 对象。
    用 `// ========== DATA ==========` 锚点定位，避注释陷阱。
    """
    marker = '// ========== DATA =========='
    mp = html.find(marker)
    if mp == -1:
        raise ValueError("找不到 DATA 锚点 // ========== DATA ==========")

    var_pos = html.find('var DATA = {', mp)
    if var_pos == -1:
        raise ValueError("锚点后找不到 var DATA = {")

    # 找匹配的 };
    brace_start = html.index('{', var_pos)
    depth = 0
    for i in range(brace_start, len(html)):
        if html[i] == '{':
            depth += 1
        elif html[i] == '}':
            depth -= 1
            if depth == 0:
                brace_end = i
                break
    else:
        raise ValueError("DATA 对象未闭合")

    json_str = html[brace_start:brace_end + 1]

    # 判断是否需要 JS→JSON 转换：看第二个非空行是否已带引号键
    lines = [l.strip() for l in json_str.split('\n') if l.strip() and l.strip() != '{']
    is_js_object = lines and not lines[0].startswith('"')

    if is_js_object:
        # JS 对象 → JSON: 键名加引号（模板场景）
        json_str = re.sub(r'(?m)(\s*)(\w+)(\s*):', r'\1"\2"\3:', json_str)
        # 去掉尾逗号
        json_str = re.sub(r',(\s*})', r'\1', json_str)
        # 单引号 → 双引号
        json_str = json_str.replace("'", '"')

    return json.loads(json_str)


def extract_section(html: str, key: str) -> tuple:
    """
    从 HTML 提取指定听力 section 的 (script, questions)。
    返回 (script:str|None, questions:list|None)
    """
    data = extract_data(html)
    lc = data.get('listening', {})
    section = lc.get(key)

    if not section:
        return None, None

    return section.get('script', ''), section.get('questions', [])

# ═══════════════════════════════════════════
# 2. 文本工具
# ═══════════════════════════════════════════

def word_count(text: str) -> int:
    """英文词数（滤标点后统计）"""
    cleaned = re.sub(r'[^\w\s]', ' ', text)
    return len(cleaned.split())


def char_count_cn(text: str) -> int:
    """中文字符数（去标点/空白）"""
    return len(re.sub(r'[\s，。、；：！？""''（）—…《》【】·,\.;:!?\-\"\'\(\)\[\]]', '', text))


def overlap_ratio(correct_opt: str, source_text: str) -> float:
    """正确选项与原文的词语重叠率（%）"""
    cw = set(correct_opt.lower().split())
    sw = set(source_text.lower().split())
    if not cw:
        return 0
    return len(cw & sw) / len(cw) * 100


# ═══════════════════════════════════════════
# 3. 答案验证
# ═══════════════════════════════════════════

def extract_answers(html: str) -> list:
    """正则提取所有 answer 字段"""
    answers = re.findall(r'["\']answer["\']\s*:\s*["\'](.)["\']', html)
    return answers


def check_distribution(answers: list,
                       section_size: int = 5,
                       global_range: tuple = (20, 35)) -> dict:
    """检查答案分布，返回详细报告"""
    total = len(answers)
    dist = Counter(answers)
    result = {
        'total': total,
        'distribution': {l: dist.get(l, 0) for l in 'ABCD'},
        'global_ok': True,
    }

    # 全局检查
    for letter in 'ABCD':
        count = dist.get(letter, 0)
        pct = count / total * 100 if total else 0
        lo, hi = global_range
        if not (lo <= pct <= hi):
            result['global_ok'] = False
        result.setdefault('details', {})[letter] = {
            'count': count,
            'pct': round(pct, 1),
            'ok': lo <= pct <= hi,
        }

    # 逐 section 检查
    sections = total // section_size
    sec_results = []
    for s in range(sections):
        sec_answers = answers[s * section_size:(s + 1) * section_size]
        sec_dist = Counter(sec_answers)
        ok = all(1 <= sec_dist.get(l, 0) <= 2 for l in 'ABCD')
        sec_results.append({
            'section': s + 1,
            'distribution': {l: sec_dist.get(l, 0) for l in 'ABCD'},
            'ok': ok,
        })

    result['sections'] = sec_results
    result['all_sections_ok'] = all(s['ok'] for s in sec_results)

    return result


# ═══════════════════════════════════════════
# 4. 题目分类
# ═══════════════════════════════════════════

def classify_question(text: str) -> str:
    """分类题型"""
    t = text.lower()
    patterns = [
        (r'\b(mainly|primarily|central|theme|argument|purpose|title)\b', '主旨'),
        (r'\b(infer|suggest|imply|conclude|indicate)\b',                    '推断'),
        (r'\b(closest|refer|meaning|mean|word|phrase)\b',                   '词汇'),
        (r'\b(attitude|tone|feel|view|think)\b',                            '态度'),
        (r'\b(why|because|reason|cause)\b',                                 '因果'),
    ]
    for pat, cat in patterns:
        if re.search(pat, t):
            return cat
    return '细节'


# ═══════════════════════════════════════════
# 5. 质量检查器
# ═══════════════════════════════════════════

QualityIssue = dict  # {'section': str, 'item': str, 'detail': str, 'severity': str}


def check_all(html_path: str) -> List[QualityIssue]:
    """运行全部质量检查，返回 issues 列表"""
    html = parse_html(html_path)
    data = extract_data(html)
    issues = []

    # ── 听力篇 ──
    lc = data.get('listening', {})
    for key, info in lc.items():
        if not info:
            continue
        script = info.get('script', '')
        questions = info.get('questions', [])
        words = word_count(script)

        # 篇幅
        lo, hi = CONFIG['listening_targets'].get(key, (0, 9999))
        if not (lo <= words <= hi):
            issues.append({
                'section': f'listening.{key}',
                'item': '篇幅',
                'detail': f'{words} 词 (期望 {lo}-{hi})',
                'severity': 'warn'
            })

        # 题文同序标注
        if not re.search(r'\[Q[1-5]\]', script):
            issues.append({
                'section': f'listening.{key}',
                'item': '题文同序标注',
                'detail': '缺少 [Q1]...[Q5] 标记',
                'severity': 'error'
            })

        # 选项长度 + 重叠率
        for i, q in enumerate(questions):
            for l in 'ABCD':
                ow = word_count(q.get(l, ''))
                if ow > CONFIG['option_limits']['listening']:
                    issues.append({
                        'section': f'listening.{key}',
                        'item': f'Q{i+1}{l}选项长度',
                        'detail': f'{ow} 词 (上限 {CONFIG["option_limits"]["listening"]})',
                        'severity': 'error'
                    })

            correct = q.get(q.get('answer', ''), '')
            ol = overlap_ratio(correct, script)
            grade = overlap_grade(ol)
            if ol > CONFIG['overlap_max']:
                issues.append({
                    'section': f'listening.{key}',
                    'item': f'Q{i+1}重叠率',
                    'detail': f'{ol:.0f}% [{grade}] (上限 {CONFIG["overlap_max"]}%)',
                    'severity': 'error'
                })
            elif ol > 30:
                issues.append({
                    'section': f'listening.{key}',
                    'item': f'Q{i+1}重叠率',
                    'detail': f'{ol:.0f}% [{grade}]',
                    'severity': 'info'
                })

        # 题内平行结构
        p_results = check_parallel_structure(questions)
        for pr in p_results:
            if not pr['ok']:
                struct_str = ', '.join(f'{l}:{s}' for l, s in pr['structs'].items())
                issues.append({
                    'section': f'listening.{key}',
                    'item': f'Q{pr["q_index"]}题内平行',
                    'detail': f'结构不一致 → {struct_str}',
                    'severity': 'error'
                })

    # ── 阅读篇 ──
    rc = data.get('reading', {})
    for key, info in rc.items():
        if not info:
            continue
        text = info.get('text', '')
        questions = info.get('questions', [])
        words = word_count(text)
        paras = len(re.findall(r'\n\n+', text)) + 1

        lo, hi = CONFIG['reading_targets'].get(key, (0, 9999))
        if not (lo <= words <= hi):
            issues.append({
                'section': f'reading.{key}',
                'item': '篇幅',
                'detail': f'{words} 词 (期望 {lo}-{hi})',
                'severity': 'warn'
            })

        if paras < CONFIG['min_paras']:
            issues.append({
                'section': f'reading.{key}',
                'item': '段落数',
                'detail': f'仅 {paras} 段 (需 ≥{CONFIG["min_paras"]})',
                'severity': 'warn'
            })

        # 题型
        types = [classify_question(q.get('q', '')) for q in questions]
        unique = set(types)
        detail_n = types.count('细节')
        if len(unique) < CONFIG['type_min']:
            issues.append({
                'section': f'reading.{key}',
                'item': '题型多样性',
                'detail': f'仅 {len(unique)} 种 {unique} (需 ≥{CONFIG["type_min"]})',
                'severity': 'error'
            })
        if detail_n > CONFIG['detail_max']:
            issues.append({
                'section': f'reading.{key}',
                'item': '细节题过多',
                'detail': f'{detail_n} 题 (上限 {CONFIG["detail_max"]})',
                'severity': 'warn'
            })

        # 选项长度 + 重叠率
        for i, q in enumerate(questions):
            for l in 'ABCD':
                ow = word_count(q.get(l, ''))
                if ow > CONFIG['option_limits']['reading']:
                    issues.append({
                        'section': f'reading.{key}',
                        'item': f'Q{i+1}{l}选项长度',
                        'detail': f'{ow} 词 (上限 {CONFIG["option_limits"]["reading"]})',
                        'severity': 'error'
                    })
            correct = q.get(q.get('answer', ''), '')
            ol = overlap_ratio(correct, text)
            grade = overlap_grade(ol)
            if ol > CONFIG['overlap_max']:
                issues.append({
                    'section': f'reading.{key}',
                    'item': f'Q{i+1}重叠率',
                    'detail': f'{ol:.0f}% [{grade}] (上限 {CONFIG["overlap_max"]}%)',
                    'severity': 'error'
                })
            elif ol > 30:
                issues.append({
                    'section': f'reading.{key}',
                    'item': f'Q{i+1}重叠率',
                    'detail': f'{ol:.0f}% [{grade}]',
                    'severity': 'info'
                })

        # 段落覆盖检查
        pc = check_paragraph_coverage(text, questions)
        if not pc['ok']:
            issues.append({
                'section': f'reading.{key}',
                'item': '答案段落覆盖',
                'detail': f'仅覆盖 {pc["covered"]}/{pc["total"]} 段 (需 ≥4)',
                'severity': 'info'
            })

        # 题内平行结构
        p_results = check_parallel_structure(questions)
        for pr in p_results:
            if not pr['ok']:
                struct_str = ', '.join(f'{l}:{s}' for l, s in pr['structs'].items())
                issues.append({
                    'section': f'reading.{key}',
                    'item': f'Q{pr["q_index"]}题内平行',
                    'detail': f'结构不一致 → {struct_str}',
                    'severity': 'error'
                })

    # ── 翻译 ──
    tr = data.get('translation', {})
    cn = tr.get('cn', '')
    en = tr.get('reference', '')
    cn_chars = char_count_cn(cn)
    en_words = word_count(en)
    lo_cn, hi_cn = CONFIG['translation_cn']
    lo_en, hi_en = CONFIG['translation_en']
    if not (lo_cn <= cn_chars <= hi_cn):
        issues.append({
            'section': 'translation',
            'item': '中文字数',
            'detail': f'{cn_chars} 字 (期望 {lo_cn}-{hi_cn})',
            'severity': 'error'
        })
    if not (lo_en <= en_words <= hi_en):
        issues.append({
            'section': 'translation',
            'item': '英文词数',
            'detail': f'{en_words} 词 (期望 {lo_en}-{hi_en})',
            'severity': 'error'
        })

    # ── 作文 ──
    wr = data.get('writing', {})
    model = wr.get('model', '')
    mw = word_count(model)
    mparas = len(re.findall(r'\n\n+', model)) + 1
    lo_wr, hi_wr = CONFIG['writing_words']
    if not (lo_wr <= mw <= hi_wr):
        issues.append({
            'section': 'writing',
            'item': '词数',
            'detail': f'{mw} 词 (期望 {lo_wr}-{hi_wr})',
            'severity': 'error'
        })
    if mparas < CONFIG['writing_paras']:
        issues.append({
            'section': 'writing',
            'item': '段落',
            'detail': f'仅 {mparas} 段 (需 ≥{CONFIG["writing_paras"]})',
            'severity': 'warn'
        })
    for pat, name in CONFIG['template_patterns']:
        if re.search(pat, model, re.DOTALL | re.IGNORECASE):
            issues.append({
                'section': 'writing',
                'item': '模板句式',
                'detail': f"检测到 '{name}'",
                'severity': 'error'
            })

    return issues


# ═══════════════════════════════════════════
# 6. 评分
# ═══════════════════════════════════════════

QualityIssue = dict  # {'section': str, 'item': str, 'detail': str, 'severity': str}


def score(issues: List[QualityIssue]) -> dict:
    """100 分制评分（对齐命题规则 §7）：听力25+阅读25+翻译25+作文25"""
    errors_by_section = defaultdict(int)
    warns_by_section = defaultdict(int)

    for iss in issues:
        sec = iss['section'].split('.')[0]
        if iss['severity'] == 'error':
            errors_by_section[sec] += 1
        elif iss['severity'] == 'warn':
            warns_by_section[sec] += 1
        # 'info' level does not affect scoring

    def section_score(errors, warns):
        base = 25 - errors * 3 - warns * 1
        return max(0, min(25, base))

    scores = {
        'listening':    section_score(errors_by_section.get('listening', 0),
                                      warns_by_section.get('listening', 0)),
        'reading':      section_score(errors_by_section.get('reading', 0),
                                      warns_by_section.get('reading', 0)),
        'translation':  section_score(errors_by_section.get('translation', 0),
                                      warns_by_section.get('translation', 0)),
        'writing':      section_score(errors_by_section.get('writing', 0),
                                      warns_by_section.get('writing', 0)),
    }
    total = sum(scores.values())
    grade = '优' if total >= 95 else ('良' if total >= 88 else '不合格')

    return {
        'scores': scores,
        'total': total,
        'grade': grade,
        'pass': total >= 88,
    }


def per_section_score(html_path: str) -> dict:
    """逐篇评分（对应规则 §8 工作流 3a-3f），返回每 section 独立评分"""
    html = parse_html(html_path)
    data = extract_data(html)
    all_issues = check_all(html_path)

    results = {}

    # ── 听力逐篇 ──
    for key in ['news', 'long_conversation', 'passage', 'lecture']:
        section = data.get('listening', {}).get(key)
        if not section:
            continue
        sec_issues = [i for i in all_issues if i['section'].startswith(f'listening.{key}')]
        errors = sum(1 for i in sec_issues if i['severity'] == 'error')
        warns = sum(1 for i in sec_issues if i['severity'] == 'warn')
        s = max(0, 25 - errors * 5 - warns * 2)
        results[f'listening.{key}'] = {'score': s, 'errors': errors, 'warns': warns, 'pass': s >= 20}

    # ── 阅读逐篇 ──
    for key in ['tech', 'social', 'long']:
        section = data.get('reading', {}).get(key)
        if not section:
            continue
        sec_issues = [i for i in all_issues if i['section'].startswith(f'reading.{key}')]
        errors = sum(1 for i in sec_issues if i['severity'] == 'error')
        warns = sum(1 for i in sec_issues if i['severity'] == 'warn')
        s = max(0, 25 - errors * 5 - warns * 2)
        results[f'reading.{key}'] = {'score': s, 'errors': errors, 'warns': warns, 'pass': s >= 20}

    # ── 翻译 ──
    tr_issues = [i for i in all_issues if i['section'] == 'translation']
    tr_errors = sum(1 for i in tr_issues if i['severity'] == 'error')
    tr_warns = sum(1 for i in tr_issues if i['severity'] == 'warn')
    tr_score = max(0, 25 - tr_errors * 5 - tr_warns * 2)
    results['translation'] = {'score': tr_score, 'errors': tr_errors, 'warns': tr_warns, 'pass': tr_score >= 20}

    # ── 作文 ──
    wr_issues = [i for i in all_issues if i['section'] == 'writing']
    wr_errors = sum(1 for i in wr_issues if i['severity'] == 'error')
    wr_warns = sum(1 for i in wr_issues if i['severity'] == 'warn')
    wr_score = max(0, 25 - wr_errors * 5 - wr_warns * 2)
    results['writing'] = {'score': wr_score, 'errors': wr_errors, 'warns': wr_warns, 'pass': wr_score >= 20}

    return results


# ═══════════════════════════════════════════
# 7. 题内平行结构检测
# ═══════════════════════════════════════════

import re as _re

_STRUCT_PATTERNS = {
    'noun_phrase': r'^(A|An|The)\s+\w+(\s+\w+){1,6}$',
    'infinitive':  r'^To\s+\w+(\s+\w+)+$',
    'gerund':      r'^\w+ing\s+',
    'full_sentence': r'^(It|They|The|This|That|These|Those|He|She|We|A|An)\s+\w+\s+(is|are|was|were|has|have|had|will|would|can|could|may|might|should)\s+',
    'because_clause': r'^Because\s+',
    'that_clause':    r'^That\s+',
    'wh_clause':      r'^(What|Why|How|When|Where|Who)\s+',
}


def detect_option_structure(option_text: str) -> str:
    """检测单个选项的语法结构类型"""
    t = option_text.strip()
    if not t:
        return 'empty'
    for name, pat in _STRUCT_PATTERNS.items():
        if _re.match(pat, t):
            return name
    return 'other'


def check_parallel_structure(questions: list) -> list:
    """
    检查题内选项结构是否平行，返回结构不一致的题目列表。
    返回 [{'q_index': i, 'structs': {'A':'noun_phrase',...}, 'ok': bool}]
    """
    results = []
    for i, q in enumerate(questions):
        structs = {}
        for l in 'ABCD':
            opt = q.get(l, '')
            structs[l] = detect_option_structure(opt)

        # 4个选项结构是否一致
        unique = set(structs.values())
        ok = len(unique) <= 2 or ('other' not in unique and 'empty' not in unique)

        results.append({
            'q_index': i + 1,
            'structs': structs,
            'ok': ok,
        })

    return results


def check_paragraph_coverage(text: str, questions: list) -> dict:
    """
    检查答案覆盖的段落数。返回 {'covered': int, 'total': int, 'ok': bool}
    前提：questions 按题文同序排列，text 用空行分隔段落。
    """
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    total_paras = len(paragraphs)
    if total_paras < 2 or len(questions) == 0:
        return {'covered': total_paras, 'total': total_paras, 'ok': True}

    # 粗略定位：每道题的答案句可能在哪段
    covered = set()
    for q in questions:
        answer = q.get(q.get('answer', ''), '')
        if not answer:
            continue
        # 找答案选项文本在原文中的近似位置
        for pi, para in enumerate(paragraphs):
            # 检查是否有显著词重叠
            ans_words = set(answer.lower().split()) - {'a', 'an', 'the', 'is', 'are', 'of', 'in', 'to', 'for', 'and', 'or', 'that', 'this', 'it'}
            para_words = set(para.lower().split())
            overlap = len(ans_words & para_words)
            if overlap >= 2:
                covered.add(pi)
                break

    ok = len(covered) >= min(4, total_paras)
    return {
        'covered': len(covered),
        'total': total_paras,
        'ok': ok,
    }


# ═══════════════════════════════════════════
# 8. 重叠率分级
# ═══════════════════════════════════════════

def overlap_grade(ratio: float) -> str:
    """重叠率分级（对应 §1.3）"""
    if ratio <= 30:
        return '优秀'
    elif ratio <= 50:
        return '可接受'
    else:
        return '超标'
