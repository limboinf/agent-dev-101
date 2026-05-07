# 📋 AI Agent 两个月系统化学习计划（每日知识点细分）

> **说明**: 八周进阶计划，将每天的学习内容细化为具体知识点。  
> 每个知识点之间具有内在关联，前一个知识点是后一个知识点的铺垫。  
> **每日投入**: 2-3 小时 · **总天数**: 56 天

---

## 第一周：夯实基础 — LLM 核心概念

> **本周目标**: 理解 LLM 基础原理，掌握 API 调用，理解 Context Engineering  
> **本周交付物**: 一个多轮对话 CLI 程序 + 一份 Context Engineering 实践笔记

---

### Day 1 · LLM 基础回顾（上）

**主线**: 理解 LLM 是怎么"说话"的 — 从文本到 Token

|  #  | 知识点                  | 要点                                                                                                | 与下一知识点的关联                          |
| :-: | -------------------- | ------------------------------------------------------------------------------------------------- | ---------------------------------- |
|  1  | Token 与 Tokenization | 什么是 Token？Tokenizer 如何将文本拆分为子词（subword）；不同模型的 Token 差异（BPE vs SentencePiece）；Token 数量与成本/上下文窗口的关系 | 理解 Token 是理解"模型如何阅读输入"的前提 →        |
|  2  | Embedding 基本概念       | Token → 向量（Embedding）的映射；为什么语义相近的词在向量空间中距离近；预告：后续 RAG 会深入 Embedding 模型                            | 模型将 Token 转为 Embedding 后才能"理解"含义 → |
|  3  | Chat Templates 与角色系统 | System / User / Assistant 三种角色的含义；Chat Template 的格式（OpenAI vs Anthropic）；为什么 System Prompt 如此重要   | 角色系统决定了我们如何与模型"对话" →               |

**实践任务**: 使用 tiktoken 库对不同文本进行 Token 计数，对比中英文 Token 差异。

---

### Day 2 · LLM 基础回顾（下）

**主线**: 控制 LLM 的输出行为，掌握 API 调用

|  #  | 知识点                  | 要点                                                                                                | 与下一知识点的关联                                     |
| :-: | -------------------- | ------------------------------------------------------------------------------------------------- | --------------------------------------------- |
|  1  | LLM 模型参数避坑指南    | Temperature / Top-p 的 Agent 场景推荐值；max_tokens vs max_completion_tokens 的坑；Structured Output 与 tool_choice；推理模型的参数差异                                  | 掌握模型参数是 API 调用和 Agent 开发的基础 → |
|  2  | API 调用实战             | 使用 Python SDK 发起第一个请求；实现一次多轮对话（手动维护消息列表）                                                          | 掌握 API 调用是后续所有实践的基础                           |
|  3  | 多轮对话与消息管理           | 手动维护消息列表的技巧；Token 计数与截断策略；对话历史的管理方式                                                              | 消息管理是 Context Engineering 的基础 →                |

**实践任务**: 用 OpenAI 或 Anthropic API 完成一次多轮对话，手动维护消息列表，体验不同 Temperature 对输出的影响。

---

### Day 3 · Context Engineering（上）

**主线**: 从"写好一句话"到"设计信息系统" — Prompt Engineering 是子集，Context Engineering 才是全局

> Andrej Karpathy 的比喻：LLM 是 CPU，上下文窗口是 RAM，而你是负责加载正确信息的操作系统。
> 瓶颈不再是你问了什么，而是问题周围环绕着什么信息。

|  #  | 知识点                               | 要点                                                                                                                                                                                        | 与下一知识点的关联                                       |
| :-: | --------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------- |
|  1  | Prompt Engineering 回顾             | Zero-shot / Few-shot / CoT 等经典技巧；System Prompt 设计（角色设定、约束、输出格式）；Prompt Engineering 在单轮、静态任务中仍然有效                                                                                          | Prompt Engineering 解决了"怎么问" → 但复杂系统需要解决"模型看到什么" |
|  2  | 什么是 Context Engineering？          | 定义：设计和管理 LLM 在每一步看到的全部输入信息的架构；与 Prompt Engineering 的核心区别 — 不仅是措辞，而是信息选择、排序和结构化；四大支柱：Context Composition（选什么）、Context Ranking（排什么序）、Context Optimization（怎么压缩）、Context Orchestration（何时加载） | 理解定义 → 为什么它比 Prompt Engineering 更重要？            |


**实践任务**: 精读 Context Engineering 相关文章，整理 Prompt Engineering vs Context Engineering 的对比笔记。

---

### Day 4 · Context Engineering（下）

**主线**: Context Engineering 的核心模式与实践

|  #  | 知识点                      | 要点                                                                                                                                                                                                                                   | 与下一知识点的关联                               |
| :-: | ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------- |
|  1  | Context Engineering 核心模式 | **渐进披露**（Progressive Disclosure）：按需加载指令和工具定义，而非一次性全部塞入；<br>**上下文压缩**（Compression）：滑动窗口 + 摘要混合策略，保留最近 N 轮完整、压缩旧轮；<br>**上下文路由**（Routing）：根据查询类型加载不同的知识库/工具集，避免无关信息占用窗口；<br>**工具管理**（Tool Management）：控制工具 Schema 的 Token 开销，按需激活而非全量注册 | 模式学会了 → 如何落地实践？                         |
|  2  | Context Engineering 实践   | 设计一个上下文模板：System Instructions + 动态工具定义 + 检索结果 + 对话历史 + 当前查询；用 Token 计数器衡量各部分占比；优化实验：对比"全量 Context"vs"精简 Context"对模型输出质量的影响                                                                                                           | Context Engineering 是贯穿整个 Agent 开发的核心能力 |
|  3  | Prompt Cache             | Prompt Cache 的原理与使用场景；不同厂商的缓存策略对比；如何设计 Prompt 结构以最大化缓存命中率                                                                                                                                                                            | Prompt Cache 是性能优化的关键手段 →               |

**实践任务**: 设计一个上下文模板（包含 System Prompt + 工具定义 + 检索结果 + 对话历史），用 Token 计数器分析各部分占比，实验对比"全量信息塞入"vs"精简后只保留高信号信息"对模型回答质量的影响。

---

### Day 5 · Agent 概念入门

**主线**: 从"对话系统"到"能自主行动的 Agent"— 理解 Agent 的本质

|  #  | 知识点               | 要点                                                                                                        | 与下一知识点的关联                   |
| :-: | ----------------- | --------------------------------------------------------------------------------------------------------- | --------------------------- |
|  1  | 什么是 AI Agent？     | Agent 的定义：能自主感知环境、做出决策并采取行动的系统；Agent ≠ Chatbot 的核心区别；Agent 的核心循环：Perceive → Reason → Act；每一步对应什么操作；循环何时终止 | 理解定义后 → 需要知道 Agent 内部是怎么运转的 |
|  2  | Workflow vs Agent | Anthropic 的核心观点：大部分场景用 Workflow 就够了；何时需要真正的 Agent；过度设计的代价                                                 | 理解"不是所有问题都需要 Agent" →       |

**实践任务**: 精读 Anthropic "Building Effective Agents"，画出 Agent 核心循环的流程图。

---

### Day 6 · Agent 设计模式

**主线**: 了解 Agent 的各种设计模式，建立全局视野

| # | 知识点 | 要点 | 与下一知识点的关联 |
|:-:|--------|------|--------------------|
| 1 | Agent 设计模式总览 | 六大模式预览：ReAct / Reflection / Tool Use / Planning / Multi-Agent / Human-in-the-Loop；各自适用场景 | 有了全局视野 → 深入最小实现 |
| 2 | 从零理解一个最简 Agent | 伪代码走通一个最小 Agent：while True → LLM 推理 → 判断是否需要行动 → 执行工具 → 返回结果 | 理解最简实现后 → 下周深入 Function Calling |

**实践任务**: 用伪代码描述一个最简 Agent，理解 Agent 的核心循环。

---

### Day 7 · 本周回顾与整理

**主线**: 巩固第一周所学，查漏补缺

| # | 任务 | 要点 |
|:-:|------|------|
| 1 | 知识点回顾 | 回顾 Token、Embedding、Chat Template、Context Engineering、Agent 概念 |
| 2 | 笔记整理 | 整理本周学习笔记，形成知识卡片 |
| 3 | 实践复盘 | 回顾本周实践代码，确保理解每一步 |

---
---

## 第二周：动手实现 — Function Calling + ReAct + 结构化输出

> **本周目标**: 掌握工具调用、ReAct 模式、结构化输出，从零实现一个完整 Agent  
> **本周交付物**: 一个从零实现的简单 ReAct Agent + 一个带工具调用的 CLI 助手

---

### Day 8 · Function Calling / Tool Use（上）

**主线**: 让模型"长出手脚" — 从只能说话到能调用外部工具

|  #  | 知识点               | 要点                                                                    | 与下一知识点的关联                              |
| :-: | ----------------- | --------------------------------------------------------------------- | -------------------------------------- |
|  1  | 为什么需要 Tool Use？   | LLM 的固有局限（无法实时获取数据、无法执行计算、无法操作外部系统）；Tool Use 如何弥补                     | 知道"为什么"→ 接下来学"怎么做"                     |
|  2  | 工具定义与 JSON Schema | 如何用 JSON Schema 描述一个工具（名称、描述、参数类型）；好的工具描述 vs 差的工具描述                   | 工具定义好后 → 模型如何选择调用哪个工具？                 |
|  3  | 模型如何选择工具          | 模型根据用户意图和工具描述"决策"调用哪个工具；tool_choice 参数（auto / required / none）；并行工具调用 | 模型决策后 → 开发者如何执行工具并返回结果？                |

**实践任务**: 定义 2-3 个工具的 JSON Schema，理解工具描述对模型选择的影响。

---

### Day 9 · Function Calling / Tool Use（下）

**主线**: 完整走通工具调用流程，掌握多工具编排

|  #  | 知识点               | 要点                                                                    | 与下一知识点的关联                              |
| :-: | ----------------- | --------------------------------------------------------------------- | -------------------------------------- |
|  1  | 工具调用的完整流程         | 用户请求 → 模型返回 tool_call → 开发者执行函数 → 将结果作为 tool message 返回 → 模型生成最终回答    | 掌握单工具后 → 多工具场景                         |
|  2  | 多工具编排             | 多个工具的注册与管理；工具命名和描述的最佳实践；错误处理（工具执行失败怎么办）                               | 工具调用是 Agent 的核心能力，接下来将把它融入 ReAct 循环 |

**实践任务**: 实现一个带天气查询 + 计算器工具的 Agent，体验完整的 Function Calling 流程。

---

### Day 10 · ReAct 模式深入（上）

**主线**: 把推理（Reasoning）和行动（Acting）结合起来 — Agent 的经典范式

|  #  | 知识点                               | 要点                                                                                                                                                                                                                            | 与下一知识点的关联        |
| :-: | --------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------- |
|  1  | ReAct 论文核心思想 + Thought-Action-Observation 循环 | Reasoning + Acting 的统一；与纯 CoT（只想不做，容易幻觉）、Act-only（只做不想，容易迷路）的对比；Thought（模型的推理过程）→ Action（选择工具+参数）→ Observation（工具执行结果）三阶段循环；ReAct 在 HotpotQA / FEVER / ALFWorld / WebShop 上的实验结果；循环终止条件（finish action / 信息已足够）；为什么 ReAct 是 Agent 的"OS 内核" | 理解理论与循环 → 如何用代码实现？ |

**实践任务**: 阅读 ReAct 论文核心部分（Yao et al., 2022），画出 Thought-Action-Observation 循环流程图，并对比 CoT-only / Act-only / ReAct 三种范式的轨迹差异。

---

### Day 11 · ReAct 模式深入（下）

**主线**: 从零手写 ReAct Agent，把 Prompt 模板、循环控制和踩坑改进一次走通

|  #  | 知识点                               | 要点                                                                              | 与下一知识点的关联                          |
| :-: | --------------------------------- | ------------------------------------------------------------------------------- | ---------------------------------- |
|  1  | 从零手写 ReAct Agent：Prompt 模板、循环控制、踩坑与改进方向 | 不依赖任何框架，用 Python + OpenAI API 走通 ReAct 全流程：System Prompt 定义 Thought/Action/Observation 格式、stop word 截断、循环驱动、工具分发、Observation 拼接；常见格式错乱、死循环、Token 爆炸的真实踩坑与修复；Planning / Reflection / 框架封装等改进方向 | 走完手写后 → 下一周用框架体会"被人包好的 ReAct" |

**实践任务**: 从零用 Python 实现一个 ReAct Agent（不用框架），包含至少 2 个工具，能解决"今天北京天气如何？如果气温超过 30°C 就推荐冷饮"这类需要多步推理的问题。

---

### Day 12 · 结构化输出全攻略

**主线**: 把模型的输出从"自由文本"驯服成"可程序化处理的结构化数据" — 一天打通从原理到 Agent 实战

|  #  | 知识点                             | 要点                                                                     | 与下一知识点的关联                          |
| :-: | ------------------------------- | ---------------------------------------------------------------------- | ---------------------------------- |
|  1  | 为什么需要结构化输出 + 三种实现层级 | Agent 需要程序化处理模型输出；自由文本难以解析；下游系统集成需要固定格式；三种"驯服"层级：Prompt 引导 → JSON Mode → Structured Output（JSON Schema） | 理解层级 → 逐个上手 |
|  2  | JSON Mode 与 Structured Output | OpenAI 的 `response_format: json_object` 只保证"是合法 JSON"；Structured Outputs（JSON Schema + `strict: true`）严格约束字段、类型、枚举；与 Anthropic / 其他厂商的实现差异 | Schema 定义结构 → 还需要在代码侧验证 |
|  3  | Pydantic 验证 + Agent 中的结构化输出   | 用 Pydantic 定义数据模型，自动校验 + 类型转换；工具参数 / Agent 最终输出都用 Pydantic 兜底；模型输出不合格时的自动重试策略 | 实战 → 整理稳定输出 JSON 的工程套路 |
|  4  | 面试题：怎么稳定输出 JSON                  | 综合方案对比：Prompt 技巧 vs JSON Mode vs Structured Output vs 框架封装（Instructor / outlines）；什么时候用哪个；常见踩坑（被截断、嵌入解释文本、字段漂移） | 工程化必备                                 |

**实践任务**: 让 Agent 输出结构化的旅行计划 JSON（包含目的地、日程、预算等字段），分别用 JSON Mode 和 Structured Output 实现并对比，最后用 Pydantic 验证。

---

### Day 13 · 结构化输出实战与复盘

**主线**: 不引入新知识点，专门把 D12 的内容用一个稍大的实战项目跑透，并梳理踩坑笔记

| # | 任务 | 要点 |
|:-:|------|------|
| 1 | 多场景实战 | 选 2-3 个真实场景（旅行计划、信息抽取、报销单解析）分别用 Pydantic + Structured Output 实现 |
| 2 | 失败案例收集 | 故意构造让模型容易出错的输入（缺字段、歧义字段、长文本），记录失败模式与修复手段 |
| 3 | 重试与降级策略 | 实现自动重试（模型输出不通过 Pydantic 时再问一次）+ Schema 降级（strict 失败时回退到 json_object） |
| 4 | 笔记整理 | 梳理一份"稳定输出 JSON 的 Checklist"，作为后续 Agent 项目的复用资产 |

---

### Day 14 · 🔨 第二周项目：命令行 AI 助手

**主线**: 整合本周所学，构建一个完整的 CLI Agent

| # | 知识点/任务 | 要点 | 关联 |
|:-:|-------------|------|----|
| 1 | 项目设计与架构 | 确定 CLI 助手的功能范围；定义 Agent 的角色（System Prompt）；列出工具清单 | → |
| 2 | 工具实现 | 实现 3 个工具：搜索（Web Search API）、计算器（Python eval）、天气查询（天气 API） | → |
| 3 | ReAct 循环集成 | 将 ReAct 实现应用到 CLI 助手中；处理多轮对话 | → |
| 4 | 结构化输出整合 | 工具参数使用 JSON Schema 定义；最终输出使用 Pydantic 验证 | → |
| 5 | 用户交互与异常处理 | CLI 交互界面（input/print）；优雅的错误处理；对话历史管理 | → |
| 6 | 代码整理与文档 | 项目结构化（模块拆分）；README 编写；记录设计决策 | 第二周完成 ✅ |

**交付物**: 一个从零实现的 CLI Agent，支持多工具调用、ReAct 推理循环、结构化输出。

---
---

## 第三周：框架入门 — LangChain 基础 + RAG

> **本周目标**: 掌握 LangChain 核心概念，理解 RAG 原理  
> **本周交付物**: 一个 LangChain Agent + 一个 RAG 文档问答系统

---

### Day 15 · LangChain 入门

**主线**: 从"手写一切"到"框架加速" — LangChain 的核心抽象

| # | 知识点 | 要点 | 与下一知识点的关联 |
|:-:|--------|------|--------------------|
| 1 | LangChain 是什么？ | LangChain 解决的问题；核心定位：LLM 应用开发框架；与直接调用 API 的区别 | 了解定位 → 学习核心概念 |
| 2 | LLM 集成与 ChatModel | ChatOpenAI / ChatAnthropic 的使用；统一接口的意义；模型切换的便利性 | 有了模型 → 需要组织 Prompt |
| 3 | Prompt Templates | PromptTemplate / ChatPromptTemplate 的用法；变量注入；模板复用 | Prompt 生成输出 → 需要解析输出 |

**实践任务**: 安装 LangChain，用 ChatModel 和 PromptTemplate 完成一个简单的问答链。

---

### Day 16 · LangChain LCEL 与 Chain

**主线**: 掌握 LangChain Expression Language，构建可组合的 Chain

| # | 知识点 | 要点 | 与下一知识点的关联 |
|:-:|--------|------|--------------------|
| 1 | Output Parsers | StrOutputParser / JsonOutputParser / PydanticOutputParser；链式处理 | 模型 + Prompt + Parser 组合 → 形成 Chain |
| 2 | Chain（LCEL） | LangChain Expression Language（LCEL）的管道语法（`|`）；Runnable 接口；Chain 的组合与嵌套 | Chain 是 LangChain 的基本构建块 |
| 3 | Runnable 核心类型 | RunnableSequence / RunnableParallel / RunnableLambda / RunnablePassthrough；各自的使用场景 | 掌握 Runnable 组合 → 下一步添加 Tool |

**实践任务**: 用 LCEL 构建一个包含并行处理的 Chain（如同时生成摘要和关键词提取）。

---

### Day 17 · LangChain Tools 与 Agent

**主线**: 用 LangChain 构建工具丰富的 Agent

| # | 知识点 | 要点 | 与下一知识点的关联 |
|:-:|--------|------|--------------------|
| 1 | @tool 装饰器 | 用 @tool 装饰器快速定义工具；自动生成 JSON Schema；类型注解的重要性 | 定义好工具 → 如何让 Agent 使用？ |
| 2 | Tool Calling Agent | create_tool_calling_agent 的用法；与手写 Function Calling 的对比 | Agent 创建好 → 如何运行？ |
| 3 | AgentExecutor | AgentExecutor 的运行机制；max_iterations 控制；verbose 模式调试 | 运行 Agent → 如何管理工具？ |

**实践任务**: 用 LangChain 改写第二周的天气 Agent，体验框架带来的代码简化。

---

### Day 18 · Agent Memory（记忆系统）

**主线**: 让 Agent 拥有"记忆" — 从"金鱼记忆"到"长期记忆"

| # | 知识点 | 要点 | 与下一知识点的关联 |
|:-:|--------|------|--------------------|
| 1 | 为什么 Agent 需要记忆？ | LLM 本身是无状态的；每次请求独立；多轮对话需要手动维护上下文 | 了解问题 → 学习短期记忆 |
| 2 | 短期记忆：对话历史 | ConversationBufferMemory；消息列表的维护；Token 限制下的窗口策略（ConversationBufferWindowMemory） | 短期记忆会溢出 → 需要压缩 |
| 3 | 摘要记忆与长期记忆 | ConversationSummaryMemory；用 LLM 自动总结历史对话；将重要信息 Embedding 后存入向量数据库；Semantic Memory 的概念 | 向量记忆引出了"检索"的概念 → RAG |

**实践任务**: 实现一个能记住上下文的对话 Agent，支持对话历史 + 摘要记忆。

---

### Day 19 · RAG 基础（上）

**主线**: 让 Agent 能"阅读文档" — 检索增强生成的前半流程

| # | 知识点 | 要点 | 与下一知识点的关联 |
|:-:|--------|------|--------------------|
| 1 | RAG 是什么？为什么需要？ | Retrieval-Augmented Generation 的定义；解决 LLM 知识过时/幻觉/领域知识不足的问题 | 理解动机 → 学习 RAG Pipeline |
| 2 | 文档加载与预处理 | Document Loaders（PDF、Markdown、网页）；文本清洗；元数据提取 | 文档加载好 → 如何切成合适大小？ |
| 3 | 文档分块策略（Chunking） | 固定大小分块 vs 语义分块；chunk_size 和 chunk_overlap 的选择；分块对检索质量的影响 | 分块后 → 如何让计算机"理解"每个块？ |

**实践任务**: 使用 Document Loaders 加载一个 PDF 文档，尝试不同的分块策略并对比效果。

---

### Day 20 · RAG 基础（下）

**主线**: 完成 RAG 的后半流程 — Embedding、存储与检索生成

| # | 知识点 | 要点 | 与下一知识点的关联 |
|:-:|--------|------|--------------------|
| 1 | Embedding 与向量数据库 | Embedding 模型（OpenAI / sentence-transformers）；向量数据库（Chroma / FAISS）；存储与索引 | 向量存储好 → 如何检索？ |
| 2 | 检索与生成 | 语义搜索（相似度检索）；检索结果注入 Prompt；RAG Chain 的完整实现 | 完整 RAG 系统搭建完毕 |

**实践任务**: 构建一个能回答 PDF 文档问题的 RAG 系统，体验完整的 Load → Split → Embed → Store → Retrieve → Generate 流程。

---

### Day 21 · 本周回顾与实践

**主线**: 巩固 LangChain 与 RAG 知识，完善实践项目

| # | 任务 | 要点 |
|:-:|------|------|
| 1 | LangChain 知识梳理 | 回顾 LCEL、Agent、Memory 核心概念 |
| 2 | RAG 系统优化 | 优化分块策略、检索质量；尝试不同的 Embedding 模型 |
| 3 | 实践代码整理 | 整理本周代码，形成可复用的模板 |

---
---

## 第四周：框架进阶 — LangChain 进阶 + LangGraph

> **本周目标**: 掌握 LangChain 进阶能力（中间件、高级 LCEL 模式），入门 LangGraph  
> **本周交付物**: 一个 LangGraph Agentic RAG 系统

---

### Day 22 · LangChain 进阶：高级 LCEL 模式

**主线**: 深入 LCEL 的高级组合模式，掌握生产级链式编排

| # | 知识点 | 要点 | 与下一知识点的关联 |
|:-:|--------|------|--------------------|
| 1 | RunnableBranch 条件路由 | 根据输入动态路由到不同的 Chain；实现分类 → 分支处理的模式 | 路由能力 → 需要容错机制 |
| 2 | RunnableWithFallbacks 容错 | 主模型失败时自动切换到备选模型；with_fallbacks 的使用；降级策略设计 | 容错完成 → 需要重试和性能控制 |
| 3 | with_retry 与 with_config | 自动重试失败操作（指数退避）；绑定默认配置（tags、metadata、callbacks）；RunnableConfig 配置传播 | 掌握高级模式 → 进入中间件体系 |

**实践任务**: 构建一个带条件路由（根据问题类型分流到不同处理链）和 Fallback（主模型失败切备选模型）的 Chain。

---

### Day 23 · LangChain 进阶：Callbacks 与可观测性

**主线**: 理解 LangChain 的 Callbacks 体系，掌握调试和监控手段

| # | 知识点 | 要点 | 与下一知识点的关联 |
|:-:|--------|------|--------------------|
| 1 | Callbacks 体系 | BaseCallbackHandler 的继承与实现；on_llm_start / on_llm_end / on_tool_start 等钩子；自定义 Callback Handler | 回调能监控 → 需要更系统的追踪 |
| 2 | LangSmith Tracing | LangSmith 平台接入；Tracing 的配置与使用；Agent 执行链的可视化分析；UsageMetadataCallbackHandler 跟踪 Token 消耗 | Tracing 提供可观测性 → 缓存优化成本 |
| 3 | Caching 与 Rate Limiting | LLM 响应缓存策略（InMemoryCache / SQLiteCache）；InMemoryRateLimiter 控制请求频率；成本优化实践 | 缓存和限流是生产环境必备 |

**实践任务**: 为已有的 Agent 添加自定义 Callback Handler（记录每次工具调用的耗时和结果），接入 LangSmith Tracing。

---

### Day 24 · LangChain 进阶：Middleware 中间件系统

**主线**: 掌握 LangChain 1.0 的中间件系统 — Agent 控制的核心

| # | 知识点 | 要点 | 与下一知识点的关联 |
|:-:|--------|------|--------------------|
| 1 | Middleware 架构概述 | 中间件的设计理念；before_model / modify_model_request / after_model 三个核心钩子；与 Web 框架中间件的类比 | 理解架构 → 学习内置中间件 |
| 2 | 内置中间件 | HumanInTheLoopMiddleware（人工审批）；SummarizationMiddleware（自动摘要长对话）；ModelCallLimitMiddleware / ToolCallLimitMiddleware（调用限制）；AnthropicPromptCachingMiddleware（Prompt 缓存） | 内置中间件 → 自定义中间件 |
| 3 | 自定义 Middleware 实战 | 继承 AgentMiddleware 编写自定义逻辑；动态模型选择（简单问题用小模型、复杂问题用大模型）；输出验证与敏感信息过滤；中间件组合与执行顺序 | 中间件掌握 → 用 create_agent 整合 |

**实践任务**: 为 Agent 编写一个自定义中间件：根据问题复杂度动态切换模型 + 在 after_model 钩子中做输出安全检查。

---

### Day 25 · LangGraph 入门

**主线**: 从线性 Chain 到图状态机 — 构建可控的 Agent 工作流

| # | 知识点 | 要点 | 与下一知识点的关联 |
|:-:|--------|------|--------------------|
| 1 | 为什么需要 LangGraph？ | AgentExecutor 的局限（控制流不灵活、状态管理弱）；图状态机的优势 | 理解动机 → 学习核心概念 |
| 2 | 核心概念：State | TypedDict 定义状态；Reducer 函数（消息如何累加）；状态在节点间的传递 | 状态需要节点来处理 → |
| 3 | 核心概念：Node 与 Edge | Node = 函数（处理状态）；Edge = 连接（控制流程）；Conditional Edge（条件路由） | 节点和边组成图 → |

**实践任务**: 创建一个简单的 LangGraph 图，包含 2-3 个节点和条件路由。

---

### Day 26 · LangGraph 工具集成

**主线**: 在 LangGraph 中集成工具调用

| # | 知识点 | 要点 | 与下一知识点的关联 |
|:-:|--------|------|--------------------|
| 1 | 构建第一个 LangGraph Agent | StateGraph 的创建；添加节点和边；编译与运行；可视化图结构 | 基础 Agent 完成 → 增加工具节点 |
| 2 | LangGraph + Tool Calling | ToolNode 的使用；工具调用后的路由（继续推理 or 返回结果）；构建一个多步骤研究 Agent | 带工具的 LangGraph Agent |

**实践任务**: 用 LangGraph 构建一个多步骤研究 Agent，包含"搜索信息 → 分析内容 → 生成摘要"的工作流。

---

### Day 27 · LangGraph 进阶

**主线**: 让 Agent 可持久化、可中断、可人工干预

| # | 知识点 | 要点 | 与下一知识点的关联 |
|:-:|--------|------|--------------------|
| 1 | Persistence（检查点） | MemorySaver / SQLiteSaver；状态的持久化与恢复；thread_id 管理多会话 | 持久化让 Agent 可以"暂停" → 可以加入人工环节 |
| 2 | Human-in-the-Loop | interrupt_before / interrupt_after 机制；人工审核节点的设计；审批流程实现 | 人工节点需要等待 → 涉及流式 |
| 3 | Streaming 与子图 | stream / astream 的使用；实时输出 Agent 的思考过程；子图（Subgraph）的定义与嵌套；错误处理与重试 | 鲁棒性是 Agent 上生产的前提 |

**实践任务**: 为研究 Agent 添加人工审核节点和状态持久化。

---

### Day 28 · 🔨 第四周项目：文档问答 Agent

**主线**: 构建一个 Agentic RAG 系统 — Agent 驱动的智能文档问答

| # | 知识点/任务 | 要点 | 关联 |
|:-:|-------------|------|----|
| 1 | 项目架构设计 | Agentic RAG 的核心理念：Agent 自主决定"是否需要检索"以及"检索什么"；与 Naive RAG 的区别 | → |
| 2 | 文档索引构建 | 加载目标文档 → 分块 → Embedding → 存入 Chroma 向量数据库 | → |
| 3 | 检索工具实现 | 将文档检索封装为 LangGraph Tool；支持语义搜索 + 关键词过滤 | → |
| 4 | 网络搜索工具集成 | 集成 Tavily / SerpAPI 等搜索工具；Agent 能判断"文档中没有答案"时自动搜索网络 | → |
| 5 | LangGraph 工作流编排 | 用 LangGraph 编排完整流程：接收问题 → 判断信息来源 → 检索/搜索 → 评估信息充足性 → 生成回答 | → |
| 6 | 对话记忆与持久化 | 添加对话历史支持；使用 MemorySaver 持久化状态 | 第四周完成 ✅ |

**交付物**: 一个 LangGraph Agentic RAG 系统，能智能判断信息来源（文档 vs 网络），支持记忆和持久化。

---
---

## 第五周：多 Agent 系统 + MCP 协议

> **本周目标**: 掌握多 Agent 协作模式，理解 MCP 协议  
> **本周交付物**: 一个多 Agent 协作系统 + 一个 MCP Server

---

### Day 29 · 多 Agent 概念

**主线**: 从"单打独斗"到"团队协作" — 多 Agent 系统的设计哲学

| # | 知识点 | 要点 | 与下一知识点的关联 |
|:-:|--------|------|--------------------|
| 1 | 为什么需要多 Agent？ | 单 Agent 的局限（上下文窗口、专注度、复杂任务）；分工协作的优势；现实世界类比（公司组织架构） | 知道"为什么" → 学习"怎么组织" |
| 2 | Supervisor 模式 | 一个"主管" Agent 负责任务分配与汇总；Worker Agent 各司其职；适用场景 | Supervisor 是一种"中心化"模式 → |
| 3 | Swarm 模式与其他模式 | 去中心化的 Agent 群体；Agent 间直接通信（Handoff）；层级架构与混合模式；任务分解与委派策略 | 理解架构后 → 如何定义每个 Agent？ |

**实践任务**: 阅读 Microsoft Agent Course 多 Agent 章节，为一个"内容创作团队"设计 Agent 角色，画出协作流程图。

---

### Day 30 · Agent 角色设计

**主线**: 学习如何设计好的 Agent 角色

| # | 知识点 | 要点 | 与下一知识点的关联 |
|:-:|--------|------|--------------------|
| 1 | Agent 角色设计原则 | 职责单一原则；角色描述的最佳实践；工具分配策略；Agent 间的输入输出约定 | 设计好角色 → 用 LangGraph 实现 |
| 2 | 角色实战设计 | 为具体场景（内容创作/研究分析/客服系统）设计 Agent 角色；定义每个角色的 Prompt、工具和输出格式 | 角色设计完成 → 下一步实现 |

**实践任务**: 为"内容创作团队"设计完整的 Agent 角色定义文档。

---

### Day 31 · LangGraph Multi-Agent（上）

**主线**: 用 LangGraph 实现多 Agent 编排

| # | 知识点 | 要点 | 与下一知识点的关联 |
|:-:|--------|------|--------------------|
| 1 | LangGraph 多 Agent 架构 | 每个 Agent 是一个 Node；Supervisor 作为路由节点；状态在 Agent 间传递 | 理解架构 → 实现 Supervisor |
| 2 | Supervisor 节点实现 | 用 LLM 决定下一步交给哪个 Agent；路由逻辑设计；终止条件 | Supervisor 分发任务 → Worker 如何工作？ |

**实践任务**: 实现一个 Supervisor 节点，能根据任务类型路由到不同的 Worker。

---

### Day 32 · LangGraph Multi-Agent（下）

**主线**: 完成多 Agent 系统的 Worker 实现与状态管理

| # | 知识点 | 要点 | 与下一知识点的关联 |
|:-:|--------|------|--------------------|
| 1 | Worker Agent 定义 | 每个 Worker 是一个子图或独立 Node；专属工具和 Prompt；输入输出标准化 | Worker 完成后 → 如何汇总结果？ |
| 2 | 状态共享与通信 | 共享 State 设计；消息传递模式；Agent 间上下文传递 | 状态管理好 → 可以实现完整系统 |

**实践任务**: 用 LangGraph 实现一个完整的 Supervisor 多 Agent 系统（研究员 + 作者 + 编辑）。

---

### Day 33 · MCP 协议（上）

**主线**: Agent 世界的"USB 接口" — 标准化的工具连接协议

| # | 知识点 | 要点 | 与下一知识点的关联 |
|:-:|--------|------|--------------------|
| 1 | MCP 是什么？ | 解决的问题：M×N 集成困境；MCP 的定位：模型与工具的标准化接口；与 Function Calling 的关系 | 理解定位 → 学习架构 |
| 2 | MCP 架构 | Client / Server / Transport 三层架构；Host Application 的角色；通信流程 | 架构清楚 → 学习核心能力 |
| 3 | MCP 核心能力 | Resources（数据暴露）/ Tools（操作执行）/ Prompts（交互模板）；三者的区别与配合 | 理解能力 → 动手实现 |

**实践任务**: 阅读 MCP 官方文档，理解协议的核心概念。

---

### Day 34 · MCP 协议（下）

**主线**: 动手构建和使用 MCP Server

| # | 知识点 | 要点 | 与下一知识点的关联 |
|:-:|--------|------|--------------------|
| 1 | 构建 MCP Server | 用 MCP Python SDK 创建一个 Server；定义 Tool（如文件操作、数据库查询）；Transport 配置（stdio / SSE） | Server 建好 → 如何连接？ |
| 2 | MCP Client 集成 | 在 Agent 中接入 MCP Server；工具自动发现；调用流程；与现有 LangChain 工具的桥接 | MCP 生态将在不同框架中出现 |

**实践任务**: 用 MCP SDK 构建一个简单的 MCP Server（例如文件管理工具），并用 Client 接入调用。

---

### Day 35 · 🔨 第五周项目：多 Agent 研究助手

**主线**: 构建一个分工明确的多 Agent 研究团队

| # | 知识点/任务 | 要点 | 关联 |
|:-:|-------------|------|----|
| 1 | 项目设计 | 四个 Agent 角色定义：Planner（分解任务）→ Researcher（搜索信息）→ Writer（撰写报告）→ Reviewer（审核质量） | → |
| 2 | Planner + Researcher 实现 | 接收研究主题 → 分解子问题 → 搜索收集信息 → 输出关键发现 | → |
| 3 | Writer + Reviewer 实现 | Writer 将发现整合为报告 → Reviewer 评估质量并提出修改建议 → 迭代优化 | → |
| 4 | 编排与集成 | 使用 LangGraph 编排四个 Agent；MCP Server 提供外部工具支持 | → |
| 5 | 测试与优化 | 端到端测试；优化 Agent Prompt；处理边界情况 | 第五周完成 ✅ |

**交付物**: 一个多 Agent 协作系统（4 个 Agent 分工合作完成研究报告）+ 一个 MCP Server。

---
---

## 第六周：工程化实践 — Harness Engineering + 框架探索

> **本周目标**: 理解 Harness Engineering，掌握更多主流 AGI 框架  
> **本周交付物**: 一份 Harness Engineering 改进报告 + 用新框架复现的多 Agent 系统

---

### Day 36 · Harness Engineering（上）

**主线**: Agent 的真正产品不是模型，而是模型周围的一切 — 理解 Harness Engineering

> 核心公式：**Agent = Model + Harness**（如果你不是模型，你就是 Harness）  
> 三层递进：Prompt Engineering（怎么问）→ Context Engineering（模型看到什么）→ Harness Engineering（整个系统如何运转）

| # | 知识点 | 要点 | 与下一知识点的关联 |
|:-:|--------|------|--------------------|
| 1 | 什么是 Harness Engineering？ | Harness = 模型之外的一切基础设施：编排循环、工具层、记忆、上下文管理、状态持久化、错误处理、验证和防护栏；类比操作系统 — 模型是 CPU，上下文窗口是 RAM，Harness 是 OS；与 Prompt/Context Engineering 的层级关系（Harness 包含两者） | 理解定义 → 学习 Harness 的组成 |
| 2 | Harness 的 11 大组件 | 编排循环（ReAct/TAO Loop）、工具层、Prompt 管理、上下文管理、状态与检查点、记忆系统、错误处理与重试、安全与权限、验证循环（Verification Loops）、子 Agent 编排、可观测性与日志 | 了解全貌 → 学习关键设计模式 |

**实践任务**: 对照 Harness 11 大组件，分析自己之前构建的 Agent 项目缺失了哪些组件。

---

### Day 37 · Harness Engineering（下）

**主线**: Harness 设计模式与实践

| # | 知识点 | 要点 | 与下一知识点的关联 |
|:-:|--------|------|--------------------|
| 1 | Feedforward 与 Feedback 控制 | **Guides（前馈控制）**：在 Agent 行动前预防错误 — AGENTS.md、Linter 规则、架构约束、工具 Schema；**Sensors（反馈控制）**：在 Agent 行动后检测问题 — 测试、类型检查、LLM-as-Judge；两类执行方式：Computational vs Inferential | 控制机制清楚 → 如何设计验证循环？ |
| 2 | 验证循环与 Steering Loop | 三种验证方式：规则检查（测试/Linter）、视觉反馈（截图）、LLM-as-Judge；**Steering Loop**：每次 Agent 犯错 → 改进 Harness → 让同类错误不再发生 | 验证做好 → 整体架构设计 |
| 3 | Harness 设计七大决策 | ①编排模式 ②上下文策略 ③验证方式 ④权限模型 ⑤工具范围 ⑥Harness 厚度 ⑦构建以删除为目标 | Harness 设计能力是 Agent 工程师的核心技能 |

**实践任务**: 为之前构建的 Agent 项目添加至少 2 项 Harness 改进（如 AGENTS.md 指导文件 + 自动化测试验证循环）。

---

### Day 38 · 主流 Agent 框架探索（上）

**主线**: 广度扩展 — 快速了解主流 Agent 框架

|  #  | 知识点                        | 要点                                                                                                                                                                                                              | 与下一知识点的关联            |
| :-: | -------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------- |
|  1  | Agno                       | 极致性能（Agent 实例化 ~2μs，比 LangGraph 快 5000 倍、内存低 50 倍）；模型无关（可接入任意 LLM，无厂商锁定）；多模态原生支持（文本/图像/音频/视频）；内置 Team 抽象（route/coordinate/collaborate 三种多 Agent 协作模式）；AgentOS 一键部署 + A2A 互操作；Pythonic API 上手极快                  | 高性能轻量方案 → 对比角色协作方案   |
|  2  | **CrewAI**                 | 角色扮演架构（Manager/Worker/Researcher 各司其职，模拟真实团队分工）；灵活编排（sequential/parallel/hierarchical 任务流）；700+ 工具集成（Notion、Stripe、Zoom 等）；Flows 事件驱动编排 + Crews 多 Agent 协作双模式；60% Fortune 500 企业采用；YAML 配置 + Python 代码双入口，上手门槛低 | 角色协作范式 → Claude 原生方案 |
|  3  | Anthropic Claude Agent SDK | Claude 原生支持；Extended Thinking；与 MCP 的深度集成                                                                                                                                                                       | Claude 生态 → 对比选型     |

**实践任务**: 分别阅读三个框架的 Quickstart 文档，完成各框架的 Hello World Agent。

---

### Day 39 · 主流 Agent 框架探索（下）

**主线**: 框架选型与实战对比

|  #  | 知识点            | 要点                                               | 与下一知识点的关联   |
| :-: | -------------- | ------------------------------------------------ | ----------- |
|  1  | 框架选型指南         | 按场景选框架、各框架的 Harness 实现对比（Harness Engineering 视角） | 选型能力 → 综合应用 |
|  2  | 用选定框架复现多 Agent | 选择一个新框架，快速复现第五周的"内容创作团队"；体验不同框架的差异               | 框架广度学习完毕    |


---

### Day 40-42 · 本周回顾 + 弹性时间

| # | 任务 | 要点 |
|:-:|------|------|
| 1 | Harness Engineering 报告 | 撰写一份 Harness Engineering 改进报告，记录分析过程和改进措施 |
| 2 | 框架对比总结 | 整理各框架的优劣势对比表 |
| 3 | 查漏补缺 | 回顾前六周的薄弱环节，针对性补强 |

---
---

## 第七周：生产化 — 评估、安全与部署

> **本周目标**: 掌握 Agent 评估、安全、部署，具备生产化能力  
> **本周交付物**: 一个可部署的 Agent API 服务

---

### Day 43 · Agent 评估（Evals）

**主线**: 如何衡量 Agent 的"好坏" — 从直觉到量化

| # | 知识点 | 要点 | 与下一知识点的关联 |
|:-:|--------|------|--------------------|
| 1 | 为什么需要评估？ | "感觉还行"不可靠；Agent 输出的不确定性；回归测试的必要性 | 知道必要性 → 学习评估维度 |
| 2 | 评估维度与方法 | 正确性、相关性、完整性、安全性；LLM-as-Judge；基于规则检查；人工评估；自动化测试集 | 方法选定 → 工具支持 |
| 3 | Error Analysis | 常见失败模式（工具调用错误、推理偏差、幻觉）；根因分析方法；评估迭代闭环 | 评估发现问题 → 学习如何防护 |

**实践任务**: 为文档问答 Agent 设计评估数据集（10 个问答对），实现 LLM-as-Judge 自动评估。

---

### Day 44 · Agent 安全（Guardrails）

**主线**: 为 Agent 上"保险" — 防止滥用和有害输出

| # | 知识点 | 要点 | 与下一知识点的关联 |
|:-:|--------|------|--------------------|
| 1 | Agent 安全威胁全景 | Prompt Injection（直接/间接）；越狱攻击；数据泄露；恶意工具调用 | 了解威胁 → 学习防护手段 |
| 2 | 输入输出安全 | 用户输入安全检查；Prompt Injection 检测；有害内容检测；PII 脱敏；工具权限控制 | 输入输出安全 → 系统防护 |
| 3 | Guardrails 框架实践 | NeMo Guardrails / OpenAI Moderation API；在 Agent 中集成防护层；安全测试 | 安全机制就绪 → 部署上线 |

**实践任务**: 为 Agent 添加输入验证（Prompt Injection 检测）+ 输出安全检查（PII 脱敏），编写安全测试用例。

---

### Day 45 · Agent 部署（上）

**主线**: 从本地脚本到线上服务

| # | 知识点 | 要点 | 与下一知识点的关联 |
|:-:|--------|------|--------------------|
| 1 | FastAPI 封装 | 将 Agent 封装为 REST API；请求/响应模型设计；异步处理（async/await） | API 封装好 → 需要容器化 |
| 2 | Docker 容器化 | Dockerfile 编写；环境变量管理（API Key 安全）；镜像优化 | 容器化后 → 配置管理 |

**实践任务**: 将 Agent 封装为 FastAPI 服务，编写 Dockerfile。

---

### Day 46 · Agent 部署（下）

**主线**: 异步处理、配置管理与部署上线

| # | 知识点 | 要点 | 与下一知识点的关联 |
|:-:|--------|------|--------------------|
| 1 | 异步与队列 | Agent 执行时间长的问题；后台任务（BackgroundTask / Celery）；WebSocket 实时推送 | 异步处理完 → 配置管理 |
| 2 | 配置与环境管理 | 多环境配置（dev/staging/prod）；.env 文件管理；Secret 管理最佳实践 | 配置就绪 → 部署上线 |
| 3 | 部署方案选择 | 云部署选项（Railway / Fly.io / AWS Lambda）；本地部署（Docker Compose）；成本考量 | 部署完成 → 添加监控 |

**实践任务**: 成功在本地 Docker 环境中运行 Agent API 并通过 API 调用。

---

### Day 47 · Agent 调试与可观测性

**主线**: 生产环境中的 Agent 需要"透明可见"

| # | 知识点 | 要点 | 与下一知识点的关联 |
|:-:|--------|------|--------------------|
| 1 | 结构化日志 | Python logging 最佳实践；JSON 格式日志；日志级别策略 | 日志是基础 → 需要更精细的追踪 |
| 2 | 分布式追踪（Tracing） | OpenTelemetry 概述；Span 与 Trace 的概念；Agent 调用链的追踪 | Tracing 提供调用链 → 需要异常处理 |
| 3 | 指标与告警 | 关键指标：响应时间、Token 消耗、工具调用成功率；Agent 级错误处理；重试与降级策略 | 可观测性完成 |

**实践任务**: 为 Agent API 添加结构化日志 + OpenTelemetry Tracing + 关键指标收集。

---

### Day 48-49 · 弹性时间

| # | 任务 | 要点 |
|:-:|------|------|
| 1 | 部署实践完善 | 完善 Docker 部署、测试 API 稳定性 |
| 2 | 查漏补缺 | 回顾本周内容，解决遗留问题 |

---
---

## 第八周：总结与最佳实践

> **本周目标**: 沉淀学习成果，形成 AI Agent 开发最佳实践指南  
> **本周交付物**: 一份完整的 AI Agent 开发最佳实践与踩坑指南

---

### Day 50 · Agent 架构设计最佳实践

**主线**: 总结 Agent 系统的架构设计经验

| # | 知识点 | 要点 |
|:-:|--------|------|
| 1 | 何时该用 Agent、何时不该用 | 过度 Agent 化的常见误区；简单任务用 Workflow 足矣；Agent 适用场景的判断标准 |
| 2 | Agent 架构选型决策树 | 单 Agent vs 多 Agent 的选择标准；框架选型的关键因素（团队规模、任务复杂度、可控性需求）；Thin Harness vs Thick Harness 的权衡 |
| 3 | System Prompt 设计黄金法则 | 角色定义的最佳实践；指令的结构化与分层；Few-shot 示例的选择与维护；版本管理与 A/B 测试 |

**实践任务**: 回顾自己之前构建的所有 Agent 项目，用架构设计最佳实践进行审视和改进。

---

### Day 51 · 工具设计与 Context 管理踩坑指南

**主线**: 总结工具设计和上下文管理中的常见问题与解决方案

| # | 知识点 | 要点 |
|:-:|--------|------|
| 1 | 工具设计的常见坑 | 工具描述模糊导致模型误选；工具数量过多导致选择困难（Vercel 删除 80% 工具后效果更好的启示）；工具参数设计不合理（过于复杂 vs 过于简单）；工具错误处理不当导致 Agent 死循环 |
| 2 | Context 管理的常见坑 | 上下文爆炸（对话历史无限增长）；信息噪声稀释关键信号；"Lost in the Middle" 问题的实际影响；上下文窗口的成本陷阱 |
| 3 | Token 与成本优化 | Token 消耗的隐形成本（工具 Schema 占用大量 Token）；缓存策略（Prompt Cache）的合理使用；流式输出的成本与体验平衡 |

**实践任务**: 整理自己在项目中遇到的工具设计和 Context 管理问题，形成踩坑清单。

---

### Day 52 · 可靠性与调试最佳实践

**主线**: 如何让 Agent 在生产环境中稳定可靠

| # | 知识点 | 要点 |
|:-:|--------|------|
| 1 | 结构化输出的可靠性保障 | JSON 输出不稳定的根因分析；多层验证策略（Schema 约束 + Pydantic 验证 + 重试机制）；不同模型的结构化输出能力对比 |
| 2 | Agent 循环的防护 | 死循环检测与防护（max_iterations 不够用的情况）；Agent 陷入重复行为的识别与干预；超时控制与优雅降级 |
| 3 | 调试方法论 | Agent 调试的三板斧：日志、Tracing、Replay；LangSmith 调试实战技巧；如何快速定位"模型决策错误"vs"工具执行错误"vs"编排逻辑错误" |

**实践任务**: 为已有 Agent 补充调试工具链（结构化日志 + Tracing + 错误分类统计）。

---

### Day 53 · 安全与评估最佳实践

**主线**: Agent 安全防护与质量评估的实战经验

| # | 知识点 | 要点 |
|:-:|--------|------|
| 1 | Prompt Injection 防御实战 | 常见攻击向量与真实案例；多层防御策略（输入清洗 + 指令隔离 + 输出过滤）；间接 Prompt Injection（通过检索文档注入）的特殊处理 |
| 2 | 评估体系搭建 | 评估数据集的构建方法（人工标注 vs 合成数据）；LLM-as-Judge 的校准与偏差处理；评估自动化流水线的设计（CI/CD 集成） |
| 3 | 人工介入机制设计 | Human-in-the-Loop 的最佳实践；哪些操作必须人工审批（高风险工具调用、外部通信）；审批流程的用户体验优化 |

**实践任务**: 编写一份 Agent 安全检查清单（Checklist），涵盖输入、输出、工具调用、数据隐私。

---

### Day 54 · 多 Agent 与生产部署踩坑指南

**主线**: 多 Agent 协作与生产部署的实战经验

| # | 知识点 | 要点 |
|:-:|--------|------|
| 1 | 多 Agent 系统的常见坑 | Agent 间上下文污染；Supervisor 决策偏差导致任务分配错误；Agent 间通信的信息丢失；多 Agent 系统的调试困难 |
| 2 | 生产部署注意事项 | API Key 管理与轮换策略；Rate Limiting 的设计（API 层面 + Agent 层面）；长时间运行任务的超时处理；成本监控与预警 |
| 3 | 性能优化策略 | 并发请求处理；响应延迟优化（流式输出、预计算）；向量数据库的索引优化；模型选择策略（按任务复杂度选模型） |

**实践任务**: 整理多 Agent 和生产部署的踩坑经验，形成运维手册。

---

### Day 55 · 最佳实践指南撰写

**主线**: 将所有经验沉淀为一份完整的最佳实践文档

| # | 任务 | 要点 |
|:-:|------|------|
| 1 | 文档结构设计 | 按主题组织：架构设计、工具设计、Context 管理、可靠性、安全、评估、部署、多 Agent |
| 2 | 内容撰写 | 每个主题包含：最佳实践（Do）、常见陷阱（Don't）、案例分析、代码示例 |
| 3 | 速查表制作 | 制作快速参考卡片：Agent 选型速查、工具设计 Checklist、安全防护 Checklist、部署 Checklist |

---

### Day 56 · 🎯 回顾与展望

**主线**: 沉淀学习成果，规划下一阶段

| # | 任务 | 要点 |
|:-:|------|------|
| 1 | 知识地图回顾 | 对照 `research.md` 中的知识体系总览，检查每个分支的掌握程度；标记薄弱环节 |
| 2 | 项目复盘 | 所有项目的收获与不足；技术选型的反思；最有价值的学习资源 |
| 3 | 学习总结撰写 | 写一篇学习总结博文（可发布到 GitHub / 博客）；整理代码仓库 |
| 4 | 进阶方向规划 | 可选方向：A2A 协议深入 / Agent 安全研究 / 垂直领域 Agent / 开源框架贡献 / Agent 产品化 |
| 5 | 持续学习路线图 | 订阅资源（Newsletter、Discord）；设定下一阶段的学习目标 |

---

## 📊 八周知识脉络总览

```
Week 1: LLM 基础
  Token → Embedding → Chat → Context Engineering → Agent 概念 → 设计模式
  │                                                                │
  └──────────── 理解底层原理，建立概念框架 ──────────────────────────┘

Week 2: 动手实现
  Function Calling → Tool Use → ReAct → 结构化输出 → CLI Agent
  │                                                       │
  └──────────── 从零实现一切，深入理解底层机制 ───────────────┘

Week 3: 框架入门
  LangChain 基础 → LCEL → Tools → Memory → RAG
  │                                          │
  └──────────── 用框架简化开发，理解检索增强 ──┘

Week 4: 框架进阶
  LangChain 进阶（LCEL 高级模式 + Callbacks + Middleware）→ LangGraph → Agentic RAG
  │                                                                            │
  └──────────── 掌握中间件体系，构建图状态机 Agent ────────────────────────────┘

Week 5: 协作与互操作
  多 Agent 概念 → LangGraph Multi-Agent → MCP 协议
  │                                               │
  └──────────── 多 Agent 协作，标准化协议 ────────┘

Week 6: 工程化与广度
  Harness Engineering → 主流 AGI 框架探索（Smolagents / OpenAI SDK / Anthropic SDK）
  │                                                                            │
  └──────────── 系统工程思维，框架选型能力 ────────────────────────────────────┘

Week 7: 生产化
  评估 → 安全 → 部署 → 可观测性
  │                            │
  └──────────── 从 Demo 到 Production 的最后一公里 ──┘

Week 8: 沉淀总结
  架构最佳实践 → 工具与 Context 踩坑 → 可靠性与调试 → 安全与评估 → 多 Agent 与部署 → 最佳实践指南
  │                                                                                    │
  └──────────── AI Agent 开发最佳实践与踩坑注意指南 ──────────────────────────────────────┘
```

---

*生成日期: 2026-04-10*
*基于 research.md 计划细化*
