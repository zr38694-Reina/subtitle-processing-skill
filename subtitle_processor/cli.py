#!/usr/bin/env python3
"""
subtitle-process — 字幕加工命令行工具

安装后全局使用:
  subtitle-process 字幕文件.md -v
  subtitle-process 字幕文件.md --also-merge -v
  subtitle-process 字幕文件.md --only-clean --output 清理后.md

也可通过 Python 模块调用:
  python3 -m subtitle_processor 字幕文件.md --only-clean -v
"""

import sys
import json
import argparse

from .core import process_file


def main():
    parser = argparse.ArgumentParser(
        prog='subtitle-process',
        description='字幕加工流水线 — 清理语气词、修正 ASR 错误、合并过短条目',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  subtitle-process 字幕.md -v                        # 语气词清理 + ASR修正 + 过短处理
  subtitle-process 字幕.md --also-merge -v            # 完整流水线（含断句合并）
  subtitle-process 字幕.md --only-clean -o 输出.md     # 仅清理，输出到新文件
  subtitle-process 字幕.md --asr-fixes fixes.json -v  # 带自定义ASR修正
        """,
    )
    parser.add_argument('input', help='输入的 SRT/.md 字幕文件路径')
    parser.add_argument('-o', '--output', help='输出文件路径（默认覆盖输入）')
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
    parser.add_argument('--no-export-desktop', action='store_true',
                        help='不导出 SRT 到桌面')
    parser.add_argument('--asr-fixes', type=str,
                        help='额外 ASR 修正 JSON 文件路径'
                        '（格式: {"错误文本": "正确文本"}）')

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
        verbose=args.verbose,
        export_desktop=not args.no_export_desktop,
    )

    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
