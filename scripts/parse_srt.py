#!/usr/bin/env python3
"""
parse_srt.py — 解析 SRT 字幕，输出「视频打点」所需的 JSON 结构。

用途：
  视频打点（学习导航）工作流的第 3 步，需要从字幕中提取时间轴与过渡信息。
  本脚本输出与 video-bookmark 打点工作流对齐的 JSON：
    total_entries       字幕条目总数
    total_duration      总时长（MM:SS 或 HH:MM:SS）
    entries             每条字幕：{idx, start, end, text}
    text_by_timeframe   按 60 秒窗口分组的文本摘要
    transition_points   过渡词（首先/接下来/最后等）出现的时间点，辅助定位模块边界

用法：
  python3 scripts/parse_srt.py "<srt_file>"
  python3 scripts/parse_srt.py "<srt_file>" --window 120

输入：
  标准 SRT 字幕（也兼容写入 .md 文件的 SRT 块）
"""

import sys
import re
import json

# 过渡词：辅助定位内容模块边界（可自行增删）
TRANSITION_WORDS = [
    '首先', '接下来', '然后', '最后', '我们先', '我们来看', '我们看',
    '第二', '第三', '第二点', '第三点', '第二部分', '第三部分',
    '小结', '总结', '回顾', '下面', '现在', '给大家', '讲一下', '说一下',
]


# ============================================================
# SRT 解析（与 subtitle_processor/core.py 保持同构）
# ============================================================

def parse_srt(text):
    """解析 SRT 格式文本为结构化数据块列表"""
    blocks = []
    lines = text.strip().split('\n')
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if line.isdigit():
            idx = int(line)
            i += 1
            if i >= len(lines):
                break
            time_line = lines[i].strip()
            i += 1
            text_lines = []
            while i < len(lines) and lines[i].strip():
                text_lines.append(lines[i].strip())
                i += 1
            blocks.append({'idx': idx, 'time': time_line, 'text': ' '.join(text_lines)})
        else:
            i += 1
    return blocks


def parse_ms(t):
    """SRT 时间戳（HH:MM:SS,mmm 或 MM:SS,mmm）→ 毫秒"""
    t = t.strip()
    m = re.match(r'(\d{1,2}):(\d{1,2}):(\d{1,2})[,.](\d{1,3})', t)
    if m:
        h, mi, s, ms = m.groups()
        return int(h) * 3600000 + int(mi) * 60000 + int(s) * 1000 + int(ms.ljust(3, '0'))
    m2 = re.match(r'(\d{1,2}):(\d{1,2})[,.](\d{1,3})', t)
    if m2:
        mi, s, ms = m2.groups()
        return int(mi) * 60000 + int(s) * 1000 + int(ms.ljust(3, '0'))
    return 0


def fmt_clock(ms):
    """毫秒 → MM:SS（超 1 小时用 HH:MM:SS）"""
    ms = max(0, int(ms))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    if h:
        return f'{h:02d}:{m:02d}:{s:02d}'
    return f'{m:02d}:{s:02d}'


def split_time(time_line):
    """'00:00:00,000 --> 00:00:02,000' → (start_ms, end_ms)"""
    parts = time_line.split('-->')
    if len(parts) != 2:
        return (0, 0)
    return (parse_ms(parts[0]), parse_ms(parts[1]))


# ============================================================
# 主流程
# ============================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description='解析 SRT 字幕为视频打点所需 JSON')
    parser.add_argument('input', help='SRT/.md 字幕文件路径')
    parser.add_argument('--window', type=int, default=60,
                        help='文本分组窗口（秒），默认 60')
    parser.add_argument('--no-transitions', action='store_true',
                        help='不输出过渡词定位点')
    args = parser.parse_args()

    with open(args.input, 'r', encoding='utf-8') as f:
        content = f.read()

    blocks = parse_srt(content)
    entries = []
    total_end = 0
    for b in blocks:
        start, end = split_time(b['time'])
        total_end = max(total_end, end)
        entries.append({
            'idx': b['idx'],
            'start': fmt_clock(start),
            'end': fmt_clock(end),
            'start_ms': start,
            'end_ms': end,
            'text': b['text'],
        })

    # 按窗口分组文本（便于整体浏览各时段讲了什么）
    window_sec = max(1, args.window)
    buckets = {}
    for e in entries:
        w = int(e['start_ms'] / 1000 / window_sec)
        buckets.setdefault(w, []).append(e['text'])
    text_by_timeframe = {}
    for w in sorted(buckets):
        start_fmt = fmt_clock(w * window_sec * 1000)
        end_fmt = fmt_clock((w + 1) * window_sec * 1000)
        text_by_timeframe[f'{start_fmt} - {end_fmt}'] = ' '.join(buckets[w])

    # 过渡词出现的时间点（辅助模块边界定位）
    transition_points = []
    if not args.no_transitions:
        for e in entries:
            hits = [w for w in TRANSITION_WORDS if w in e['text']]
            if hits:
                transition_points.append({
                    'time': e['start'],
                    'words': hits,
                    'text': e['text'][:40],
                })

    # 输出时去掉 ms 字段，保持 JSON 简洁
    result = {
        'total_entries': len(entries),
        'total_duration': fmt_clock(total_end),
        'entries': [
            {k: v for k, v in e.items() if k not in ('start_ms', 'end_ms')}
            for e in entries
        ],
        'text_by_timeframe': text_by_timeframe,
        'transition_points': transition_points,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
