#!/usr/bin/env bash
# subtitle-processing-skill 一键安装脚本
set -e

REPO_URL="https://github.com/zr38694-Reina/subtitle-processing-skill"
INSTALL_DIR="${HOME}/.local/share/subtitle-processor"

echo "📦 安装 subtitle-processor（字幕加工流水线）"
echo ""

# 检测 Python
if command -v python3 &>/dev/null; then
    PYTHON=python3
elif command -v python &>/dev/null; then
    PYTHON=python
else
    echo "❌ 未找到 Python，请先安装 Python 3.8+"
    exit 1
fi

echo "✅ 使用 Python: $($PYTHON --version)"

# 克隆或更新
if [ -d "$INSTALL_DIR" ]; then
    echo "📂 更新已有安装..."
    cd "$INSTALL_DIR"
    git pull
else
    echo "📥 克隆仓库..."
    mkdir -p "$(dirname "$INSTALL_DIR")"
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# pip 安装
echo "🔧 安装 Python 包..."
$PYTHON -m pip install -e . --quiet

# Claude Skill 安装（可选）
if [ -d "${HOME}/.claude/skills" ]; then
    echo "🔗 链接到 Claude Skills..."
    ln -sfn "$INSTALL_DIR" "${HOME}/.claude/skills/subtitle-processing"
    echo "   → ~/.claude/skills/subtitle-processing"
fi

echo ""
echo "🎉 安装完成！"
echo ""
echo "使用方法:"
echo "  subtitle-process 字幕文件.md -v              # 清理语气词 + ASR修正"
echo "  subtitle-process 字幕文件.md --also-merge -v  # 完整流水线"
echo "  subtitle-process --help                       # 查看全部选项"
echo ""
echo "Python 模块方式:"
echo "  python3 -m subtitle_processor 字幕文件.md -v"
echo ""
echo "更多信息: $REPO_URL"
