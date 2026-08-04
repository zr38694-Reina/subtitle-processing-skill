#!/usr/bin/env python3
"""
字幕加工流水线 (Subtitle Processing Pipeline)
==============================================
处理 SRT 格式的字幕文件，支持：
  1. 语气词清理 (啊、那、这个、呢、吧、哦、嗯、呃等)
  2. ASR 错误修正 (如 大圆/大元→大语言模型, VB→Vibe Coding)
  3. 过短条目合并 (≤2 字)
  4. 断句合并 (可选)

用法:
  python3 process_subtitles.py <输入文件> [选项]

选项:
  --only-clean-fillers    仅清理语气词，不做合并
  --also-merge            清理后做断句合并
  --output FILE           输出文件路径 (默认覆盖输入文件)
  --backup                自动备份原文件 (默认不备份)
  --summary               生成课程概要 (需要 also-merge 或调用外部逻辑)
  --verbose               显示详细处理信息
"""

import re
import os
import sys
import json
import copy

# ============================================================
# 常量与配置
# ============================================================

MAX_CHARS = 55        # 单条字幕最大字符数 (合并且过长时拆分)
MAX_TIME_MS = 12000   # 单条字幕最大时间跨度 (毫秒)

# ASR 错误修正映射表 (由用户根据课程内容扩展)
ASR_FIXES = {
    '大圆模型': '大语言模型',
    '大元模型': '大语言模型',
    '大圆': '大语言',
    '大元': '大语言',
    # 智谱课程实测：conda 的 ASR 误写
    '空大': 'conda',
    '框大': 'conda',
    # 智谱课程实测：TRAE（字节跳动 AI 编程工具）的 ASR/拼写误写
    # 注意：tree 不在此默认映射中（避免误伤"决策树"等），如课程中需要可用 --asr-fixes 传入
    'tray': 'TRAE',
    'trae': 'TRAE',
    # 注意：VB→Vibe 在下面的正则中处理
    # AI 编程课程实测（Karpathy / Vibe Coding 三层模型相关 ASR 误写）
    'capathy': 'Karpathy',
    'Kapathy': 'Karpathy',
    'authentic engineering': 'agentic engineering',
    'rap coding': 'vibe coding',
    "honey's engineering": 'harness engineering',
    # 中文 ASR 误写
    '角手器': '脚手架',
    # AI 编程工具名误写
    'codebody': 'WorkBuddy',
    'workbody': 'WorkBuddy',
    # AI 产品实践课程实测（Day3 字幕清洗新增）
    'TOKEN dance': 'TokenDance',   # 国内 AI 模型聚合平台（词元跳动）
    'Deepseek': 'DeepSeek',        # 模型厂商品牌大小写归一
    'vessel': 'Vercel',            # 部署平台 Vercel 的 ASR 误写（部署语境；vscode/resell 见 SKILL.md 语境说明）
    # 品牌名归一：奈势AI（中文品牌名）——"奈氏"为 ASR 误写；"NexAI"为英文拼写，字幕语境统一为中文品牌名
    # 注意：商务/官方文档"NexAI 奈势"联合署名时保留英文 NexAI，勿全局替换
    '奈氏AI': '奈势AI',
    '奈氏': '奈势AI',
    'NexAI': '奈势AI',
}

ASR_REGEX_FIXES = [
    (re.compile(r'(?i)vb\s*coding'), 'Vibe Coding'),
    (re.compile(r'(?i)v\s*v\s*b\s*coding'), 'Vibe Coding'),
    (r'v\s*b\s*coding', 'Vibe Coding'),
    # 智谱课程实测：greedy translate 的 ASR 拼写误写（Grady/grady）
    (re.compile(r'(?i)grady\s*translate'), 'greedy translate'),
]


# ============================================================
# 1. SRT 解析 / 格式化
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
            if i >= len(lines): break
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
    """SRT 时间戳 → 毫秒"""
    m = re.match(r'(\d{2}):(\d{2}):(\d{2}),(\d{3})', t.strip())
    if m:
        h, mi, s, ms = map(int, m.groups())
        return h * 3600000 + mi * 60000 + s * 1000 + ms
    return 0


def fmt_ms(ms):
    """毫秒 → SRT 时间戳"""
    ms = max(0, ms)
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'


def fmt_srt(blocks):
    """结构化数据 → SRT 格式字符串"""
    return ''.join(
        f"{b['idx']}\n{b['time']}\n{b['text']}\n\n" for b in blocks
    )


# ============================================================
# 2. 语气词清理
# ============================================================

def clean_fillers(text):
    """
    去除中文口语语气词和冗余表达。
    针对中文技术课程录音特征优化。
    """
    if not text:
        return text
    orig = text
    t = text

    # 2.1 纯口头禅 (独立出现)
    t = re.sub(r'[嗯呃诶哎噢哦哈](?=[，。！？；：、\s]|$)', '', t)

    # 2.1b 句首/标点后的独立语气词（后接汉字也删，如"嗯优秀的作业"→"优秀的作业"）
    t = re.sub(r'^[嗯呃诶哎噢哦]+', '', t)
    t = re.sub(r'([，。！？；：、])\s*[嗯呃诶哎噢哦]+', r'\1', t)
    # 句中"嗯"夹在两汉字之间（嗯不作构词语素，删除安全）
    t = re.sub(r'(?<=[一-鿿])嗯(?=[一-鿿])', '', t)

    # 2.2 啊 (全部删除)
    t = re.sub(r'\s*啊([，。！？；：、])', r'\1', t)
    t = re.sub(r'\s*啊$', '', t)
    t = re.sub(r'(^|[，。！？；：])\s*啊\s*', r'\1', t)
    t = re.sub(r'(\S)\s*啊(\S)', r'\1\2', t)

    # 2.3 呢 / 吧 / 啦 / 哟 / 噢 / 嘛
    for ch in '呢吧啦哟噢嘛':
        t = re.sub(r'\s*' + ch + r'([，。！？；：]|$)', r'\1', t)

    # 2.4 句首"那" → 删除 (除特殊情况)
    retain_after_na = '就是么个些里样能性种年天月时号周点位只次'
    t = re.sub(r'(^|[。！？])\s*那(?![' + retain_after_na + r']|是)', r'\1', t)
    t = re.sub(r'(^|[。！？])\s*那\s+', r'\1', t)
    t = re.sub(r'，\s*那\s+', '，', t)
    t = re.sub(r'(^|[。！？])\s*那(?=我们|大家|同学|咱们|自己|这|那)', r'\1', t)

    # 2.5 "这个" 填充词
    t = re.sub(r'(^|[，。！？；：])\s*这个\s*([，。！？；：]|$)', r'\1\2', t)
    t = re.sub(r'(的)这个', r'\1', t)                      # "今后的这个工作" → "今后的工作"
    t = re.sub(r'(叫做|称为|作为)这个', r'\1', t)            # "叫做这个提示词" → "叫做提示词"
    t = re.sub(r'(所谓的)这个', r'\1', t)                   # "所谓的这个" → "所谓的"
    t = re.sub(r'(进行|使用|采用|通过)这个', r'\1', t)       # "通过这个" → "通过"
    t = re.sub(r'(这些|那些|很多)这个', r'\1', t)            # "这些这个" → "这些"
    t = re.sub(r'(以及|和|与|跟)这个', r'\1', t)            # "和这个" → "和"
    # "这个" 后跟动词/副词 → 删除
    t = re.sub(
        r'这个(?=就|也|还|都|又|才|更|很|太|非常|比较|为了|因为|所以|不'
        r'|需要|能够|可以|应该|必须|进行|使用|想要|得到|叫做|称为|作为'
        r'|具体|主要|直接|分别)',
        '', t
    )
    t = re.sub(r'(比较|非常|十分|很|太|最)这个', r'\1', t)  # "非常这个" → "非常"

    # 2.6 "那个" 填充词
    t = re.sub(r'(^|[，。！？；：])\s*那个\s*([，。！？；：]|$)', r'\1\2', t)

    # 2.7 "这样" 冗余
    t = re.sub(r'的这样一个', '的', t)
    t = re.sub(r'是这样一个', '是', t)
    t = re.sub(r'在这样一个', '在这个', t)
    t = re.sub(r'(?<![是和在])\s*这样一个', '', t)
    t = re.sub(r'这样一些', '这些', t)
    t = re.sub(r'这样的一些', '这些', t)

    # 2.8 其他
    t = re.sub(r'比如说', '比如', t)
    t = re.sub(r'那实际上', '实际', t)
    t = re.sub(r'\s*呃\s*', '', t)
    t = re.sub(r'\s*[——-]\s*', '', t)

    # 2.9 清理多余空格和标点
    t = re.sub(r'\s+', ' ', t)
    t = re.sub(r'[，,]\s*[，,]', '，', t)
    t = re.sub(r'[。.]\s*[。.]', '。', t)
    t = re.sub(r'^[，,、；：]\s*', '', t)
    t = re.sub(r'[，,、；：]\s*$', '', t)
    t = t.strip()

    if not t or all(c in '，。！？、；：' for c in t):
        return orig
    return t


# ============================================================
# 3. ASR 错误修正
# ============================================================

def fix_asr_errors(text, extra_fixes=None):
    """
    修正常见的 ASR (语音识别) 错误。

    参数:
        extra_fixes: dict，额外的修正映射 {错误文本: 正确文本}
                     或 list of (pattern, replacement)
    """
    fixes = dict(ASR_FIXES)
    if extra_fixes:
        if isinstance(extra_fixes, dict):
            fixes.update(extra_fixes)

    # 1) 精确替换 (字典)
    for wrong, right in fixes.items():
        text = text.replace(wrong, right)

    # 2) 正则替换 (内置)
    for pattern, replacement in ASR_REGEX_FIXES:
        text = re.sub(pattern, replacement, text)

    # 3) 额外正则
    if extra_fixes and not isinstance(extra_fixes, dict):
        for pattern, replacement in extra_fixes:
            text = re.sub(pattern, replacement, text)

    return text


# ============================================================
# 4. 过短条目处理
# ============================================================

def fix_short_entries(blocks):
    """
    处理 ≤2 字的过短字幕条目。
    策略:
      - '啊', '嗯', '呢', '哦', '那' (纯语气词) → 删除
      - 其他 → 合并到上一条或下一条
    返回处理后的 blocks (原地修改)
    """
    # 预定义处理策略
    # key: 原始 idx, value: 'prev' 合并到上一条, 'next' 合并到下一条, 'delete' 删除
    actions = {}

    for b in blocks:
        text = b['text'].strip()
        if len(text) <= 2:
            if text in ('啊', '嗯', '呢', '哦', '噢', '诶', '哎', '哈', '啦'):
                actions[b['idx']] = 'delete'
            elif text in ('那',):
                actions[b['idx']] = 'delete'
            elif text in ('的', '了', '吗', '吧'):
                actions[b['idx']] = 'prev'  # 助词跟上一条
            elif text in ('所以', '比如', '还是', '就是', '现在', '然后', '但是', '因此'):
                actions[b['idx']] = 'next'  # 连词跟下一条
            elif text in ('简单', '复杂', '具体', '主要', '基本'):
                actions[b['idx']] = 'prev'  # 形容词跟上一条
            else:
                actions[b['idx']] = 'prev'  # 默认为跟上一条

    merged_set = set()
    i = 0
    while i < len(blocks):
        b = blocks[i]
        if b['idx'] in merged_set:
            i += 1
            continue

        action = actions.get(b['idx'])
        if action is None:
            i += 1
            continue

        if action == 'delete':
            b['text'] = '__DELETE__'
            i += 1
        elif action == 'prev':
            if i > 0:
                prev = blocks[i - 1]
                # 合并当前到上一条
                ps = prev['time'].split(' --> ')[0]
                pe = b['time'].split(' --> ')[1]
                prev['time'] = f'{ps} --> {pe}'
                prev['text'] = prev['text'] + b['text']
                b['text'] = '__DELETE__'
                merged_set.add(b['idx'])
            i += 1
        elif action == 'next':
            if i < len(blocks) - 1:
                nxt = blocks[i + 1]
                cs = b['time'].split(' --> ')[0]
                ne = nxt['time'].split(' --> ')[1]
                nxt['time'] = f'{cs} --> {ne}'
                nxt['text'] = b['text'] + nxt['text']
                b['text'] = '__DELETE__'
                merged_set.add(b['idx'])
                # 如果下一条也在 actions 里, 标记已处理
                if nxt['idx'] in actions:
                    merged_set.add(nxt['idx'])
            i += 1

    # 删除标记的条目
    blocks[:] = [b for b in blocks if b['text'] != '__DELETE__']
    # 重编号，保证 SRT 编号连续（删除/合并后 idx 会出现空号）
    for idx, b in enumerate(blocks, 1):
        b['idx'] = idx
    return blocks


# ============================================================
# 5. 断句合并 (可选)
# ============================================================

SENT_END = re.compile(r'[。！？]')
MUST_CONTINUE = re.compile(
    r'(需要|能够|可以|应该|必须|进行|使用|采用|通过|经过'
    r'|希望|开始|继续|要求|决定)$'
)
HANGING_PREP = re.compile(r'(把|将|让|給|给|替|被|从|在|关于|对于|通过|根据|按照|作为)$')
HANGING_CONJ = re.compile(r'(和|与|跟|同|及|或|或者|还是|并且)$')
ENDS_SHORT = re.compile(r'(一个|这个|那个|这些|那些|的|地|了|，)$')


def must_merge_with_next(text):
    """判断当前条目是否必须与下一条合并"""
    if not text:
        return True
    if SENT_END.search(text):
        return False
    if len(text) < 10:
        return True
    if MUST_CONTINUE.search(text):
        return True
    if HANGING_PREP.search(text):
        return True
    if HANGING_CONJ.search(text):
        return True
    if ENDS_SHORT.search(text) and len(text) < 25:
        return True
    # 以对象代词结尾短句 (需续接动词)
    if len(text) < 18 and not text[-1] in '。！？；：':
        if re.search(r'(这个|那个|这些|那些|一个|一些|某种)$', text):
            return True
        if re.search(r'[的把地了]$', text):
            return True
        if re.search(r'(给它|将其|把它|对他|对它|对其)$', text):
            return True
    return False


def merge_sentences(blocks, max_chars=MAX_CHARS, max_time_ms=MAX_TIME_MS):
    """智能合并断句 (原地修改 blocks)"""
    result = []
    i = 0
    while i < len(blocks):
        cur = blocks[i]
        # 检查是否需要合并
        if i + 1 < len(blocks) and must_merge_with_next(cur['text']):
            st = cur['time'].split(' --> ')[0]
            sm = parse_ms(st)
            texts = [cur['text']]
            et = cur['time'].split(' --> ')[1]
            j = i + 1
            while j < len(blocks):
                bj = blocks[j]
                # 检查合并后长度
                if len(''.join(texts + [bj['text']])) > max_chars:
                    break
                # 检查时间跨度
                ejm = parse_ms(bj['time'].split(' --> ')[1])
                if ejm - sm > max_time_ms and len(''.join(texts)) > 25:
                    break
                texts.append(bj['text'])
                et = bj['time'].split(' --> ')[1]
                # 当前句完整且够长 → 停
                if SENT_END.search(bj['text']) and len(''.join(texts)) > 20:
                    # 但下一句若也需要合并则继续
                    if j + 1 < len(blocks) and must_merge_with_next(bj['text']):
                        j += 1
                        continue
                    j += 1
                    break
                # 下一条是新句子 → 停
                if j + 1 < len(blocks):
                    nn = blocks[j + 1]['text']
                    if re.match(
                        r'^(那[么]?|所以|因此|但是|接下来|最后|首先|本节课|那好吧|以上)',
                        nn
                    ) and len(''.join(texts)) > 20:
                        j += 1
                        break
                j += 1

            merged = clean_fillers(''.join(texts))
            merged = re.sub(r'\s+', ' ', merged).strip()
            ei = min(j - 1, len(blocks) - 1)
            result.append({
                'idx': 0,
                'time': f"{st} --> {blocks[ei]['time'].split(' --> ')[1]}",
                'text': merged
            })
            i = ei + 1
        else:
            result.append({'idx': 0, 'time': cur['time'], 'text': cur['text']})
            i += 1

    # 重编号
    for idx, b in enumerate(result, 1):
        b['idx'] = idx

    blocks[:] = result
    return blocks


# ============================================================
# 6. 字幕加工主流程
# ============================================================

def export_to_desktop(content, filename, verbose=False):
    """
    将清理后的字幕导出为 .srt 文件到桌面。

    参数:
        content: SRT 格式字符串
        filename: 原始文件名 (如 '智谱1.3.md')
    """
    import shutil
    desktop_dir = os.path.expanduser('~/Desktop')
    srt_name = os.path.splitext(os.path.basename(filename))[0] + '.srt'
    desktop_path = os.path.join(desktop_dir, srt_name)
    with open(desktop_path, 'w', encoding='utf-8') as f:
        f.write(content)
    if verbose:
        print(f"   🖥️  SRT 已导出到桌面: {desktop_path}")
    return desktop_path


def process_file(
    filepath,
    output_path=None,
    clean_fillers_flag=True,
    fix_asr_flag=True,
    fix_short_flag=True,
    merge_flag=False,
    asr_extra_fixes=None,
    verbose=False,
    export_desktop=True
):
    """
    执行完整的字幕加工流水线。

    返回 dict:
        before:     原条目数
        after:      处理后条目数
        cleaned:    语气词清理条目数
        short_fixed: 过短处理条目数
        merges:     断句合并处数
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    blocks = parse_srt(content)
    stats = {'before': len(blocks)}
    if verbose:
        print(f"📖 原始: {len(blocks)} 条")

    # Step 1: 语气词清理
    if clean_fillers_flag:
        n_cleaned = 0
        for b in blocks:
            c = clean_fillers(b['text'])
            if c != b['text']:
                n_cleaned += 1
            b['text'] = c
        stats['cleaned'] = n_cleaned
        if verbose:
            print(f"🧹 语气词清理: {n_cleaned}/{len(blocks)} 条")

    # Step 2: ASR 错误修正
    if fix_asr_flag:
        n_fixed = 0
        for b in blocks:
            c = fix_asr_errors(b['text'], asr_extra_fixes)
            if c != b['text']:
                n_fixed += 1
            b['text'] = c
        stats['asr_fixed'] = n_fixed
        if verbose:
            print(f"🔧 ASR 修正: {n_fixed} 处")

    # Step 3: 过短条目处理
    if fix_short_flag:
        before = len(blocks)
        fix_short_entries(blocks)
        stats['short_fixed'] = before - len(blocks)
        if verbose:
            print(f"✂️  过短处理: 删除了 {stats['short_fixed']} 条")

    # Step 4: 断句合并
    if merge_flag:
        before = len(blocks)
        merge_sentences(blocks)
        stats['merges'] = before - len(blocks)
        if verbose:
            print(f"🔗 断句合并: {stats['merges']} 处")

    # 输出
    stats['after'] = len(blocks)
    if not output_path:
        output_path = filepath
    # 如果输出和输入相同且需备份
    if output_path == filepath:
        backup_path = filepath + '.bak'
        import shutil
        if not os.path.exists(backup_path):
            shutil.copy2(filepath, backup_path)
            if verbose:
                print(f"💾 备份已创建: {backup_path}")

    output = fmt_srt(blocks)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(output)

    # 导出到桌面 (除非明确跳过)
    if export_desktop:
        export_to_desktop(output, filepath, verbose)

    if verbose:
        red = int((1 - stats['after'] / stats['before']) * 100) if stats['before'] > 0 else 0
        print(f"✅ 完成: {stats['before']} → {stats['after']} (缩减 {red}%)")

    return stats


# ============================================================
# 7. 课程概要生成辅助
# ============================================================

def extract_section_boundaries(blocks, keywords):
    """
    根据关键词列表识别章节边界。

    参数:
        keywords: list of (section_title, [keywords])

    返回:
        list of (section_title, start_block_idx, end_block_idx)
    """
    boundaries = []
    text_blocks = [(i, b['text']) for i, b in enumerate(blocks)]

    for title, kws in keywords:
        start = None
        for i, txt in text_blocks:
            if any(kw in txt for kw in kws):
                if start is None:
                    start = i
        if start is not None:
            boundaries.append((title, start))

    # 排序并生成区间
    boundaries.sort(key=lambda x: x[1])
    sections = []
    for j, (title, start) in enumerate(boundaries):
        end = boundaries[j + 1][1] if j + 1 < len(boundaries) else len(blocks)
        sections.append((title, start, end))

    return sections


def get_block_text_range(blocks, start, end):
    """获取指定范围内的连续文本"""
    texts = [blocks[i]['text'] for i in range(start, min(end, len(blocks)))]
    return ' '.join(texts)


# ============================================================
# CLI 入口
# ============================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='字幕加工流水线 — 清理语气词、修正 ASR 错误、合并过短条目',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('input', help='输入的 SRT/.md 字幕文件路径')
    parser.add_argument('-o', '--output', help='输出文件路径 (默认覆盖输入)')
    parser.add_argument('--only-clean', action='store_true',
                        help='仅清理语气词，不做合并')
    parser.add_argument('--also-merge', action='store_true',
                        help='清理后做断句合并')
    parser.add_argument('--no-asr', action='store_true',
                        help='跳过 ASR 错误修正')
    parser.add_argument('--no-short', action='store_true',
                        help='跳过过短条目处理')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='显示详细处理信息')
    parser.add_argument('--asr-fixes', help='额外 ASR 修正 JSON 文件路径'
                        ' (格式: {"错误文本": "正确文本"})')

    args = parser.parse_args()

    # 加载额外 ASR 修正
    extra_fixes = None
    if args.asr_fixes:
        with open(args.asr_fixes, 'r', encoding='utf-8') as f:
            extra_fixes = json.load(f)

    merge_flag = args.also_merge
    if args.only_clean:
        merge_flag = False

    stats = process_file(
        filepath=args.input,
        output_path=args.output,
        clean_fillers_flag=True,
        fix_asr_flag=not args.no_asr,
        fix_short_flag=not args.no_short,
        merge_flag=merge_flag,
        asr_extra_fixes=extra_fixes,
        verbose=args.verbose
    )

    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
