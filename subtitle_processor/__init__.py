# subtitle-processor
# 中文课程字幕加工流水线

from .core import (
    parse_srt,
    fmt_srt,
    clean_fillers,
    fix_asr_errors,
    fix_short_entries,
    merge_sentences,
    process_file,
)
