![](https://limbo.oss-cn-beijing.aliyuncs.com/wiki/20260616131429270.png)
图片来源：《图解SKILL》


**Skill 到底解决什么问题？**

一句话定调：

> **Skill 的本质，是把"领域经验"打包成可被 Agent 渐进式调用的文件**——它解决的是"通用大模型 + 专用经验"之间的张力。

大模型本身很强，但它不知道你公司的表结构、你的代码规范、你团队踩过的坑。Skill 的职责不是教模型"怎么写代码"，而是把**它不知道的领域知识、约定和流程**，以可被按需加载的方式喂给它。

一个 Claude Skill 本质上是一个文件夹，最少只需要一个 `SKILL.md` 文件，完整结构如下：

![](https://limbo.oss-cn-beijing.aliyuncs.com/wiki/20260616113843706.png)

理解了这层"为什么"，后面所有的机制和设计原则才有归属。

---

## 一、运行机制：渐进式披露（Progressive Disclosure）

理解 Skill 的第一件事，是搞清楚它**什么时候被加载**。

Claude 采用 **Progressive Disclosure（渐进式披露）** 策略——这是整个 Skill 体系的**核心设计哲学**，不是普通优化手段。它的目标：在动辄上百个 Skill 并存的场景里，把上下文窗口的开销压到最低。

| 内容 | 加载时机 | 说明 |
| --- | --- | --- |
| `name + description` | 始终加载 | 启动时预加载到系统提示，用于 Skill 发现阶段 |
| `SKILL.md 正文` | 触发时加载 | 命中触发条件后才读取 |
| `references/ 文件` | 按需加载 | SKILL.md 中明确引用时才读取 |
| `scripts/ 文件` | 按需执行 | 明确请求执行时才运行，**只有输出进上下文** |

关键推论：

- 大文件在被读取前**零上下文成本**——所以可以把完整 API 文档、大型数据集放心塞进 `references/`。
- 这套机制正是后面"设计模式"成立的基础：你之所以敢把内容拆到子文件，正是因为它不会提前烧 token。

---

## 二、frontmatter 规范：两张"索引卡"的硬约束

`SKILL.md` 必须以 YAML frontmatter 开头，只有两个字段是必填的，但它们都有**硬性约束**：

| 字段 | 约束 | 作用 |
| --- | --- | --- |
| `name` | ≤64 字符；仅小写字母/数字/连字符；**禁用保留字** `anthropic`、`claude`；不含 XML 标签 | Skill 的唯一标识 |
| `description` | ≤1024 字符；非空；不含 XML 标签；**始终用第三人称** | 唯一的"触发判据" |

记住一句话：**100+ 个 Skill 里，`description` 是 Claude 决定是否调用你的唯一依据。** 它比正文重要得多。

### 文件大小建议

| 文件类型 | 建议上限 |
| --- | --- |
| `SKILL.md` | 500 行 |
| `references/*.md` | 200 行 / 每个 |
| `scripts/*` | 300 行 / 每个 |
| `templates/*.template` | 100 行 / 每个 |

> Skill 正文控制在 4000 字以下、500 行以内，把最核心的操作流程和规范写进去即可，其他可以拆分到关联文件中。

![](https://limbo.oss-cn-beijing.aliyuncs.com/wiki/20260616113938292.png)

---

## 三、如何写好 description

**description = 功能定义 + 触发场景 / 触发词**

三大要素：**简洁、高效、准确**，篇幅控制在 100～200 字。两条铁律：

1. **始终用第三人称**（描述被注入系统提示，"我可以帮你"会造成视角混乱）；
2. **具体并包含关键术语**（触发词要写全，否则选不中）。

看一个案例：<https://github.com/mattpocock/skills/blob/main/skills/engineering/prototype/SKILL.md>

| 字段 | 内容 |
| --- | --- |
| name | prototype |
| description | Build a throwaway prototype to flesh out a design before committing to it. Routes between two branches — a runnable terminal app for state/business-logic questions, or several radically different UI variations toggleable from one route. Use when the user wants to prototype, sanity-check a data model or state machine, mock up a UI, explore design options, or says "prototype this", "let me play with it", "try a few designs". |

中文描述也就是：

> 构建一个一次性原型，在确定设计方案之前先完善它。可以在两个分支之间切换——一个可运行的终端应用用于处理状态/业务逻辑问题，或者从一个路由切换出几种截然不同的 UI 变体。当用户想要制作原型、检查数据模型或状态机的合理性、模拟 UI、探索设计方案，或说出"把这个做成原型"、"让我试试"、"尝试几种设计"时使用。

**反例对照**（官方明确反对的模糊写法）：

```yaml
# ✗ 太模糊，选不中
description: 帮助处理文档

# ✓ 具体，带触发词
description: 从 PDF 文件中提取文本和表格、填充表单、合并文档。在处理 PDF 文件或用户提及 PDF、表单或文档提取时使用。
```

![](https://limbo.oss-cn-beijing.aliyuncs.com/wiki/20260616132505198.png)

---

## 四、一个最小可用样例

讲了这么多规范，直接看一个**完整可运行**的 Skill 长什么样。以 PDF 处理为例，目录结构：

```
pdf/
├── SKILL.md              # 主要说明（触发时加载）
├── FORMS.md              # 表单填充指南（按需加载）
├── reference.md          # API 参考（按需加载）
├── examples.md           # 使用示例（按需加载）
└── scripts/
    ├── analyze_form.py   # 实用脚本（执行，不加载）
    ├── fill_form.py      # 表单填充脚本
    └── validate.py       # 验证脚本
```

对应的 `SKILL.md`：

```markdown
---
name: pdf-processing
description: 从 PDF 文件中提取文本和表格、填充表单和合并文档。在处理 PDF 文件或用户提及 PDF、表单或文档提取时使用。
---

# PDF 处理

## 快速开始

使用 pdfplumber 提取文本：
​```python
import pdfplumber
with pdfplumber.open("file.pdf") as pdf:
    text = pdf.pages[0].extract_text()
​```

## 高级功能

**表单填充**：完整指南请参阅 [FORMS.md](FORMS.md)
**API 参考**：所有方法请参阅 [REFERENCE.md](REFERENCE.md)
**示例**：常见模式请参阅 [EXAMPLES.md](EXAMPLES.md)
```

注意三个细节：

1. **frontmatter 的 description 同时承担"功能 + 触发词"**；
2. **正文只放最高频的核心用法**，其余全部外链；
3. **scripts/ 是"执行"而非"阅读"**——只有脚本输出进上下文，代码本身不占 token。

这 30 行，就是"渐进式披露 + 单一职责"在最小尺度上的完整体现。

---

## 五、工具与技能的关系

工具提供的能力通常是比较稳定的（比如读文件、跑 bash）。

而"技能"则是提供一些**经验**，教大模型具体怎么去做。大模型通过调用工具来执行任务，只有将工具能力与经验这两部分结合起来，才能构建出一个高质量的 Skill。

因此有两条实操要求：

1. **技能需要调用特定工具时，务必在描述里写清完整工具名**（包括 MCP 工具的完全限定名 `ServerName:tool_name`），这样智能体才能精准识别并调用。
2. **不要假设依赖已安装**——在说明里明确写出 `pip install xxx`，而不是"用 pdf 库处理"。

---

## 六、两条上位原则：写正文前先记住

官方《技能编写最佳实践》反复强调两条原则，比任何检查清单都更上位，建议单独内化。

### 原则一：默认假设 Claude 已经很聪明

**只写它不知道的**（领域经验、踩坑、约定），不要解释什么是 PDF、库怎么用。每写一段，问自己三个问题：

- "Claude 真的需要这个解释吗？"
- "我可以假设 Claude 知道这个吗？"
- "这段话值得它的 token 成本吗？"

对比一下（官方原例）：

```markdown
# ✓ 简洁（约 50 token）
## 提取 PDF 文本
使用 pdfplumber 进行文本提取：
​```python
import pdfplumber
with pdfplumber.open("file.pdf") as pdf:
    text = pdf.pages[0].extract_text()
​```

# ✗ 冗长（约 150 token）
## 提取 PDF 文本
PDF（便携式文档格式）文件是一种常见的文件格式，包含
文本、图像和其他内容。要从 PDF 中提取文本，您需要
使用一个库……（省略大段科普）
```

简洁版默认模型知道"PDF 是什么"和"库怎么装"。

### 原则二：自由度匹配任务脆弱性

**把具体程度，匹配到任务的脆弱性和可变性上。**

| 自由度 | 适用场景 | 写法 | 类比 |
| --- | --- | --- | --- |
| **高**（文本说明） | 多种方法都有效、决策看上下文 | 给方向、给清单 | 开阔地，多条路都通 |
| **中**（伪代码 / 带参脚本） | 有首选模式、允许变化 | 给模板 + 参数 | 有主路但允许绕行 |
| **低**（精确命令） | 操作脆弱、一致性至关重要 | 给死命令、禁加标志 | 两侧悬崖的窄桥 |

典型对照：

```markdown
# 高自由度：代码审查（开阔地）
1. 分析代码结构和组织
2. 检查潜在 bug 或边界情况
3. 建议可读性/可维护性改进

# 低自由度：数据库迁移（窄桥）
运行完全相同的命令，不要修改或加标志：
​```bash
python scripts/migrate.py --verify --backup
​```
```

这两条原则，是后面所有"设计模式"和"检查清单"的第一性依据。

---

## 七、SKILL 的设计模式

标题既然叫"设计模式"，就该把真正的模式摆出来。综合官方文档和顶级 Skill 实践，可归纳为以下几种。每种模式回答的都是同一个问题：**"怎么组织 SKILL.md 和它的关联文件？"**

### 模式 1：高级指南 + 引用文件（High-level Guide + References）

**SKILL.md 当目录，正文只放高频核心，详情拆到子文件。**

这是最基础也最常用的模式。适用于：技能内容较多，但核心用法集中。前文的 PDF 样例就是这种。

```markdown
# PDF 处理
## 快速开始
（最高频用法，直接写）
## 高级功能
**表单填充**：参阅 [FORMS.md](FORMS.md)
**API 参考**：参阅 [REFERENCE.md](REFERENCE.md)
```

**关键约束**：引用保持**一级深**，不要 `SKILL.md → advanced.md → details.md` 嵌套——否则 Claude 会用 `head -100` 预览，读到残缺信息。

### 模式 2：领域分仓（Domain Partitioning）

**按业务域拆分 reference，按需只加载一个域。**

适用于：一个技能覆盖多个互不相关的领域。典型如 BigQuery 分析——问销售指标时，不该把财务、营销的 schema 全塞进上下文。

```
bigquery-skill/
├── SKILL.md（概述和导航）
└── reference/
    ├── finance.md   # 收入、账单
    ├── sales.md     # 机会、管道
    ├── product.md   # API 使用
    └── marketing.md # 活动、归因
```

SKILL.md 里给出"域 → 文件"的导航表，并在正文示范 `grep` 快速检索，让 Claude 学会按域定位。

### 模式 3：条件详情（Conditional Detail）

**基础内容内联，高级特性外链。**

适用于：80% 用户只需要基础功能，20% 才会碰高级特性。

```markdown
# DOCX 处理
## 创建文档
（直接写，常用）
## 编辑文档
对于简单编辑，直接修改 XML。
**需要跟踪修订**：参阅 [REDLINING.md](REDLINING.md)
**需要 OOXML 细节**：参阅 [OOXML.md](OOXML.md)
```

和模式 1 的区别：模式 1 是"全部外链"，模式 3 是"基础内联 + 高级外链"。

### 模式 4：工作流 + 清单（Workflow + Checklist）

**把复杂任务拆成顺序步骤，配一个可勾选的清单。**

适用于：多步骤、易跳步、需要过程可视化的任务。

```markdown
## PDF 表单填充工作流
复制此清单并跟踪进度：
- [ ] 步骤 1：分析表单（运行 analyze_form.py）
- [ ] 步骤 2：创建字段映射（编辑 fields.json）
- [ ] 步骤 3：验证映射（运行 validate_fields.py）
- [ ] 步骤 4：填充表单（运行 fill_form.py）
- [ ] 步骤 5：验证输出（运行 verify_output.py）
```

清单的价值：**防止 Claude 跳过关键验证步骤**，同时让人和模型都能追踪进度。

### 模式 5：计划-验证-执行（Plan-Validate-Execute）

**对高风险/破坏性操作，先生成结构化中间产物，用脚本验证后再执行。**

适用于：批量操作、破坏性更改、复杂校验规则。流程是：

```
分析 → 生成 changes.json（计划）→ 脚本校验计划 → 执行 → 验证
```

**为什么有效**：

- 错误在"应用前"就被脚本客观拦截；
- 计划可逆——Claude 可以反复改 `changes.json` 而不碰原始文件；
- 错误信息指向具体字段，便于修复。

这是官方在"可执行代码 Skill"里最推崇的高阶模式，本质是把"信任 LLM 的输出"变成"信任脚本的校验"。

### 模式选型一览

| 模式 | 核心问题 | 何时用 |
| --- | --- | --- |
| 高级指南+引用 | 内容多，核心集中 | 通用首选 |
| 领域分仓 | 多业务域，互不相关 | BI / 数据分析类 |
| 条件详情 | 二八定律，高级少用 | 编辑器、格式转换类 |
| 工作流+清单 | 多步骤、易跳步 | 表单填充、部署类 |
| 计划-验证-执行 | 高风险、破坏性 | 批量改、迁移类 |

---

## 八、SKILL 工程化流程

设计模式讲完，回到落地。Skill 的工程化流程分三步：**需求澄清 → 设计评审 → 实现与迭代**。

### 第一步：澄清需求

先填写**技能需求卡**：

| 序号 | 类别 | 内容 |
| --- | --- | --- |
| ① | 问题 | 解决什么？ |
| ② | 场景 | 谁在什么时候用？ |
| ③ | 输入 | 需要什么？ |
| ④ | 输出 | 产出什么？ |
| ⑤ | 规则 | 有什么约束？ |
| ⑥ | 禁止清单 | 绝对不能做什么？ |

### 第二步：设计评审

写 `SKILL.md` 时，对照下面这张**设计参考清单**过一遍：

> 1. **单一职责**：这个技能只做一件事吗？
> 2. **按需加载**：`SKILL.md` 的 `name`、`description`、正文是否符合最佳实践？详细内容是否拆到了 `references/`？引用是否保持一级深？
> 3. **可预测**：有没有明确的输出格式和示例？
> 4. **可容错**：输入为空或异常时会怎样？关键步骤有没有人工确认 / 脚本验证？
> 5. **可扩展**：稳定的流程和变化的细节是否分开了？
> 6. **跨对话记忆**：有没有单独维护一个记录文件？
> 7. **踩坑点**：有没有预留踩坑点部分？
> 8. **禁止清单**：有没有写清"不要做什么"？

### 第三步：实现与迭代

核心原则：**人负责决策，LLM 负责执行**。

| 阶段 | 你负责 | 智能体负责 |
| --- | --- | --- |
| 定义需求 | 定义做什么、为什么做 | （理解意图） |
| 沉淀经验 | 提供领域经验和踩坑教训 | （内化经验） |
| 创建内容 | 通过提示词下达构建指令（提需求） | 编写 `SKILL.md` 和配置关联文件 |
| 验证质量 | 检查输出是否符合预期 | （无） |
| 调试修复 | 发现并描述问题 | 定位问题并完成修复 |

Skill 先跑通 MVP，然后逐步补齐功能、持续验证和优化。

---

## 九、评测驱动：让 Skill 持续变好

持续验证的核心是**评测驱动开发**——先建评测，再写说明，用数据迭代。

### 评测驱动的开发流程

| 步骤 | 说明 |
| --- | --- |
| 1. 识别差距 | 无 Skill 跑代表性任务，记录具体失败 |
| 2. 建评测集 | 针对这些差距，建 ≥3 个测试场景 |
| 3. 建基线 | 无 Skill 时测量性能 |
| 4. 写最小说明 | 只写足够通过评测的内容 |
| 5. 迭代 | 跑评测、比基线、改进 |

**顺序很关键**：先评测再写文档，确保解决的是真实问题，而不是想象出来的需求。

### 一个评测用例长什么样

评测采用结构化 JSON，每个用例包含技能、查询、文件、期望行为：

```json
{
  "skills": ["pdf-processing"],
  "query": "从此 PDF 文件中提取所有文本并将其保存到 output.txt",
  "files": ["test-files/document.pdf"],
  "expected_behavior": [
    "使用适当的 PDF 处理库或命令行工具成功读取 PDF 文件",
    "从文档中的所有页面提取文本内容，不遗漏任何页面",
    "以清晰、可读的格式将提取的文本保存到名为 output.txt 的文件"
  ]
}
```

### A / B 协作迭代法

官方推荐的高效迭代姿势：**用两个 Claude 实例分工**。

- **Claude A（专家）**：帮你设计和改进 SKILL.md；
- **Claude B（执行者）**：加载技能跑真实任务，暴露问题；
- 你把 B 的观察带回 A，A 改进后回 B 测试，循环往复。

观察 B 的关键信号：它是否按预期顺序读文件？是否漏掉了重要引用？是否反复读同一文件（说明该内容该上提到正文）？是否从不访问某个捆绑文件（说明它多余或信号不足）？

---

## 十、反模式速查：不要这么做

| 反模式 | 为什么错 | 正确做法 |
| --- | --- | --- |
| description 写"帮助处理文档" | 太模糊，100+ 技能里选不中 | 写清功能 + 触发词 |
| 解释"Claude 已知"的常识 | 浪费 token | 只写领域经验 |
| 高风险操作给高自由度 | 容易跑飞 | 给精确命令 + 验证 |
| 引用嵌套 `A→B→C` | Claude 读到残缺 | 保持一级引用 |
| Windows 路径 `scripts\helper.py` | Unix 上报错 | 一律用正斜杠 |
| 假设依赖已安装 | 运行时报错 | 明确 `pip install xxx` |
| 给一堆可选库"你可以用 A 或 B 或 C" | 选择困难 | 给默认 + 逃生舱 |
| 时间敏感信息写进正文 | 会过期变错 | 单独"旧模式"折叠区 |

---

## 十一、一句话回顾

> Skill = **把领域经验打包成可渐进式调用的文件**。
> 写好它的关键 = **精准的 description（触发） + 渐进式披露的结构（加载） + 匹配脆弱性的自由度（执行） + 评测驱动的迭代（改进）**。

记住四个动词：**触发、加载、执行、改进**——分别对应 description、references、自由度、评测集。掌握这四个，就算"读懂"了 SKILL 的设计模式。

---

## 延伸阅读

- 《图解SKILL》
- [Equipping agents for the real world with Agent Skills — Anthropic 工程博客](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
- [技能编写最佳实践 — Claude 官方文档（中文）](https://platform.claude.com/docs/zh-CN/agents-and-tools/agent-skills/best-practices)
- [anthropics/skills — GitHub 官方仓库](https://github.com/anthropics/skills)
- [Agent Skills Specification — agentskills.io 开放标准](https://agentskills.io/specification)
- [工作流的 Skill 怎么写？从 7 个顶级 Skill 中提炼的模式](https://developer.aliyun.com/article/1732677)

