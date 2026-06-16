"""
CET-6 答案分布验证 v2 — 基于共享库，支持历史和趋势对比。
Usage:
  python verify_answers.py <html_file>                   # 单文件检查
  python verify_answers.py <html_file> --json            # JSON 输出
  python verify_answers.py <file1> <file2> --compare     # 两文件对比
"""
import sys, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib import extract_answers, check_distribution, CONFIG


def print_human(result: dict, label: str = ''):
    """人类可读输出"""
    if label:
        print(f"\n📊 {label}")
    dist = result['distribution']
    total = result['total']
    lo, hi = CONFIG['answer_range']

    print(f"总题数: {total}")
    for l in 'ABCD':
        d = result['details'].get(l, {})
        flag = '✓' if d.get('ok') else '✗'
        print(f"  {l}: {d.get('count', 0)} ({d.get('pct', 0)}%) {flag}")

    print(f"\n逐 section (目标: 每字母 1-2 次):")
    for s in result['sections']:
        flag = '✓' if s['ok'] else '✗'
        d = s['distribution']
        print(f"  Section {s['section']}: A:{d['A']} B:{d['B']} C:{d['C']} D:{d['D']} {flag}")

    print(f"\n{'✅ 通过' if result['global_ok'] and result['all_sections_ok'] else '❌ 不通过'}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python verify_answers.py <html_file> [--json]")
        print("       python verify_answers.py <file1> <file2> --compare")
        sys.exit(2)

    mode_json   = '--json' in sys.argv
    mode_compare = '--compare' in sys.argv
    files = [a for a in sys.argv[1:] if not a.startswith('--')]

    if mode_compare and len(files) >= 2:
        results = []
        for fpath in files:
            with open(fpath, 'r', encoding='utf-8') as f:
                html = f.read()
            answers = extract_answers(html)
            results.append(check_distribution(answers))

        if mode_json:
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            print_human(results[0], files[0])
            print_human(results[1], files[1])

            # 趋势对比
            d1 = results[0]['distribution']
            d2 = results[1]['distribution']
            print("\n── 趋势 ──")
            for l in 'ABCD':
                delta = d2.get(l, 0) - d1.get(l, 0)
                arrow = '↑' if delta > 0 else ('↓' if delta < 0 else '→')
                print(f"  {l}: {d1.get(l,0)} → {d2.get(l,0)} ({arrow}{abs(delta)})")

        ok = all(r['global_ok'] and r['all_sections_ok'] for r in results)
        sys.exit(0 if ok else 1)

    else:
        # 单文件模式
        filepath = files[0]
        with open(filepath, 'r', encoding='utf-8') as f:
            html = f.read()
        answers = extract_answers(html)
        result = check_distribution(answers)

        if mode_json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print_human(result)

        ok = result['global_ok'] and result['all_sections_ok']
        sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
