"""
CET-6 质量检查 v2 — 基于共享库 lib.py，支持评分输出、逐篇评分和批量模式。
Usage:
  python quality_check.py <html_file>               # 单文件检查
  python quality_check.py <html_file> --json        # JSON 输出
  python quality_check.py <html_file> --score       # 只输出总分
  python quality_check.py <html_file> --per-section # 逐篇评分（对应规则 §8）
  python quality_check.py <html_file> --verbose     # 显示 info 级别信息（重叠率分级等）
"""
import sys, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib import check_all, score, per_section_score, extract_data, parse_html


def main():
    if len(sys.argv) < 2:
        print("Usage: python quality_check.py <html_file> [--json|--score|--per-section|--verbose]")
        sys.exit(2)

    html_path = sys.argv[1]
    mode_json = '--json' in sys.argv
    mode_score = '--score' in sys.argv
    mode_per_section = '--per-section' in sys.argv
    mode_verbose = '--verbose' in sys.argv

    try:
        issues = check_all(html_path)
    except Exception as e:
        print(f"Failed to parse: {e}")
        sys.exit(2)

    result = score(issues)

    if mode_per_section:
        ps = per_section_score(html_path)
        print(f"Per-section scores:")
        for sec, info in ps.items():
            flag = '✓' if info['pass'] else '✗'
            print(f"  {sec}: {info['score']}/25 ({info['errors']}E {info['warns']}W) {flag}")
        all_pass = all(info['pass'] for info in ps.values())
        sys.exit(0 if all_pass else 1)

    if mode_score:
        print(f"Total: {result['total']}/100  ({result['grade']})")
        for k, v in result['scores'].items():
            print(f"  {k}: {v}/25")
        sys.exit(0 if result['pass'] else 1)

    if mode_json:
        ps = per_section_score(html_path)
        output = {
            'file': html_path,
            'issues': issues,
            'score': result,
            'per_section': ps,
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
        sys.exit(0 if result['pass'] else 1)

    # ── human readable ──
    print(f"Quality check: {html_path}")
    print(f"   Score: {result['total']}/100 ({result['grade']})")
    print(f"   Listening {result['scores']['listening']} | Reading {result['scores']['reading']} "
          f"| Translation {result['scores']['translation']} | Writing {result['scores']['writing']}")
    print()

    if not issues:
        print("All checks passed")
        sys.exit(0)

    errors = [i for i in issues if i['severity'] == 'error']
    warns  = [i for i in issues if i['severity'] == 'warn']
    infos  = [i for i in issues if i['severity'] == 'info']

    if errors:
        print(f"{len(errors)} errors:")
        for i in errors:
            print(f"  [{i['section']}] {i['item']}: {i['detail']}")

    if warns:
        print(f"{len(warns)} warnings:")
        for i in warns:
            print(f"  [{i['section']}] {i['item']}: {i['detail']}")

    if infos and mode_verbose:
        print(f"{len(infos)} info:")
        for i in infos:
            print(f"  [{i['section']}] {i['item']}: {i['detail']}")

    sys.exit(0 if result['pass'] else 1)


if __name__ == '__main__':
    main()
