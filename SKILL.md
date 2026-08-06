---
name: subtitle-processing
command: subtitle
description: >-
  【/subtitle 命令】输入 /subtitle 直接执行字幕清理流水线（含课程概要生成）：
  语气词删除 + ASR 错误修正 + 过短条目处理 + 按章节输出概要文档。
  命令格式：/subtitle（完整流程+概要）/subtitle clean（仅清理）。
  也适用于任何 AI 工具处理 SRT / .md 格式的课程字幕。
  当用户提及 字幕、SRT、语音转写、课程概要、字幕清理、语气词、ASR 错误 时触发。
---

# 字幕加工流水线（通用工作流文档）

## /subtitle 命令说明

**输入 `/subtitle` 后，直接执行字幕清理流水线（含课程概要生成）：**

1. ✅ 语气词清理（啊、那、这个、呢、吧等）
2. ✅ ASR 错误修正（大圆→大语言、VB→Vibe Coding 等）
3. ✅ 过短条目处理（≤2 字的条目自动移除）
4. ✅ 原始文件备份（`.bak`）
5. ✅ **生成课程概要文档** — 阅读清理后的字幕，按章节提取知识点，输出到 `课程大纲汇总/` 目录
6. ✅ **输出 SRT 到桌面** — 将清理后的字幕导出为 `.srt` 格式保存到 `~/Desktop/`
7. ✅ **输出概要到桌面** — 将课程概要文档同样输出一份到 `~/Desktop/`

**使用方式：**

| 输入 | 效果 |
|------|------|
| `/subtitle` | 自动识别当前笔记或询问要处理的文件 → 执行清理流水线 + 生成概要 |
| `/subtitle 文件名.md` | 直接处理指定文件 + 生成概要 |
| `/subtitle clean 文件名.md` | 仅清理（不做概要生成） |

**处理流程：**

当触发时：
1. 确定字幕文件路径（从 `<current_note>` 推断，或询问用户）
2. 调用 `subtitle-process` 命令执行脚本（`--only-clean` 模式）
3. 报告处理结果（原条目数 → 处理后条目数，缩减比例）
4. **生成课程概要文档** — 阅读清理后的字幕，识别章节边界，提取关键知识点
5. 输出概要文档到 `课程大纲汇总/` 目录，命名格式：`{课程名} {章节号} {章节标题}-课程概要.md`
6. **导出 SRT 到桌面** — 将清理后的字幕转换为 `.srt` 格式并保存到 `~/Desktop/`
7. **导出概要到桌面** — 将课程概要 `.md` 文档也保存一份到 `~/Desktop/`

## 概述

输入：SRT 格式课程字幕（`.md` 或 `.srt` 文件）
输出：清理后的字幕 + 可选课程概要文档

核心流水线步骤：

```
原始字幕 → 语气词清理 → ASR 错误修正 → 过短条目处理 → [可选生成概要] → SRT + 概要到桌面 → 交付
```

---

## 第一步：自动化清理

### 安装

```bash
# 一键安装
bash <(curl -fsSL https://raw.githubusercontent.com/zr38694-Reina/subtitle-processing-skill/main/install.sh)

# 或 pip 安装
pip install git+https://github.com/zr38694-Reina/subtitle-processing-skill.git
```

### 使用

```bash
# 语气词清理 + ASR修正 + 过短处理（最常用）
subtitle-process 字幕文件.md -v

# 仅清理（不做任何合并）
subtitle-process 字幕文件.md --only-clean -v

# 带自定义 ASR 修正
subtitle-process 字幕文件.md --asr-fixes fixes.json -v

# 查看全部选项
subtitle-process --help
```

### 参数速查

| 参数 | 效果 |
|------|------|
| `-v` / `--verbose` | 显示处理详情 |
| `--only-clean` | 仅清理语气词，不做概要生成 |
| `--asr-fixes fixes.json` | 加载自定义 ASR 修正规则 |
| `--no-asr` | 跳过 ASR 错误修正 |
| `--no-short` | 跳过过短条目处理 |
| `-o 输出文件.md` | 指定输出路径 |
| `--no-export-desktop` | 不自动导出 SRT 到桌面 |

---

## 第二步：人工检查与补充修正

### 2.1 语气词残留检查

扫描文件中是否还有不应保留的语气词：

| 语气词 | 处理方式 | 示例 |
|--------|---------|------|
| **啊** | 几乎 100% 为填充词，删除 | "同学们啊" → "同学们" |
| **这个/那个** | 做指示词时保留（"这个问题"），做填充词时删除（"这个……我们需要"） | — |
| **那** | 句首填充词全部删除 | "那我们开始" → "我们开始" |
| **呢/吧/哦/嗯/呃** | 全部为语气词，删除 | — |

> **注意**：句首或标点后的 `嗯/呃/哦/诶` 即使后接汉字（如"嗯优秀的作业"）也应删除；`哈` 除外（保留"哈喽"）。脚本 2.1b 规则已覆盖。

### 2.2 ASR 错误检查

中文技术课程常见的 ASR 错误模式：

| 常见错误 | 正确形式 | 原因 |
|---------|---------|------|
| 大圆模型 / 大元模型 | 大语言模型 | 快速发音"大语言"听似"大圆" |
| VB coding / v v b coding | Vibe Coding | AI 编程范式术语 |
| 向量数据苦 | 向量数据库 | 常见于 RAG 课程 |
| MCT 协议 | MCP 协议 | 模型上下文协议 |
| tray / trae / tree | TRAE | 字节跳动 AI 编程工具（Trae），ASR 听写/拼写错误，统一全大写 `TRAE` |
| 空大 / 框大 | conda | Python 环境管理工具，中文发音"conda"听似"空大" |
| Grady translate / grady translate | greedy translate | 贪心解码/贪心翻译（greedy translate），ASR 拼写误写 |
| job（dropout/训练语境） | drop | dropout 的 ASR 误写（"把 job 里边的参数"→"把 drop 里边的参数"）；**仅在 Transformer 训练/推理语境修正**，勿误伤 job description（JD 岗位描述）等正常用法 |
| Web coding / webcording | Vibe Coding | Karpathy 2025 年提出的 AI 编程范式，ASR 听似"Web coding"；**仅在 AI 编程/Vibe Coding 语境修正**，避免误伤"Web 开发"类课程 |
| capathy / Kapathy | Karpathy | OpenAI 创始成员、提出 Vibe Coding 的 Andrej Karpathy 的 ASR 误写 |
| authentic engineering | agentic engineering | Karpathy 提出的 AI 编程第二层概念（做对），ASR 误写 |
| rap coding | vibe coding | Karpathy 三层模型第一层（先做出来），ASR 误写 |
| honey's engineering | harness engineering | 给模型加"马鞍脚手架"的 harness 工程，ASR 误写 |
| 角手器 | 脚手架 | "脚手架"的中文 ASR 误写（harness 语境） |
| 柯泽 | Cursor | 口语"Cursor"音译误写（IDE 语境） |
| codebody / workbody / work body | WorkBuddy | AI 编程/工作工具 WorkBuddy，ASR 拼写误写（勿误为 CodeBuddy）；`work body` 仅在 AI 工具名语境修正，避免误伤"工作主体"等正常用法 |
| TOKEN dance | TokenDance | 国内 AI 模型聚合 API 平台（词元跳动，观猹/Watcha 出品），ASR 听写误写 |
| Deepseek | DeepSeek | AI 模型厂商品牌 DeepSeek，大小写归一 |
| vessel（部署语境） | Vercel | AI 应用部署平台 Vercel 的 ASR 误写（部署/上线语境）；`vscode` / `resell` / `Resso` 同为此误写，仅在部署语境修正 |

**智谱课程实测修正（可直接复用）：**
- **TRAE**：`tray` / `trae` / `tree` 均为 AI 编程工具 Trae 的误写，统一改为全大写 `TRAE`。注意 `tree` 仅在 AI 编程工具语境下修正（如"cursor ... tree"），避免误伤"决策树"等正常词汇。
- **conda**：`空大` / `框大` 均为 Python 环境管理工具 conda 的误写，统一改为 `conda`（如"空大环境"→"conda环境"、"空大DL"→"condaDL"）。

**AI 产品经理共创营课程实测修正（可直接复用）：**
- **Vibe Coding**：`Web coding` / `webcording` 均为 Vibe Coding 的 ASR 误写（如"Web coding和直接让ChatGPT写代码是一回事吗"）。**仅在 AI 编程课程语境下修正**，避免误伤真正的"Web 开发"课程。
- **人名归一**：同一主讲人常出现多个称呼变体（如 傲游 / 欧优 / 欧阳 / 欧欧 / 奥威 / 瑶瑶 / 欧老师 / 林老师），需按课程统一为真实称呼（本课统一为"林老师"）。注意多词组合（如"傲游老师"）可能被断句隔开，需同时处理独立词片段（如"傲游"→"林"）。

**Day2 课程实测修正（AI 狼人杀 / HTML 原型课，可直接复用）：**
- **Codex**（OpenAI AI agent 工具名）：ASR/拼写误写极多，统一为全大写 `Codex`——`callx` / `callbacks` / `callouts` / `collect`(含 `collection`) / `collex` / `Colex` / `Codec` / `codec`。**仅在本课程（讲 Codex 实操）语境修正**；注意 `collection` 要先于 `collect` 替换，避免拼成 `Codexion`。
- **Next.js**：`next点js` / `next点JS` / `next点Js`（中文"点"=英文句点）统一为 `Next.js`。
- **Suno**：`速诺` / `素诺` 均为 AI 音乐生成工具 Suno 的中文音译误写。
- **GPT Image 2**：`GPT IMAGE2` / `GPT2` 均为 OpenAI 图像生成模型的误写（在生图语境）。
- **OpenRouter**：`open Router` 为 AI 模型聚合平台 OpenRouter 的误写。
- **Selector**：`Slater` 为浏览器元素选择器小工具 Selector 的音译误写。
- **SVG**：`s SVG` → `SVG`（"用s SVG的方式"→"用SVG的方式"）。
- **DuMate**：`do Mate` → `DuMate`（国产 AI agent 工具名）。

**Day3 课程实测修正（AI 产品实践 / 接入 API + 部署上线课，可直接复用）：**
- **Vercel**（部署平台）：ASR 误写极多——`vessel` / `resell` / `Resso` / `vscode`（部署语境）统一为 `Vercel`。**仅在部署/上线语境修正**，勿误伤 VS Code 编辑器等正常用法。
- **Werewolf**（AI 狼人杀项目名）：`wolfcha` / `wolfchat` / `warroof` 统一为 `Werewolf`（项目/域名语境，如"warroof.com"→"Werewolf.com"）。
- **TokenDance**：`TOKEN dance` → `TokenDance`（国内 AI 模型聚合平台，见 2.2 表）。
- **奈势AI**（中文品牌名）：`奈氏` / `奈氏AI` → `奈势AI`（ASR 误写，如"是奈氏AI的共创者"→"是奈势AI的共创者"）；`NexAI` 为英文品牌拼写，字幕语境统一为中文品牌名 `奈势AI`（如"是NexAI的共创者"→"是奈势AI的共创者"）。**注意**：官方/商务文档常用"NexAI 奈势"联合署名，此时保留英文 `NexAI`，勿在商务语境全局替换。
- **DeepSeek**：`Deepseek` → `DeepSeek`（品牌大小写归一）。
- **人名/演示名归一**：直播对话中的示例用户名（如 Codex 演示里"我叫 Alloy"）常被 ASR 写成 `好友` / `OIO` / `欧呦` / `欧友`，需统一为正确拼写 `Alloy`。

**AI影视短片导演课（大鹏 AIGC 课程）1.2 三幕式剧本创作 实测修正（可直接复用）：**
- **三幕式 系列**：`三目式` / `三目表` / `三目线` 均为"三幕"的 ASR 误写（影视剧本语境，如"完善三目表"→"完善三幕表"、"三目线"→"三幕线"）。已加入默认映射。
- **催化**：`崔化` 为"催化"（催化剂/催化事件）的 ASR 误写（如"崔化美故事启动"→"催化 故事启动"）。已加入默认映射。
- **人物弧光**：`人物湖光` → `人物弧光`（角色开始与结尾的变化，课程重点概念；"湖光"为 ASR 误写）。已加入默认映射。
- **Markdown**：`马上格式` → `Markdown格式`（"马上"为 Markdown 的 ASR 误写）。已加入默认映射。
- **文件扩展名（中文"点"=英文句点）**：`点MD` / `点my` → `.md`，`点zip` → `.zip`。已加入默认映射。
- **skill（AI 创作/skill 制作语境）**：`scale` / `SQL` 均为 skill 的 ASR 误写（如"把这个scale复制一下"→"把这个skill复制一下"、"优化SQL"→"优化skill"、"完整的SQL文件"→"完整的skill文件"）。**仅在 AI 创作/skill 制作语境修正**，勿误伤 SQL 数据库、scale 规模化等正常用法。
- **其他语境修正（仅本课）**：`崔花钱`→`催化型`（青春电影催化型故事）；`一2和5`→`1、2和5`；`大战一枚鞭炮`→`点燃一枚鞭炮`（功夫案例）；`MMD格式`→`.md格式`；`5定定股价`→`五问定框架`；`知识库的cal`→`知识库的调用`；`是就是`→`就是`（叠词）。

**AI影视短片导演课（大鹏 AIGC 课程）1.3 15 Beats 与 Story Circle 实测修正（可直接复用）：**
- **15 Beats（救猫咪节拍法）系列**：`10五Beats` / `15B4` / `15B子` 均为"15 Beats"的 ASR 误写（影视剧本语境，如"他们是10五Beats"→"他们是15 Beats"）。其中 `10五Beats` / `15B4` / `15B子` 已加入默认映射；`15bit` 因可能误伤"15-bit"（位深/ADC 等技术词汇）**仅在本课 fixes.json 修正**，勿加入默认。
- **故事环（Story Circle）系列**：`顾传` / `顾志环` / `故事魂` / `人物环` 均为"故事环"的 ASR 误写（如"顾传我们在运用这个15 Beats"→"故事环我们在运用这个15 Beats"、"顾志环的评分9.5分"→"故事环的评分9.5分"）。**仅在本课 fixes.json 修正**，避免误伤人名"顾传/志环"及"故事魂"等正常用法。
- **救猫咪（Save the Cat）**：`兽必死救猫咪` → `救猫咪`（"兽必死"为英文书名 Save the Cat 的音译误写）。仅本课修正。
- **节拍名语境修正（仅本课）**：`调目切入点`→`第二幕衔接点`（15 Beats 第 6 拍）；`黄昏黑夜`→`灵魂黑夜`（第 12 拍，同课 1.2 人物湖光式误写）；`催化剂激励受谏`→`催化剂激励事件`（激励事件 = inciting incident）；`是剧写的`→`一无所有`（第 11 拍，AI 节拍清单快速朗读误写）；`重视画面`→`终场画面`（第 15 拍）；`游戏时间终点`→`游戏时间、中点`（第 8、9 拍连读）。均按 15 拍顺序推断，仅在节拍清单语境修正。

**AI影视短片导演课（大鹏 AIGC 课程）1.5 海报产品图与主视觉的生成 实测修正（可直接复用）：**
- **GPT Image 2**：`image two` / `image to` 均为 GPT Image 2 模型的 ASR 误写（如"image two和Nano Banana Pro"→"Image 2和Nano Banana Pro"、"GPT image to锁定"→"GPT Image 2锁定"）。`image two` / `GPT image to` / `GPT的image to` 已加入默认映射；**注意**"image to image（图生图）"等正常英文短语避免误伤。
- **管口**：`光口` → `管口`（护肤品/化妆品管身开口，如"光口挤出一大坨"→"管口挤出一大坨"）。已加入默认映射。
- **skill 拼写误写**：`SKLL` / 分开书写的 `S K I L l` 均为 skill 的拼写误写（如"文生图SKLL杠2"→"文生图SKILL杠2"）。已加入默认映射；`skil` 因是 `skill` 的子串**不要单独加入映射**（会把正确词变 `skilll`），需用短语或上下文处理。
- **TVC（电视广告）**：`TV c` → `TVC`（如"你是一个TV c光影指导"→"你是一个TVC光影指导"）。已加入默认映射。
- **模型名大小写归一**：`GPT4O` → `GPT-4o`（旧模型引用，如"针对于GPT4O"→"针对于GPT-4o"）。已加入默认映射。
- **品牌名归一**：`ichange` → `iChange`（本课护肤品品牌 iChange）。已加入默认映射。
- **Markdown 简写展开**：`MD格式` → `Markdown格式`（如"设计的MD格式"→"设计的Markdown格式"）。已加入默认映射；`design MD` / `设计MD` → `design Markdown` / `设计Markdown` 仅本课 fixes.json 修正。
- **仅本课 fixes.json 修正**：`SQL` → `skill`（AI 创作/skill 制作语境，如"在我的SQL中加入视觉方案"→"在我的skill中加入视觉方案"）；`使用我上传的skil` → `使用我上传的skill`（`skil` 为 `skill` 子串，用完整短语替换）。**勿**将 `SQL` 加入默认映射，避免误伤 SQL 数据库。
- **遗留未改**：平台名 `Livetv`（本课生图平台，无法确认正确名称）；`维生素CQ` / `维生素t`（上节课 skill 名/提示词的 ASR 严重误写，无法可靠还原）——如后续确认再补。

**做法：** 逐段阅读发现错误后：
1. 创建课程专用的 `fixes.json`
2. 运行 `subtitle-process 字幕.md --asr-fixes fixes.json -v`

### 2.3 过短条目检查

确认脚本已将 ≤2 字的条目处理完毕。如发现遗漏，手动合并。

---

## 第三步：生成课程概要（可选）

### 识别章节边界

阅读清理后的字幕，寻找以下分段信号：

| 信号词 | 含义 |
|--------|------|
| "接下来我们介绍…" | 新话题开始 |
| "我们先来了解一下…" | 新知识点 |
| "第一种/第二种/第三种" | 子主题枚举 |
| "介绍完了XX，我们接下来…" | 话题切换 |
| "本节课需要牢记的知识点有…" | 知识总结 |
| "我们来实践一下" | 实战环节 |
| "本节课的内容就到这里" | 结束 |

### 概要文档结构

每个小节包含：
- **小节标题** — 核心主题
- **关键概念** — 定义、原理、要点（列表形式）
- **示例** — 课程中的具体例子（如有）
- **代码/工具** — 涉及的工具、库、API（如有）
- **最佳实践 / 注意事项** — 课程总结的要点

### 文档格式

```markdown
# 课程名称 — 章节标题

> 课程概要 · 基于课程字幕整理

---

## 一、小节标题

### 子主题 1
- 关键点 1
- 关键点 2

## 二、下个小节

---

*本概要由 [章节名] 字幕整理而成*
```

### 命名规范

```
课程大纲汇总/{课程名} {章节号} {章节标题}-课程概要.md
```

---

## 第四步：输出文件到桌面

清理完成后，自动将字幕和概要文档导出到桌面。

### SRT 字幕输出

| 项目 | 说明 |
|------|------|
| **源文件** | 清理后的 `.md` 字幕文件（SRT 格式写入 Markdown 中） |
| **输出路径** | `~/Desktop/{原文件名}.srt` |
| **命名规则** | 保留原文件名，扩展名替换为 `.srt` |

示例：`智谱1.3.md` → `~/Desktop/智谱1.3.srt`

标准 SRT 格式：
```srt
1
00:00:00,900 --> 00:00:02,566
好的各位同学大家好

2
00:00:02,566 --> 00:00:04,733
我们继续接着上节课的内容
```

### 课程概要输出

| 项目 | 说明 |
|------|------|
| **源文件** | `课程大纲汇总/{课程名} {章节号} {章节标题}-课程概要.md` |
| **输出路径** | `~/Desktop/{课程名} {章节号} {章节标题}-课程概要.md` |
| **命名规则** | 与 vault 内概要文档同名 |

示例：`~/Desktop/智谱AI 1.3 AI编程工具与Vibe Coding-课程概要.md`

### 使用场景
- SRT 文件：导入视频播放器（PotPlayer、VLC）作为外挂字幕
- 概要文件：直接分享给同学，或导入其他笔记工具
- 桌面文件方便快速访问和分享

---

## 第五步：最终检查清单

- [ ] 字幕文件格式正确（SRT：编号 + 时间轴 + 文本）
- [ ] 无不合理的语气词残留
- [ ] 无 ASR 识别错误
- [ ] 无 ≤2 字的过短条目
- [ ] 时间轴编号连续
- [ ] 概要文档（若有）结构清晰、信息准确
- [ ] 原始文件已备份（`.bak`）
- [ ] SRT 文件已导出到桌面（`~/Desktop/{文件名}.srt`）
- [ ] 概要文档已导出到桌面（`~/Desktop/{课程名}...课程概要.md`）

---

## 在不同平台中使用

### Claude（Skill 自动加载）

`SKILL.md` 放入 `~/.claude/skills/subtitle-processing/`，提及字幕处理时自动触发。

### Cursor / Windsurf / 其他 AI IDE

AI 可读取本 SKILL.md 了解工作流，调用 `subtitle-process` 命令执行脚本。

### GitHub Copilot / ChatGPT / 通用 AI

直接提供本 SKILL.md 的内容给 AI，AI 即可理解标准工作流。脚本命令可直接执行。

### 仅脚本使用（无需 AI）

```bash
pip install subtitle-processor
subtitle-process 字幕.md -v                # 清理语气词 + ASR修正 + 过短处理
subtitle-process 字幕.md --only-clean -v   # 仅清理
```
完全独立使用，不依赖任何 AI 工具。

---

## FAQ

**Q: 为什么有些"这个"没有被删除？**
A: "这个"可能做指示词使用（如"这个问题"）。脚本只删除明显为填充词的情况，最终还需人工判断。

**Q: 不同课程有自己特有的 ASR 错误？**
A: 创建课程专用的 `fixes.json`：
```json
{
  "错误词1": "正确词1",
  "错误词2": "正确词2"
}
```
用 `--asr-fixes fixes.json` 传入脚本。

**Q: 同一课程多章节如何统一 ASR 规则？**
A: 创建一个共享 `fixes.json`，每章节处理时都用 `--asr-fixes fixes.json`。
