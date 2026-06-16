import json

with open('C:/Users/30943/cet6-daily/sprint_data.json', 'r', encoding='utf-8') as f:
    D = json.load(f)

# EXPLAIN data now lives in sprint_data.json
LEC_EXPLAIN = {i: lec['explain'] for i, lec in enumerate(D['lectures'])}
CLOZE_EXPLAIN = {i: cs['explain'] for i, cs in enumerate(D['cloze_sets'])}

# ============ BUILD HTML SECTIONS ============

# Build cloze HTML
cloze_html = ""
for ci, cs in enumerate(D['cloze_sets']):
    text = cs['text']
    for i in range(1, 11):
        text = text.replace(f'({i})', f'<span class="blank" id="c{ci}_{i}">({i})____</span>')
    
    wb = ''.join(f'<span class="word-chip" data-set="{ci}" data-word="{w["word"]}" onclick="pickWord(\'{ci}\',\'{w["word"]}\',this)">{w["word"]}</span>' for w in cs['word_bank'])
    
    cloze_html += f'''
    <div class="section">
      <h3>📖 {cs["title"]}</h3>
      <p class="hint">先标注每个空需要的词性(n/v/adj/adv)，再选词。点击词汇→点击空格填入，双击空格撤销。</p>
      <div class="word-bank">{wb}</div>
      <div class="reading-text cloze-text">{text}</div>
      <div style="margin-top:8px"><span class="hint">当前选择：</span><span id="pick-ci{ci}" style="color:var(--accent);font-weight:600">无</span></div>
      <button class="btn-sm" onclick="checkCloze({ci}, {json.dumps(cs['answers'], ensure_ascii=False)})">✅ 检查答案</button>
      <div class="explain" id="clozenote-{ci}"></div>
    </div>'''

# Build lecture HTML
lec_html = ""
for li, lec in enumerate(D['lectures']):
    q_html = ""
    for i, q in enumerate(lec['questions']):
        opts = ''.join(f'<label><input type="radio" name="l{li}_{i}" value="{l}"> {l}. {q[l]}</label>' for l in 'ABCD')
        q_html += f'<div class="q-item"><p class="q-num">{i+1}.</p>{opts}</div>'
    
    lec_html += f'''
    <div class="section">
      <h3>🎧 {lec["title"]}</h3>
      <p class="hint">信号词位置：{lec["signals"]}</p>
      <audio controls style="width:100%;margin:8px 0" preload="none">
        <source src="{lec["audio"]}" type="audio/mpeg">
      </audio>
      <details class="script-box"><summary>📄 原文（做完后对照）</summary>
      <pre class="script-text" style="max-height:300px;overflow-y:auto">{lec["script"]}</pre></details>
      <div class="q-list">{q_html}</div>
      <button class="btn-sm" onclick="checkLec({li}, {json.dumps([q['answer'] for q in lec['questions']], ensure_ascii=False)})">✅ 检查答案</button>
      <div class="explain" id="lecnote-{li}"></div>
    </div>'''

# Spelling table
spell_rows = ''.join(f'<tr><td class="wrong-word">{s["wrong"]}</td><td class="correct-word">{s["correct"]}</td><td>{s["hint"]}</td></tr>' for s in D['spelling'])

# Translation table
trans_rows = ''.join(f'<tr><td>{t["cn"]}</td><td>{t["en"]}</td><td>{t["example"]}</td></tr>' for t in D['translation_patterns'])

# Proper nouns
nouns_html = '<div class="word-bank" style="background:#fff">' + ''.join(f'<span class="word-chip" style="background:#27ae60">{n}</span>' for n in D['proper_nouns']) + '</div>'

# Schedule
sched_html = ''
for s in D['schedule']:
    tasks = ''.join(f'<li>{t}</li>' for t in s['tasks'])
    sched_html += f'<div class="section"><h3>📅 {s["phase"]}</h3><ul style="padding-left:20px;line-height:2.2">{tasks}</ul></div>'

# ============ SERIALIZE EXPLAIN DATA ============
lec_explain_js = json.dumps(LEC_EXPLAIN, ensure_ascii=False)
cloze_explain_js = json.dumps(CLOZE_EXPLAIN, ensure_ascii=False)

# ============ FULL HTML ============
html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CET-6 18天冲刺训练营</title>
<style>
:root {{ --bg: #f5f7fa; --card: #fff; --text: #2d3436; --accent: #6c5ce7; --accent-light: #f0f0ff; --border: #e0e0e0; --green: #27ae60; --red: #e74c3c; --hint: #888; }}
[data-theme="dark"] {{ --bg: #1a1a2e; --card: #16213e; --text: #e0e0e0; --accent: #a29bfe; --accent-light: #2a2a4e; --border: #333; --hint: #999; }}
[data-theme="dark"] body {{ background: var(--bg); }}
[data-theme="dark"] .q-item {{ background:#2a2a4e; }}
[data-theme="dark"] .script-text {{ background:#1a1a2e; color:#ccc; }}
[data-theme="dark"] .word-bank {{ background:#1a1a2e; }}
[data-theme="dark"] th {{ background:#2a2a4e; }}
[data-theme="dark"] .explain.show {{ color:var(--text); }}
[data-theme="dark"] .tab {{ background:#16213e; }}
[data-theme="dark"] .tab.active {{ background:#2a2a4e; }}
[data-theme="dark"] .blank.filled {{ background:#2a2a4e; }}
[data-theme="dark"] mark.user-highlight {{ background:#5a4a1a; color:#ffd54f; }}
[data-theme="dark"] .highlight-toggle.active {{ background:#5a4a1a; border-color:#e6a817; color:#ffd54f; }}
[data-theme="dark"] .theme-toggle {{ color:#ffd54f; border-color:#a29bfe; }}
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family: -apple-system,'PingFang SC','Microsoft YaHei',sans-serif; background:var(--bg); color:var(--text); line-height:1.8; }}
.header {{ background:linear-gradient(135deg,#6c5ce7,#a29bfe); color:#fff; padding:40px 20px; text-align:center; }}
.header h1 {{ font-size:26px; margin-bottom:6px; }}
.header p {{ font-size:14px; opacity:.85; }}
.header-btns {{ display:flex; gap:10px; justify-content:center; margin-top:12px; flex-wrap:wrap; }}
.container {{ max-width:860px; margin:0 auto; padding:20px; }}
.section {{ background:var(--card); border-radius:12px; padding:24px; margin-bottom:18px; box-shadow:0 2px 8px rgba(0,0,0,.05); }}
.section h3 {{ font-size:18px; margin-bottom:12px; color:var(--accent); border-bottom:2px solid var(--accent); padding-bottom:8px; }}
.hint {{ font-size:13px; color:var(--hint); margin-bottom:10px; }}
.q-list {{ display:flex; flex-direction:column; gap:10px; }}
.q-item {{ padding:10px 14px; background:var(--accent-light); border-radius:8px; border:1px solid var(--border); }}
.q-num {{ font-size:14px; color:var(--accent); font-weight:600; margin-bottom:4px; }}
.q-item label {{ display:block; padding:3px 0; font-size:14px; cursor:pointer; }}
.q-item input[type="radio"] {{ margin-right:8px; accent-color:var(--accent); }}
.word-bank {{ display:flex; flex-wrap:wrap; gap:8px; margin:12px 0; }}
.word-chip {{ display:inline-block; padding:6px 14px; background:var(--accent); color:#fff; border-radius:20px; font-size:14px; cursor:pointer; transition:opacity .2s; }}
.word-chip:hover {{ opacity:.8; }}
.word-chip.used {{ opacity:.3; pointer-events:none; }}
.blank {{ display:inline-block; min-width:70px; border-bottom:2px solid var(--accent); text-align:center; font-weight:600; color:var(--accent); margin:0 3px; cursor:pointer; padding:2px 6px; font-size:14px; }}
.blank.filled {{ background:var(--accent-light); }}
.reading-text {{ font-size:15px; line-height:2.2; text-align:justify; margin:12px 0; }}
.cloze-text {{ line-height:2.5; }}
.script-box {{ margin:10px 0; }}
.script-box summary {{ cursor:pointer; color:var(--accent); font-weight:600; }}
.script-text {{ white-space:pre-wrap; font-size:13px; line-height:1.8; background:#f5f5f5; padding:14px; border-radius:8px; margin-top:6px; }}
.explain {{ display:none; margin-top:10px; padding:10px 14px; border-radius:6px; font-size:13px; }}
.explain.show {{ display:block; }}
.btn-sm {{ padding:8px 20px; background:var(--accent); color:#fff; border:none; border-radius:8px; font-size:14px; cursor:pointer; margin-top:12px; }}
.btn-sm:hover {{ opacity:.9; }}
table {{ width:100%; border-collapse:collapse; margin:12px 0; font-size:14px; }}
th, td {{ padding:8px 12px; border:1px solid var(--border); text-align:left; }}
th {{ background:var(--accent-light); }}
.wrong-word {{ color:var(--red); font-weight:600; text-decoration:line-through; }}
.correct-word {{ color:var(--green); font-weight:600; }}
.tabs {{ display:flex; gap:10px; margin-bottom:20px; flex-wrap:wrap; }}
.tab {{ padding:10px 18px; background:var(--card); border:2px solid var(--border); border-radius:8px; cursor:pointer; font-size:14px; font-weight:600; }}
.tab.active {{ border-color:var(--accent); background:var(--accent-light); }}
.highlight-toggle {{ padding:6px 14px; border:2px solid var(--accent); border-radius:20px; background:transparent; color:var(--accent); cursor:pointer; font-size:13px; transition:all .2s; }}
.highlight-toggle.active {{ background:#fff3cd; border-color:#e6a817; color:#856404; }}
mark.user-highlight {{ background:#fff3cd; padding:0 1px; border-radius:2px; cursor:pointer; }}
.theme-toggle {{ padding:6px 14px; border:2px solid var(--accent); border-radius:20px; background:transparent; color:var(--accent); cursor:pointer; font-size:13px; transition:all .2s; }}
.timer-bar {{ display:none; height:4px; background:var(--accent); border-radius:2px; transition:width .5s linear; margin-top:12px; }}
.timer-bar.warn {{ background:var(--red); }}
.timer-label {{ display:none; font-size:12px; color:var(--hint); margin-top:4px; }}
.err-log {{ font-size:13px; line-height:1.8; }}
.err-item {{ padding:8px 12px; border-left:3px solid var(--red); margin:8px 0; background:var(--accent-light); border-radius:0 6px 6px 0; }}
.err-item .user-ans {{ color:var(--red); text-decoration:line-through; }}
.err-item .correct-ans {{ color:var(--green); font-weight:600; }}
</style>
</head>
<body>
<div class="header">
  <h1>🏃 CET-6 18天冲刺训练营</h1>
  <p>基于摸底诊断定制 · P0→选词填空+拼写+讲座听力</p>
  <p style="margin-top:4px;font-size:13px;opacity:.9">📅 <span id="sprint-day">冲刺训练营</span></p>
  <div class="header-btns">
    <button class="highlight-toggle" id="highlight-toggle" onclick="toggleHighlightMode()">🖊️ 勾画模式</button>
    <button class="theme-toggle" id="theme-toggle" onclick="toggleTheme()">🌙 深色模式</button>
  </div>
  <div class="timer-bar" id="timer-bar"></div>
  <div class="timer-label" id="timer-label"></div>
</div>
<div class="container">

<div class="tabs">
  <div class="tab active" onclick="showTab('schedule')">📅 日程表</div>
  <div class="tab" onclick="showTab('spelling')">🔤 拼写急救</div>
  <div class="tab" onclick="showTab('cloze')">📖 选词填空×3</div>
  <div class="tab" onclick="showTab('lecture')">🎧 讲座听力×3</div>
  <div class="tab" onclick="showTab('trans')">✍️ 翻译句型</div>
  <div class="tab" id="err-tab" style="display:none" onclick="showTab('errors')">📋 错题本</div>
</div>

<div id="tab-schedule">{sched_html}</div>
<div id="tab-spelling" style="display:none">
  <div class="section">
    <h3>🔤 拼写急救表（你的20个真实错误）</h3>
    <p class="hint">每天早晨抽10分钟，遮住右边，看左边错词写正确拼写。连续3天写对→划掉。</p>
    <table>{spell_rows}</table>
  </div>
</div>
<div id="tab-cloze" style="display:none">
  <div class="section" style="background:var(--accent-light)">
    <h3>⚡ 词性排除法（解题技巧）</h3>
    <p class="hint">十五选十的核心不是认不认识词——是<strong>词性判断</strong>。拿到题先不看词库，逐个空标注需要什么词性：</p>
    <table>
      <tr><th>空前后线索</th><th>需要的词性</th><th>示例</th></tr>
      <tr><td>a/an/the + ___ + n</td><td>形容词</td><td>a ___ challenge</td></tr>
      <tr><td>be + ___</td><td>形容词/名词/过去分词</td><td>is ___</td></tr>
      <tr><td>___ + 名词</td><td>形容词</td><td>___ damage</td></tr>
      <tr><td>can/may/must + ___</td><td>动词原形</td><td>can ___</td></tr>
      <tr><td>介词 + ___</td><td>名词/动名词</td><td>for ___</td></tr>
    </table>
  </div>
  {cloze_html}
</div>
<div id="tab-lecture" style="display:none">
  <div class="section" style="background:var(--accent-light)">
    <h3>⚡ 讲座听力三遍法</h3>
    <p class="hint">①第一遍：正常做题不暂停 → ②第二遍：逐句听写（听不出的空着） → ③第三遍：对照原文标红失败位置，分析原因</p>
    <p class="hint">信号词后必出题：However / In fact / Therefore / Moreover / Strikingly / As a result</p>
  </div>
  {lec_html}
</div>
<div id="tab-trans" style="display:none">
  <div class="section">
    <h3>✍️ 翻译高频句型（10个）</h3>
    <p class="hint">每天背2句，5天背完。做翻译时强制用上。</p>
    <table>{trans_rows}</table>
  </div>
  <div class="section">
    <h3>📝 翻译专有名词（20个）</h3>
    <p class="hint">考前必须零拼写错的名词。</p>
    {nouns_html}
  </div>
</div>
<div id="tab-errors" style="display:none">
  <div class="section">
    <h3>📋 错题本（全冲刺周期积累）</h3>
    <p class="hint">每次检查答案后自动收集错题。D15-D18 集中复习，逐一消灭。</p>
    <div class="err-log" id="err-log">暂无错题。做了题就会自动记录。</div>
  </div>
</div>

</div>

<script>
function showTab(name) {{
  document.querySelectorAll('[id^="tab-"]').forEach(el => el.style.display = 'none');
  document.getElementById('tab-' + name).style.display = '';
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  event.target.classList.add('active');
}}

// Cloze word picking
let currentPick = {{}};
function pickWord(setIdx, word, el) {{
  currentPick[setIdx] = {{word, el}};
  document.getElementById('pick-ci'+setIdx).textContent = word;
  document.querySelectorAll('.word-chip[data-set="'+setIdx+'"]').forEach(c => c.style.outline='none');
  el.style.outline = '3px solid #ffd700';
}}

document.querySelectorAll('.blank').forEach(b => {{
  b.addEventListener('click', function() {{
    const setIdx = this.id.split('_')[0].replace('c','');
    if (!currentPick[setIdx]) return;
    if (this.classList.contains('filled')) return;
    this.textContent = currentPick[setIdx].word;
    this.classList.add('filled');
    this.dataset.pick = currentPick[setIdx].word;
    currentPick[setIdx].el.classList.add('used');
    currentPick[setIdx] = null;
    document.getElementById('pick-ci'+setIdx).textContent = '无';
  }});
  b.addEventListener('dblclick', function() {{
    if (!this.classList.contains('filled')) return;
    const w = this.dataset.pick;
    document.querySelectorAll('.word-chip[data-word="'+w+'"]').forEach(c => c.classList.remove('used'));
    this.textContent = '(' + this.id.split('_')[1] + ')____';
    this.classList.remove('filled');
    delete this.dataset.pick;
  }});
}});

// ========== CHECK FUNCTIONS ==========
var LEC_EXPLAIN = {lec_explain_js};
var CLOZE_EXPLAIN = {cloze_explain_js};

function showExplain(container, idx, i, type) {{
  var data = type === 'lec' ? LEC_EXPLAIN : CLOZE_EXPLAIN;
  var ex = data[idx] && data[idx][i];
  if (!ex) return;
  var div = document.createElement('div');
  div.style.cssText = 'margin-top:4px;padding:6px 10px;background:var(--accent-light);border-radius:6px;font-size:12px;line-height:1.6;color:var(--text);';
  div.textContent = '💡 ' + ex;
  container.appendChild(div);
}}

function checkCloze(idx, answers) {{
  let correct = 0;
  answers.forEach((ans, i) => {{
    const b = document.getElementById('c'+idx+'_'+(i+1));
    if (!b) return;
    if (b.dataset.pick === ans) {{ 
      correct++; 
      b.style.borderBottom='3px solid var(--green)'; 
      b.style.background='#e8f5e9';
    }} else {{ 
      b.style.borderBottom='3px solid var(--red)'; 
      b.style.background='#fdecea';
      b.title = '答案: '+ans;
      var hint = document.createElement('sup');
      hint.style.cssText = 'color:var(--green);font-size:11px;margin-left:2px;';
      hint.textContent = '→' + ans;
      b.appendChild(hint);
      saveError('选词填空', idx, i+1, b.dataset.pick||'(空)', ans, CLOZE_EXPLAIN[idx]&&CLOZE_EXPLAIN[idx][i]||'');
    }}
    showExplain(b.parentNode, idx, i, 'cloze');
  }});
  var el = document.getElementById('clozenote-'+idx);
  el.className = 'explain show';
  el.style.background = correct >= 7 ? '#e8f5e9' : '#fdecea';
  el.innerHTML = (correct >= 7 ? '✅ ' : correct >= 4 ? '⚠️ ' : '❌ ') + '<b>' + correct + '/10</b> ' + (correct >= 7 ? '过关！' : '继续练') + ' — 绿色=对，红色=错（箭头后是正确答案）';
}}

function checkLec(idx, answers) {{
  let correct = 0;
  answers.forEach((ans, i) => {{
    var sel = document.querySelector('input[name="l'+idx+'_'+i+'"]:checked');
    var labels = document.querySelectorAll('input[name="l'+idx+'_'+i+'"]');
    var myLabel = null;
    var qDiv = labels[0].closest('.q-item');
    labels.forEach(function(inp) {{
      var lbl = inp.closest('label');
      if (sel && inp.value === ans) {{
        lbl.style.background = '#e8f5e9';
        lbl.style.borderRadius = '4px';
        lbl.style.padding = '2px 6px';
      }}
      if (sel && inp === sel && sel.value !== ans) {{
        lbl.style.background = '#fdecea';
        lbl.style.borderRadius = '4px';
        lbl.style.padding = '2px 6px';
      }}
      if (inp === sel) myLabel = lbl;
    }});
    if (sel && sel.value === ans) {{
      correct++;
    }} else if (sel) {{
      var sp = document.createElement('span');
      sp.style.cssText = 'color:var(--green);font-weight:600;font-size:12px;margin-left:6px;';
      sp.textContent = '→ 正确答案: ' + ans;
      myLabel.appendChild(sp);
      saveError('讲座听力', idx, i+1, sel.value, ans, LEC_EXPLAIN[idx]&&LEC_EXPLAIN[idx][i]||'');
    }} else {{
      var correctLbl = document.querySelector('input[name="l'+idx+'_'+i+'"][value="'+ans+'"]').closest('label');
      correctLbl.style.background = '#fff3cd';
      correctLbl.style.borderRadius = '4px';
      correctLbl.style.padding = '2px 6px';
      var sp2 = document.createElement('span');
      sp2.style.cssText = 'color:#856404;font-weight:600;font-size:12px;margin-left:6px;';
      sp2.textContent = '← 未作答，正确答案';
      correctLbl.appendChild(sp2);
      saveError('讲座听力', idx, i+1, '未作答', ans, LEC_EXPLAIN[idx]&&LEC_EXPLAIN[idx][i]||'');
    }}
    if (qDiv) showExplain(qDiv, idx, i, 'lec');
  }});
  var el = document.getElementById('lecnote-'+idx);
  el.className = 'explain show';
  el.style.background = correct >= 4 ? '#e8f5e9' : '#fdecea';
  el.innerHTML = '<b>' + (correct >= 4 ? '✅ ' : correct >= 3 ? '⚠️ ' : '❌ ') + correct + '/5</b> ' + (correct >= 4 ? '过关！' : '用三遍法重听') + ' — 绿底=对，红底=错，黄底=未答';
}}

// ========== HIGHLIGHT MODE ==========
var highlightMode = false;
function toggleHighlightMode() {{
  highlightMode = !highlightMode;
  var btn = document.getElementById('highlight-toggle');
  if (highlightMode) {{
    btn.classList.add('active');
    btn.textContent = '🖊️ 勾画中（拖选文字标记，再点取消）';
  }} else {{
    btn.classList.remove('active');
    btn.textContent = '🖊️ 勾画模式';
  }}
}}
document.addEventListener('mouseup', function(e) {{
  if (!highlightMode) return;
  var existing = e.target.closest('mark.user-highlight');
  if (existing) {{
    var txt = existing.textContent;
    existing.replaceWith(document.createTextNode(txt));
    window.getSelection().removeAllRanges();
    return;
  }}
  var sel = window.getSelection();
  if (!sel.rangeCount || sel.isCollapsed) return;
  var range = sel.getRangeAt(0);
  var label = e.target.closest('label');
  if (!label) return;
  if (!label.contains(range.commonAncestorContainer)) return;
  try {{
    var mark = document.createElement('mark');
    mark.className = 'user-highlight';
    range.surroundContents(mark);
    sel.removeAllRanges();
  }} catch(ex) {{}}
}});

// ========== F KEY SHORTCUT ==========
document.addEventListener('keydown', function(e) {{
  if (e.key === 'f' && document.activeElement.tagName !== 'INPUT' && document.activeElement.tagName !== 'TEXTAREA') {{
    e.preventDefault();
    toggleHighlightMode();
  }}
}});

// ========== SPRINT DAY TRACKER ==========
(function() {{
  var START = new Date('2026-05-27');
  var today = new Date();
  var dayNum = Math.floor((today - START) / 86400000) + 1;
  var phases = [
    {{days:[1,3], name:'选词填空突破', task:'1套选词填空+1篇讲座，先标词性再看原文'}},
    {{days:[4,6], name:'听力强攻', task:'1套选词填空+2篇讲座，目标正确率5+/4+'}},
    {{days:[7,9], name:'输出提升', task:'限时12分钟选词填空+全真听力连做'}},
    {{days:[10,14], name:'全真模拟期', task:'每2天1套完整模拟卷，严格计时'}},
    {{days:[15,18], name:'收网', task:'只复习错题，默写句型和专有名词'}},
  ];
  var phase = null;
  for (var i = 0; i < phases.length; i++) {{
    if (dayNum >= phases[i].days[0] && dayNum <= phases[i].days[1]) {{ phase = phases[i]; break; }}
  }}
  if (dayNum < 1) dayNum = 1;
  if (dayNum > 18) {{ dayNum = 18; phase = phases[4]; }}
  var el = document.getElementById('sprint-day');
  if (phase) {{
    el.innerHTML = 'Day ' + dayNum + '/18 · ' + phase.name + ' — ' + phase.task;
  }} else {{
    el.innerHTML = 'Day ' + dayNum + '/18 · 冲刺训练营';
  }}
}})();
// ========== TIMER (D7-D9) ==========
var sprintDay = dayNum;
var timerInterval = null;
var timerSeconds = 0;
function startTimer(sec, label) {{
  var bar = document.getElementById('timer-bar');
  var lbl = document.getElementById('timer-label');
  if (sprintDay < 7 || sprintDay > 9) return;
  bar.style.display = 'block'; lbl.style.display = 'block';
  timerSeconds = sec;
  bar.style.width = '100%'; bar.classList.remove('warn');
  updateTimerLabel();
  timerInterval = setInterval(function() {{
    timerSeconds--;
    var pct = Math.max(0, timerSeconds / sec * 100);
    bar.style.width = pct + '%';
    if (pct < 20) bar.classList.add('warn');
    updateTimerLabel();
    if (timerSeconds <= 0) {{ clearInterval(timerInterval); bar.style.width='0%'; lbl.textContent='⏰ 时间到！'; }}
  }}, 1000);
}}
function updateTimerLabel() {{
  var m = Math.floor(timerSeconds / 60), s = timerSeconds % 60;
  document.getElementById('timer-label').textContent = '⏱ ' + m + ':' + (s<10?'0':'') + s;
}}
function stopTimer() {{ if(timerInterval){{ clearInterval(timerInterval); timerInterval=null; }} }}
// Auto-start timer when entering cloze/lecture tab in D7-D9
var origShowTab = showTab;
showTab = function(name) {{
  stopTimer();
  if (sprintDay >= 7 && sprintDay <= 9) {{
    if (name === 'cloze') startTimer(720, '限时12分钟');
    else if (name === 'lecture') startTimer(900, '限时15分钟');
  }}
  origShowTab(name);
}};

// ========== ERROR LOG ==========
function saveError(type, setId, qNum, userAns, correctAns, explain) {{
  var log = JSON.parse(localStorage.getItem('sprint-errors') || '[]');
  log.push({{type:type, set:setId, q:qNum, user:userAns, correct:correctAns, explain:explain, date:new Date().toISOString().slice(0,10)}});
  localStorage.setItem('sprint-errors', JSON.stringify(log));
}}
function renderErrors() {{
  var log = JSON.parse(localStorage.getItem('sprint-errors') || '[]');
  var el = document.getElementById('err-log');
  if (!log.length) {{ el.innerHTML = '暂无错题。做了题就会自动记录。'; return; }}
  var html = '<p class=\"hint\">共 <b>' + log.length + '</b> 条错题</p>';
  log.forEach(function(e, i) {{
    html += '<div class=\"err-item\"><b>' + (i+1) + '.</b> [' + e.type + ' Set' + (e.set+1) + ' Q' + e.qNum + '] ' + e.date;
    html += '<br>你的答案: <span class=\"user-ans\">' + e.user + '</span> → 正确答案: <span class=\"correct-ans\">' + e.correct + '</span>';
    html += '<br><span style=\"color:var(--hint)\">' + (e.explain || '') + '</span></div>';
  }});
  el.innerHTML = html;
}}
// Show error tab only D15-D18
if (sprintDay >= 15) {{
  document.getElementById('err-tab').style.display = '';
  renderErrors();
}}
// Clear errors button
function clearErrors() {{
  if (confirm('确定清空所有错题记录？不可恢复。')) {{
    localStorage.removeItem('sprint-errors');
    renderErrors();
  }}
}}
function toggleTheme() {{
  var current = document.documentElement.getAttribute('data-theme');
  var next = current === 'dark' ? '' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  localStorage.setItem('cet6-theme', next);
  var btn = document.getElementById('theme-toggle');
  btn.textContent = next === 'dark' ? '☀️ 浅色模式' : '🌙 深色模式';
}}
(function() {{
  var saved = localStorage.getItem('cet6-theme');
  if (saved === 'dark') {{
    document.documentElement.setAttribute('data-theme', 'dark');
    document.getElementById('theme-toggle').textContent = '☀️ 浅色模式';
  }}
}})();
</script>
</body>
</html>'''

with open('C:/Users/30943/cet6-daily/cet6-sprint.html', 'w', encoding='utf-8') as f:
    f.write(html)
print(f"Saved cet6-sprint.html ({len(html)} bytes)")
