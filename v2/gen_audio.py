"""
CET-6 音频生成 v2 — 基于共享库统一解析，带错误恢复和进度条。
Usage:
  python gen_audio.py <html_file> [output_dir]
"""
import re, os, sys, subprocess, tempfile, shutil, asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib import parse_html, extract_section, CONFIG


def build_text(script: str, questions: list) -> str:
    """生成朗读文本：原文 + 仅题干（不含选项，选项由学生阅读页面）"""
    lines = [script.strip(), '', '']
    for i, q in enumerate(questions):
        lines.append(f'Question {i+1}. {q.get("q", "")}')
        lines.append('')
    return '\n'.join(lines)


async def gen_single(text: str, voice: str, output: str):
    """生成单声音频"""
    import edge_tts
    comm = edge_tts.Communicate(text, voice)
    await comm.save(output)
    size_kb = os.path.getsize(output) // 1024
    print(f'  ✓ {os.path.basename(output)}: {size_kb} KB')


async def gen_conversation(script: str, questions: list, output: str):
    """长对话：逐句多声音 + ffmpeg 拼接"""
    import edge_tts

    voices = {
        'M': CONFIG['voices']['male'],
        'W': CONFIG['voices']['female'],
    }

    tmpdir = tempfile.mkdtemp(prefix='cet6_audio_')
    files = []

    try:
        # 逐行对话
        idx = 0
        for line in script.strip().split('\n'):
            line = line.strip()
            if not line:
                continue
            if line.startswith('M:'):
                voice, text = voices['M'], line[2:].strip()
            elif line.startswith('W:'):
                voice, text = voices['W'], line[2:].strip()
            else:
                voice, text = CONFIG['voices']['default'], line

            fp = os.path.join(tmpdir, f'd_{idx:04d}.mp3')
            comm = edge_tts.Communicate(text, voice)
            await comm.save(fp)
            files.append(fp)
            idx += 1

        # 问题部分（单声音，仅题干不含选项）
        for i, q in enumerate(questions):
            text = f'Question {i+1}. {q.get("q", "")}'
            fp = os.path.join(tmpdir, f'q_{i:04d}.mp3')
            comm = edge_tts.Communicate(text, CONFIG['voices']['default'])
            await comm.save(fp)
            files.append(fp)

        # ffmpeg 拼接
        concat_file = os.path.join(tmpdir, 'concat.txt')
        with open(concat_file, 'w', encoding='utf-8') as f:
            for fp in files:
                f.write(f"file '{fp}'\n")

        result = subprocess.run(
            ['ffmpeg', '-y', '-f', 'concat', '-safe', '0',
             '-i', concat_file, '-c', 'copy', output],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f'  ✗ ffmpeg 失败: {result.stderr[:200]}')
            return

        size_kb = os.path.getsize(output) // 1024
        print(f'  ✓ {os.path.basename(output)}: {size_kb} KB ({len(files)} segments)')

    finally:
        for fp in files:
            if os.path.exists(fp):
                os.remove(fp)
        if os.path.exists(concat_file):
            os.remove(concat_file)
        shutil.rmtree(tmpdir, ignore_errors=True)


async def main():
    if len(sys.argv) < 2:
        print("Usage: python gen_audio.py <html_file> [output_dir]")
        sys.exit(2)

    html_path = sys.argv[1]
    out_dir = sys.argv[2] if len(sys.argv) > 2 else CONFIG['audio_out_dir']

    html = parse_html(html_path)
    date = re.search(r'(\d{8})', os.path.basename(html_path))
    date = date.group(1) if date else 'unknown'

    os.makedirs(out_dir, exist_ok=True)

    for key, fname_tpl, voice_key, is_conv in CONFIG['SECTIONS']:
        print(f'[{key}]', end=' ')
        script, questions = extract_section(html, key)

        if not script:
            print('SKIP (无数据)')
            continue

        output = os.path.join(out_dir, fname_tpl.format(date=date))

        if is_conv:
            await gen_conversation(script, questions, output)
        else:
            voice = CONFIG['voices'][voice_key] if voice_key else CONFIG['voices']['default']
            text = build_text(script, questions)
            await gen_single(text, voice, output)

    print('✅ DONE')


if __name__ == '__main__':
    asyncio.run(main())
