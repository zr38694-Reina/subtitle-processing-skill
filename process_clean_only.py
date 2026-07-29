#!/usr/bin/env python3
"""字幕加工流水线 — 仅清理模式（无断句合并，无拆分）

步骤：
1. 语气词清理（啊、那、这个、呢、吧等）
2. ASR 错误修正
3. 过短条目处理（≤2 字）
"""

import re
import os
import sys
import shutil

vault_root = "/Users/reina/Library/Mobile Documents/iCloud~md~obsidian/Documents/Storage for Reina"
filepath = os.path.join(vault_root, "智谱课程字幕检查", "智谱1.3.md")

# ============================================================
# 语气词清理规则
# ============================================================

FILLER_REPLACEMENTS = [
    # 句首"那"开头的填充
    (r'^那\s*', ''),
    # "那" + 特定字开头的填充
    (r'^那(?=这个|我们|你|我|他|它|一|两|目前|如果|除了|关于|首先|接下来|最后|一般)',
     ''),
    # "那"在句中做填充
    (r'(?<=[，。！？])那(?=这个|我们|你|我|他|它|一|两|目前|如果|除了|关于|首先|接下来|最后|一般)',
     ''),
    # "这个/那个"做填充词（非指示词用法）
    (r'(^|[\s，。！？])这个\s+(?=我们|你|他|一|两|就是|可以|需要|能够|应该|把|将|在)',
     r'\1'),
    (r'(^|[\s，。！？])那个\s+(?=我们|你|他|一|两|就是|可以|需要|能够)',
     r'\1'),
    # "呢" — 删除所有居中的
    (r'\b呢\b', ''),
    # "吧" — 删除所有
    (r'\b吧\b', ''),
    # "哦" — 删除所有
    (r'\b哦\b', ''),
    # "嗯" — 删除所有
    (r'\b嗯\b', ''),
    # "呃" — 删除所有
    (r'\b呃\b', ''),
    # "呀" — 部分删除（保留在语气需要的场合）
    (r'(?<=好)呀', ''),
    (r'呀(?=[。，！？]|$)', ''),
    # "诶" — 删除
    (r'\b诶\b', ''),
    # "啊"的处理 — 句尾/句中填充删除
    (r'(?<=[^\s，。！？、；：])啊(?=[\s，。！？、；：]|$)', ''),
    (r'^啊\s*', ''),
    (r'啊(?=[。，！？])', ''),
    # "这个啊" → "这个"
    (r'这个啊', '这个'),
    (r'那个啊', '那个'),
    # "的啊" → "的"
    (r'的啊', '的'),
    # "了啊" → "了"
    (r'了啊', '了'),
    # "那么"做填充（句首）
    (r'^那么\s*', ''),
    # "其实"前的"那"
    (r'那其实', '其实'),
    (r'那实际上', '实际上'),
    (r'那当然', '当然'),
    (r'那首先', '首先'),
    (r'那接下来', '接下来'),
    (r'那最后', '最后'),
    (r'那目前', '目前'),
    (r'那如果', '如果'),
    (r'那除了', '除了'),
    (r'那关于', '关于'),
    # "这个"做填充
    (r'这样一个', '一个'),
    (r'这样一些', '这些'),
    (r'说简单点呢', '简言之'),
]

# ============================================================
# ASR 错误修正
# ============================================================

ASR_FIXES = {
    '大元模型': '大语言模型',
    '大圆模型': '大语言模型',
    '大语言元模型': '大语言模型',
    '大元': '大语言',
    '大圆': '大语言',
    'VB coding': 'Vibe Coding',
    'v b coding': 'Vibe Coding',
    'v b': 'Vibe',
    'VB': 'Vibe',
    'vb coding': 'Vibe Coding',
    'vb': 'Vibe',
    '轨迹流动': '硅基流动',
    '归基流动': '硅基流动',
    '空大环境': 'conda 环境',
    '空大': 'conda',
    'VibeCoding': 'Vibe Coding',
    '这个呃': '',
    '呃这个': '',
    '各各位': '各位',
    '接接下来': '接下来',
    '所所有': '所有',
    'VPI API': 'API',
    'VPIAPI': 'API',
}


# ============================================================
# 工具函数
# ============================================================

def parse_srt(content):
    entries = []
    blocks = re.split(r'\n\n+', content.strip())
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) < 3:
            continue
        try:
            idx = int(lines[0].strip())
        except ValueError:
            continue
        time_match = re.match(
            r'(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})',
            lines[1])
        if not time_match:
            continue
        text = ''.join(line.strip() for line in lines[2:])
        entries.append((idx, time_match.group(1), time_match.group(2), text))
    return entries


def format_srt(entries):
    lines = []
    for i, (idx, start, end, text) in enumerate(entries, 1):
        if text.strip():
            lines.append(f'{i}')
            lines.append(f'{start} --> {end}')
            lines.append(text.strip())
            lines.append('')
    return '\n'.join(lines)


def clean_text(text):
    """清理单一文本条目"""
    # 1. 正则语气词替换
    for pattern, replacement in FILLER_REPLACEMENTS:
        text = re.sub(pattern, replacement, text)

    # 2. ASR 修正
    for wrong, correct in ASR_FIXES.items():
        text = text.replace(wrong, correct)

    # 3. 清理多余空格和标点
    text = re.sub(r'\s+', '', text)

    # 4. 统一中英文之间的空格
    text = re.sub(r'([一-鿿])([A-Za-z0-9])', r'\1 \2', text)
    text = re.sub(r'([A-Za-z0-9])([一-鿿])', r'\1 \2', text)
    text = re.sub(r' +', ' ', text)

    return text.strip()


# ============================================================
# 主流程
# ============================================================

def main():
    print(f"📄 读取: 智谱1.3.md")

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 解析
    entries = parse_srt(content)
    original_count = len(entries)
    print(f"   原始条目: {original_count}")

    # 步骤 1 & 2: 清理语气词 + ASR 修正
    cleaned = []
    for e in entries:
        new_text = clean_text(e[3])
        cleaned.append((e[0], e[1], e[2], new_text))

    # 步骤 3: 移除过短条目（≤2 字）
    before_short = len(cleaned)
    cleaned = [e for e in cleaned if len(e[3]) > 2]
    short_removed = before_short - len(cleaned)

    # 写入 vault 内 .md 文件
    output = format_srt(cleaned)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(output)

    print(f"   ✨ 语气词清理 + ASR 修正完成")
    print(f"   ✂️  移除过短条目 (≤2字): {short_removed} 条")
    print(f"\n📊 最终统计:")
    print(f"   原始: {original_count} 条")
    print(f"   最终: {len(cleaned)} 条")
    print(f"   缩减: {original_count - len(cleaned)} 条")
    print(f"\n✅ 清理完成！文件已保存")

    # ============================================================
    # 步骤 4: 导出 SRT 到桌面
    # ============================================================
    desktop_path = os.path.expanduser("~/Desktop/智谱1.3.srt")
    with open(desktop_path, 'w', encoding='utf-8') as f:
        f.write(output)
    print(f"   🖥️  SRT 已导出到桌面: {desktop_path}")


if __name__ == '__main__':
    main()
