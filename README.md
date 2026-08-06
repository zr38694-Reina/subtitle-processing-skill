# subtitle-processing-skill

**中文课程字幕加工流水线** — 清理语气词、修正 ASR 错误、合并断句、生成课程概要。

适用于所有 AI 工具和开发者。支持 Claude Skill 系统，也可作为独立命令行工具使用。

---

## ✨ 功能

| 步骤 | 说明 | 可选 |
|------|------|:----:|
| 🧹 **语气词清理** | 删除口语填充词（啊、那、这个、呢、吧、哦、嗯、呃等） | 默认 |
| 🔧 **ASR 错误修正** | 修正常见语音识别错误（大圆/大元→大语言模型，VB→Vibe Coding） | 默认 |
| ✂️ **过短条目合并** | 将 ≤2 字的字幕条目合并到相邻条目或直接删除 | 默认 |
| 🔗 **断句合并** | 将不合理破碎的句子合并为完整语句，同步修正时间轴 | `--also-merge` |
| 📝 **课程概要生成** | 从清理后的字幕提取章节结构，生成知识点总结文档 | 手册指导 |
| 📋 **选择题生成** | 整理完课程概要后自动出 5 道选择题（含参考答案），用于复习考核 | 默认 |

## 🚀 快速安装

### 方式一：一键安装（推荐）

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/zr38694-Reina/subtitle-processing-skill/main/install.sh)
```

### 方式二：pip 安装

```bash
pip install git+https://github.com/zr38694-Reina/subtitle-processing-skill.git
```

### 方式三：手动

```bash
git clone https://github.com/zr38694-Reina/subtitle-processing-skill.git
cd subtitle-processing-skill
pip install -e .
```

## 📖 使用

### 命令行工具

安装后即可全局使用 `subtitle-process` 命令：

```bash
# 最常用：语气词清理 + ASR修正 + 过短处理
subtitle-process 字幕文件.md -v

# 完整流水线（含断句合并）
subtitle-process 字幕文件.md --also-merge -v

# 仅清理（不做任何合并）
subtitle-process 字幕文件.md --only-clean -v

# 指定输出文件
subtitle-process 字幕文件.md --only-clean -o 清理后字幕.md

# 带自定义 ASR 修正
subtitle-process 字幕文件.md --asr-fixes fixes.json -v

# 跳过 ASR 修正
subtitle-process 字幕文件.md --no-asr -v
```

### Python 模块方式

```bash
python3 -m subtitle_processor 字幕文件.md -v
```

### 在代码中调用

```python
from subtitle_processor import process_file

stats = process_file(
    filepath="课程字幕.md",
    clean_fillers_flag=True,
    fix_asr_flag=True,
    fix_short_flag=True,
    merge_flag=False,     # 设为 True 启用断句合并
    verbose=True,
)
print(stats)
# {'before': 951, 'after': 935, 'cleaned': 672, ...}
```

### 自定义 ASR 修正

创建一个 JSON 文件，传入 `--asr-fixes`：

```json
{
  "大圆模型": "大语言模型",
  "向量数据苦": "向量数据库",
  "MCT协议": "MCP协议",
  "Funtion Coring": "Function Calling"
}
```

```bash
subtitle-process 字幕.md --asr-fixes my_fixes.json -v
```

## 📋 根据课程概要生成选择题（默认自动）

`/subtitle` 完整流程在生成课程概要后，会**自动**接着出 5 道选择题（四选一 + 参考答案），用于复习与考核。该步骤由 AI 完成，属于工作流的一部分：

1. 读取 `课程大纲汇总/{课程名} {章节号} {章节标题}-课程概要.md`
2. 按章节提炼考点（概念定义、模型对比、流程步骤、注意事项）
3. 生成 5 道选择题：干扰项"似对实错"，附参考答案与出处
4. 保存到 `{课程名}/选择题/{课程名} {章节号} {章节标题}-选择题.md`
5. 可选：导出一份到 `~/Desktop/`

如需**跳过出题**（仅清理 + 概要），用 `/subtitle clean`；仅对已有概要出题用 `/subtitle quiz`。完整模板见 `SKILL.md`「第四步」。

## 🔌 作为 AI Skill 使用

本工具可与多种 AI 平台配合。

### Claude（推荐）

将 `SKILL.md` 放入 Claude skills 目录：

```bash
mkdir -p ~/.claude/skills
ln -sfn $(pwd) ~/.claude/skills/subtitle-processing
```

之后在 Claude 中提及「字幕清理、SRT 处理、课程概要」等关键词时，Claude 会自动加载本 Skill。

### Cursor / Windsurf / 其他 AI IDE

AI IDE 支持调用 Python 脚本和读取 Markdown 文档。可以将本仓库克隆到项目中，通过 `subtitle-process` 命令或直接查看 `SKILL.md` 中的工作流指导来协作处理字幕。

### GitHub Copilot / 通用 AI 助手

AI 助手可读取 `SKILL.md` 了解工作流，通过 `subtitle-process` 命令行工具执行具体操作。工作流分为六步：

1. 运行 `subtitle-process` 进行自动清理
2. 人工检查语气词/ASR 残留
3. 生成课程概要
4. 自动根据课程概要生成选择题
5. 输出 SRT / 概要到桌面
6. 最终检查与交付

详情见 `SKILL.md` 中的完整指导。

## 🛠 依赖

- **Python 3.8+**
- **无需第三方库** — 全部使用 Python 标准库

## 📁 项目结构

```
subtitle-processing-skill/
├── SKILL.md                       # AI Skill 主文档（工作流指导）
├── README.md                      # 本文件
├── Makefile                       # 常用命令（install, test, build）
├── install.sh                     # 一键安装脚本
├── pyproject.toml                 # Python 包配置
├── evals.json                     # 测试用例
└── subtitle_processor/            # Python 包
    ├── __init__.py
    ├── __main__.py                # python3 -m 入口
    ├── cli.py                     # 命令行入口
    └── core.py                    # 核心逻辑（发音词清理/ASR修正/合并）
```

## 📄 许可证

MIT
