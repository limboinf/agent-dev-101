
---

> 摘要：上一篇我们搞懂了 Context Engineering 的定义、四大支柱和 LangChain 的四种策略。但"知道"和"会用"之间隔着一条鸿沟。这篇我们聚焦三个在顶级 Agent 产品中被反复验证的实战模式——渐进披露、上下文路由、工具管理——然后揭示一个被大多数人忽视的隐藏基础设施：KV Cache。接着，看看 LangChain、LangGraph、Deep Agent 三大框架是怎么把这些模式变成可用的 API 的。最后，汇总 Anthropic、Manus、Cognition 等团队在生产环境中总结的 8 条最佳实践。

## 一、渐进披露（Progressive Disclosure）

### 为什么不能一次性全塞进去？

大多数人写 Agent 的第一版，都是这样的：
```text
系统提示: 你是一个万能助手...（2000 tokens 的详细指令）
工具定义: [搜索, 代码执行, 文件操作, 数据库查询, ...]（3000 tokens）
示例: [10 个 few-shot 示例]（2000 tokens）
───────────────────────────────────────
还没开始对话，上下文窗口已经吃掉 7000 tokens
```

**问题是：90% 的对话根本用不到这些信息。** 你为每一次调用都付了全额 Token 费用，但大部分 Token 都是"备而不用"的噪声。

### 渐进披露

**渐进披露**（Progressive Disclosure）是一个经典的 UI 设计原则：不要一次展示所有功能，而是根据用户的操作路径逐步展现。 手机 App 的设置页面不会把 200 个选项一次铺开——它先给你 10 个常用选项，点进去才看到更多。这个原则完美适用于 Context Engineering。我们可以把上下文分成三层：

```text
┌──────────────────────────────────────────────────┐
│  第一层：Discovery（发现层）                        │
│  ├── 轻量级元数据                                  │
│  ├── 工具名称 + 一句话描述                          │
│  └── Token 成本: ~200                             │
├──────────────────────────────────────────────────┤
│  第二层：Activation（激活层）                        │
│  ├── 被选中工具/能力的完整指令                       │
│  ├── 参数定义、约束说明                             │
│  └── Token 成本: ~500                             │
├──────────────────────────────────────────────────┤
│  第三层：Execution（执行层）                         │
│  ├── Few-shot 示例                                │
│  ├── 参考文档 / 代码片段                            │
│  └── Token 成本: ~1500（但只在需要时加载）           │
└──────────────────────────────────────────────────┘
```

模型在第一层就能判断"我需要什么工具"，只有确认需要后才加载第二层和第三层。**大部分请求只用到第一层的 200 tokens，而不是全量的 2200 tokens。**

### 真实案例：Claude Code 的 Skill 机制

Claude Code（Anthropic 的命令行 Agent）的做法非常优雅：

1. **Skills 存在文件系统中**——不是硬编码在 System Prompt 里，而是以文件形式存放在工作区的 `.claude/` 目录下
2. **Agent 通过 Bash 工具发现它们**——执行 `ls .claude/skills/` 就能看到有什么 Skill 可用
3. **按需读取和加载**——只有当任务需要某个 Skill 时，才用 `cat .claude/skills/xxx.md` 读取完整指令

```text
Agent 上下文的变化过程：

轮次 1: [系统指令 + 工具定义(bash, read, edit)]    → ~800 tokens
轮次 2: Agent 发现 skills 目录                      → +50 tokens
轮次 3: 用户要求"写测试"，Agent 加载 testing skill  → +300 tokens
轮次 4: 继续执行，testing skill 指令已在上下文中      → 复用
```

**关键洞察：工具定义本身就是一种"技能的元数据"。Agent 先用轻量级工具（bash）去发现更丰富的能力，而不是一开始就加载所有能力的完整定义。**

### 真实案例：Manus 的层次化行动空间

Manus 的设计更加系统化。他们把所有能力分成三层：

```text
┌─────────────────────────────────────────────────────┐
│  Layer 1: 核心原子工具（~20 个）                      │
│  ├── browser_navigate, browser_click, ...            │
│  ├── shell_exec, file_read, file_write, ...          │
│  └── 始终在上下文中，token 成本固定                     │
├─────────────────────────────────────────────────────┤
│  Layer 2: 沙箱工具（通过 bash CLI 暴露）               │
│  ├── 系统命令、包管理、构建工具                         │
│  └── 不占工具定义 token，Agent 直接 shell 调用          │
├─────────────────────────────────────────────────────┤
│  Layer 3: 代码 / 包 / 库                              │
│  ├── 复杂逻辑链（数据处理、API 调用组合）                │
│  └── Agent 编写代码来实现，而不是定义为 tool              │
└─────────────────────────────────────────────────────┘
```

Manus 联合创始人 Peak Ji 明确说过：

> "We cap the tool count at roughly twenty core atomic tools. Complex logic chains are offloaded to code and packages."
>
> ——我们把工具数量控制在大约 20 个核心原子工具。复杂的逻辑链通过代码和包来完成。

这意味着 **Manus 的工具定义在上下文中的 Token 开销是固定的**——大约 20 个工具的 Schema，不会因为功能增加而线性膨胀。需要更复杂的能力？Agent 写代码来实现，而不是增加工具定义。

---

## 二、上下文路由（Context Routing）

### 不同的问题，需要不同的上下文

如果你的 Agent 既能搜索网页、又能写代码、还能查数据库，那每次调用都把三组工具定义全塞进去就是浪费。**上下文路由的核心思想是：根据当前任务的类型，动态加载不同的上下文。**

### Manus 的可恢复压缩（Restorable Compression）

Manus 在长对话中的上下文管理策略非常值得学习。他们把压缩分成两种：

| 压缩类型          | 特点               | 信息损失 | 典型应用         |
| ------------- | ---------------- | ---- | ------------ |
| **Compact**   | 可逆的，保留 URL 等关键引用 | 极低   | 工具调用结果的"精简版" |
| **Summarize** | 有损的，只保留核心语义      | 中等   | 旧对话轮次的摘要     |

每个工具调用结果都有两种表示——**full（完整版）**和 **compact（精简版）**。当对话变长，较早的工具结果会被自动替换为 compact 版本：

```text
对话上下文演变过程：

轮次 1: search_result = [full]         ← 完整搜索结果
轮次 2: code_output = [full]           ← 完整代码输出
轮次 3: search_result = [compact]      ← 自动压缩为精简版
        code_output = [full]           ← 最近的保持完整
轮次 5: search_result = [compact]      ← 精简版
        code_output = [compact]        ← 也被压缩了
        new_result = [full]            ← 最新的保持完整
```

**为什么叫"可恢复"压缩？** 因为 compact 版本保留了关键引用（如 URL、文件路径）。如果 Agent 后续需要更多细节，它可以重新调用工具获取完整信息。这和传统的"压缩=丢弃"完全不同。

### 文件系统作为无限上下文

这是一个被低估的模式：**让 Agent 把文件系统当作自己的外部记忆。**

```python
# Agent 将中间结果写入文件，而不是保留在上下文中
def agent_step(task, context):
    analysis = llm.analyze(task, context)
    
    # 把详细结果写入文件（从上下文中"卸载"）
    write_file("analysis_result.md", analysis.details)
    
    # 上下文中只保留摘要 + 文件路径
    context.append({
        "summary": analysis.summary,
        "details_path": "analysis_result.md"  # 需要时再读取
    })
    return context
```

Manus 和 Claude Code 都大量使用这个模式。特别是 **todo.md 模式**——Agent 在执行复杂任务时，会主动维护一个 `todo.md` 文件：
```markdown
# todo.md — Agent 自己维护的任务清单
## 已完成
- [x] 分析用户需求
- [x] 搜索相关 API 文档

## 进行中
- [ ] 实现数据处理模块 ← 当前步骤

## 待做
- [ ] 编写单元测试
- [ ] 更新文档
```

**这里有一个深刻的洞察：Agent 通过更新 todo.md 来操纵自己的注意力。** 每次读取这个文件，Agent 就能快速回忆"做到哪了、下一步该做什么"——而不需要在上下文中保留完整的执行历史。这本质上是 Agent 在 **管理自己的 Context**。

---

## 三、工具管理（Tool Management）

### 工具爆炸问题

MCP（Model Context Protocol）的流行带来了一个新问题：**工具太多了。**

每个 MCP 服务器提供几个到几十个工具，连接三五个服务器，工具列表就可能膨胀到 50-100 个。每个工具的 JSON Schema 定义大约 50-200 tokens，100 个工具就是 5000-20000 tokens——还没开始对话，上下文窗口就吃掉了 15-25%。

更致命的是模型的选择困难。Anthropic 在他们的 Agent 最佳实践中直接说了：

> "If a human engineer can't look at a list of tool names and descriptions and **definitively** say which tool should be used, the AI agent can't do better."
>
> ——如果一个人类工程师看着工具列表都无法明确说出该用哪个工具，AI Agent 也不会更好。

### Mask Don't Remove（遮蔽而非移除）

面对工具爆炸，很多人的第一反应是"动态添加/移除工具"——用到什么就注册什么，不用就删掉。**但这是个坑。**

为什么？因为 **KV Cache**。

```text
动态添加/移除工具的代价：

请求 1: tools = [A, B, C, D, E]        → 缓存 prefix: [system + tools_ABCDE]
请求 2: tools = [A, B, C, F, G]        → prefix 变了！缓存完全失效
请求 3: tools = [A, B, C, D, E]        → 又变了！又要重新计算

每次变更工具列表 = 缓存失效 = 首 Token 时间翻倍 + 成本飙升
```

正确的做法是 **Mask Don't Remove**——工具定义保持不变（保护 KV Cache），但限制模型在当前步骤可以调用哪些工具。

打个比方：想象一个自动售货机（模型），里面有 10 种饮料（10 个工具）。Mask 就是**把某些饮料的按钮用胶带封住**——你按不下去，机器也不会出那个饮料。不是贴个纸条说"请不要买可乐"（模型可能无视），而是物理上让你**按不了**可乐的按钮。

为什么不能只靠 Prompt？看这个场景——假设你有一个客服 Agent，有 3 个工具：`search_knowledge`（搜索知识库）、`transfer_human`（转人工）、`refund`（退款）。你希望必须先搜索，搜不到再转人工，绝不能直接退款：

```text
❌ 软约束（靠 Prompt）：
System: "请先搜索知识库，不要直接退款"
用户:   "我要退款！！！气死了！！"
模型:   好的！→ 调用 refund 💀（被用户情绪带跑了，无视了你的指令）

✅ 硬约束（Mask）：
第一轮：只解封 search_knowledge → 模型想调 refund 也调不了
第二轮：搜索没结果，解封 transfer_human → 只能转人工
refund 的按钮从头到尾都是封住的
```

核心思想：**不要相信模型会"听话"，用机制保证它"不可能"犯错。** 下面看三种实现方式：

**方法一：OpenAI 的 `allowed_tools` 参数（API 级别）**

OpenAI 提供了最简单的方案——工具全部传入，但用 `allowed_tools` 限制当前步骤可以调用哪些：

```python
from openai import OpenAI
client = OpenAI()

# 工具定义始终不变（保护 KV Cache）
tools = [
    {"type": "function", "function": {"name": "search_knowledge", ...}},
    {"type": "function", "function": {"name": "transfer_human", ...}},
    {"type": "function", "function": {"name": "refund", ...}},
]

# 第一步：只允许搜索
response = client.responses.create(
    model="gpt-4.1",
    tools=tools,
    allowed_tools=["search_knowledge"],  # 只能搜索，调不了 refund
    input="用户说：我要退款！！！"
)

# 第二步：搜索没结果，多开一个转人工
response = client.responses.create(
    model="gpt-4.1",
    tools=tools,                          # 工具列表没变，KV Cache 命中
    allowed_tools=["search_knowledge", "transfer_human"],
    input=messages
)
```

**关键点：`tools` 数组始终不变，KV Cache 保持命中；`allowed_tools` 在 API 层面硬性拦截非法调用。**

**方法二：LangGraph 状态机（框架级别）**

如果你用 LangGraph，可以直接把工具调用流程建模为状态机——用图的边来定义"哪个状态之后可以调用哪些工具"：

```python
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

# 定义状态机：search → 判断结果 → transfer 或结束
graph = StateGraph(AgentState)
graph.add_node("search", ToolNode([search_knowledge]))    # 搜索节点只绑定搜索工具
graph.add_node("transfer", ToolNode([transfer_human]))     # 转人工节点只绑定转人工

graph.set_entry_point("search")                            # 必须从搜索开始
graph.add_conditional_edges("search", check_result, {
    "not_found": "transfer",   # 没找到 → 转人工
    "found": END,              # 找到了 → 直接结束
})
graph.add_edge("transfer", END)

# refund 工具根本不在图里，模型不可能调用到它
```

这就是"状态机"的含义——每个节点就是一个状态，边定义了合法的转移，**不存在的边 = 不可能发生的调用**。

**对比一下：**

| 方式                 | 约束强度           | 适用场景             |
| ------------------ | -------------- | ---------------- |
| Prompt 里写"不要调 XX"  | 软约束，模型可能无视     | 简单场景，容错空间大       |
| `allowed_tools` 参数 | ✅ 硬约束，API 层面拦截 | 用 OpenAI 等商业 API |
| LangGraph 状态机      | ✅ 硬约束，框架层面拦截   | 复杂多步流程编排         |

### 一致性命名约定

注意上面工具名称的规律？`browser_search`、`browser_click`、`shell_exec`、`file_read`——都有一致的前缀。这不是巧合：

```text
browser_*    → 浏览器操作组
shell_*      → 终端命令组
file_*       → 文件操作组
db_*         → 数据库操作组
```

一致的命名前缀带来两个好处：

1. **模型更容易理解工具的归属和用途**——前缀本身就是语义信息
2. **轻松实现分组屏蔽**——一行代码就能限制"只允许 browser_* 组的工具"

---

## 四、KV Cache：被忽视的隐藏基础设施

上面多次提到 KV Cache——为什么 Manus 说 **Cache Hit Rate 是他们最关注的指标**？

简单说：Agent 每次调用 LLM 都是一个新请求，但相邻请求往往有大量相同的前缀（System Prompt、工具定义、历史对话）。KV Cache 能让这些重复前缀**不用重新计算**，直接复用——省时间、省钱（缓存命中的 Token 只需 0.1x ~ 0.5x 的价格）。

Manus 团队明确表示：

> "Cache hit rate is the single most important metric for optimizing agent costs and latency."
>
> ——缓存命中率是优化 Agent 成本和延迟的**头号指标**。

这就是前面所有设计的底层逻辑：工具列表保持稳定（Mask Don't Remove）、一致性命名前缀——**都是为了保护缓存命中率**。

实践中只需记住三条原则：
**① 稳定前缀**——不要在 System Prompt 开头放时间戳等动态内容；
**② 追加式修改**——只在消息末尾追加，不要修改已有消息；
**③ 确定性序列化**——工具定义的 JSON key 顺序要固定（`sort_keys=True`）。三条都指向同一个目标：**让上下文的前缀尽可能保持不变。**

> 💡 关于 KV Cache 和 Prompt Cache 的底层原理、各厂商实现差异、定价策略，我们在下一篇 **《Prompt Cache 全解析》** 中详细展开。

---

## 五、框架实践：LangChain / LangGraph / Deep Agent 的 Context Engineering

前面讲的都是"原理和模式"，现在看看主流框架是怎么把这些模式落地的。

### LangChain Middleware：上下文工程的钩子系统

LangChain 最新的 Agent 架构引入了 **Middleware（中间件）** 机制——你可以在 Agent 循环的**每一步**钩入逻辑，动态修改上下文。这正是 Context Engineering 从"理论"变成"代码"的关键：

```python
from langchain.agents import create_agent
from langchain.agents.middleware import dynamic_prompt, ModelRequest

@dynamic_prompt
def state_aware_prompt(request: ModelRequest) -> str:
    """根据对话长度动态调整系统提示——这就是渐进披露"""
    message_count = len(request.messages)
    base = "你是一个专业的代码审查助手。"
    
    if message_count > 10:
        base += "\n这是一段长对话——请更加简洁。"
    return base

agent = create_agent(
    model="gpt-4.1",
    tools=[...],
    middleware=[state_aware_prompt]
)
```

LangChain 把上下文分为三个来源，对应不同的工程手段：

| 来源                         | 说明                   | 典型用法            |
| -------------------------- | -------------------- | --------------- |
| **State（短期记忆）**            | 当前会话的消息列表、scratchpad | 根据消息数量调整 prompt |
| **Store（长期记忆）**            | 跨会话的用户偏好、知识          | 读取用户偏好注入 prompt |
| **Runtime Context（运行时配置）** | 用户 ID、角色、环境变量        | 按用户角色切换工具权限     |

LangChain 还提供了内置中间件来处理最常见的 Context Engineering 需求：

```python
from langchain.agents.middleware import SummarizationMiddleware

agent = create_agent(
    model="gpt-4.1",
    tools=[...],
    middleware=[
        SummarizationMiddleware(
            model="gpt-4.1-mini",    # 用小模型做摘要，省钱
            trigger={"tokens": 4000}, # 超过 4000 tokens 触发
            keep={"messages": 20},    # 保留最近 20 条消息
        ),
    ],
)
```

**关键设计：SummarizationMiddleware 是持久化的**——它会永久替换旧消息为摘要并写入 State，而不是每次调用临时裁剪。这和前面讲的"滑动窗口 + 摘要"模式完全对应。

### LangGraph：图结构 + State 实现精细控制

LangGraph 是 LangChain 的底层编排框架，它把 Agent 建模为**状态图（StateGraph）**——节点是处理逻辑，边是路由条件，共享的 State 对象在节点间传递。这种结构天然支持 Context Engineering：

```text
┌──────────┐     ┌──────────┐     ┌──────────┐
│  理解意图  │ ──→ │  选择工具  │ ──→ │  执行工具  │
│ (State A) │     │ (State B) │     │ (State C) │
└──────────┘     └──────────┘     └──────────┘
       │                                 │
       └────── 每个节点可以读写 State ──────┘
       └── 每个节点可以控制 LLM 看到什么 ──┘
```

- **Write Context**：LangGraph 的 Checkpointer 实现短期记忆（线程级持久化），Store 实现长期记忆（跨会话），LangMem 提供记忆管理抽象
- **Select Context**：每个节点可以从 State 中只取出需要的字段传给 LLM——这就是**上下文路由**的代码实现
- **Compress Context**：在特定节点插入摘要逻辑，或对工具输出做后处理压缩
- **Isolate Context**：通过 State Schema 将不同类型的信息存在不同字段，只在需要时暴露给 LLM

> LangGraph 的核心哲学：**Context Engineering 不是 Prompt 的事，是图结构的事。** 你设计图的拓扑和 State Schema，就是在设计上下文的流动方式。

### LangChain Deep Agent：渐进披露的框架级实现

LangChain 最新发布的 **Deep Agent** 直接内置了我们前面讲的核心模式：

**① 渐进披露 = Skills 机制**

Deep Agent 的 Skills 完美体现了三层渐进披露：

```python
from deepagents import create_deep_agent

agent = create_deep_agent(
    model="claude-sonnet-4-6",
    # Memory 始终加载（轻量，类似 Discovery 层）
    memory=["/project/AGENTS.md"],
    # Skills 按需加载（只读 frontmatter 元数据，需要时才加载全文）
    skills=["/skills/research/", "/skills/web-search/"],
)
```

> Deep Agent 启动时只读取每个 SKILL.md 的 frontmatter（名称+描述），当判断任务相关时才加载完整内容。这和 Claude Code 的文件系统发现机制异曲同工。

**② 自动压缩 = Offloading + Summarization**

- **Offloading**：当工具调用的输入/输出超过 20,000 tokens，自动存入文件系统，上下文中只保留引用和前 10 行
- **Summarization**：当对话达到模型 `max_input_tokens` 的 85% 时自动触发，保留最近 10% 的 tokens 作为新鲜上下文，旧消息由 LLM 生成摘要

**③ 上下文隔离 = Subagent**

```text
主 Agent（干净的上下文）
  ├── task("调研竞品定价")  → 子 Agent 1（独立上下文，可能用了 50k tokens）
  │                          └── 返回: 2k tokens 的摘要报告
  ├── task("分析技术方案")  → 子 Agent 2（独立上下文）
  │                          └── 返回: 1.5k tokens 的分析结论
  └── 主 Agent 只看到两份简洁报告，上下文保持干净
```

### 三者的关系

```text
┌─────────────────────────────────────────────────────┐
│  Deep Agent（开箱即用，内置最佳实践）                  │
│    ├── 自动 Offloading / Summarization               │
│    ├── Skills 渐进披露                                │
│    └── Subagent 上下文隔离                            │
├─────────────────────────────────────────────────────┤
│  LangChain Agent + Middleware（灵活组合）              │
│    ├── SummarizationMiddleware                       │
│    ├── dynamic_prompt / dynamic_tools                │
│    └── LLMToolSelectorMiddleware                     │
├─────────────────────────────────────────────────────┤
│  LangGraph（底层编排，最大控制力）                      │
│    ├── StateGraph + Checkpointer + Store             │
│    ├── 节点级上下文控制                                │
│    └── 自定义 Reducer 合并策略                         │
└─────────────────────────────────────────────────────┘
```

**选择建议：** 快速搭建用 Deep Agent；需要中等定制用 LangChain + Middleware；需要完全控制上下文流动用 LangGraph。

---

  >看看 LangChain、LangGraph、Deep Agent 三大框架是怎么把这些模式变成可用的 API 的。**最后，汇总 Anthropic、Manus、Cognition 等团队在生产环境中总结的 8 条最佳实践。**
 
## 六、Agent 开发中的 Context Engineering 最佳实践

模式和框架都介绍完了，最后我们汇总一份**实战检查清单**——这些最佳实践来自 Anthropic、Manus、Cognition、12-Factor Agents 等多个团队在生产环境中的经验教训。

> 🤣 ...
> 
**由于小红书图片大小限制，请移步到下一篇笔记《Agent dev:Agent 开发中的 Context Engineering 最佳实践》** 

实践列表：
- 实践 1：把上下文当作有限预算来管理
- 实践 2：System Prompt 找到"正确的高度"
- 实践 3：保留错误，不要清除失败痕迹
- 实践 4：不要被自己的 Few-shot 套牢
- 实践 5：工具设计要为 Token 效率服务
- 实践 6：Context Rot 和四种上下文失败模式
- 实践 7：共享上下文而非拆分决策（Cognition 原则）
- 实践 8：为苦涩教训而建（Bitter Lesson-Pilled）


### 实践 1：把上下文当作有限预算来管理

> 📖 来源：[Anthropic - Effective Context Engineering for AI Agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)（2025.9）、[Chroma - Context Rot Research](https://research.trychroma.com/context-rot)（2025.7）

Anthropic 在他们的 Context Engineering 指南中反复强调一个核心原则：

> ——好的上下文工程就是找到**最小的高信号 Token 集合**，最大化期望结果的概率。

**每增加一个 Token，都有成本**——不仅是 API 费用，更是**注意力成本**。
Gemini 团队在用 Gemini 2.5 玩宝可梦的实验中发现：即使 Gemini 支持 100 万+ Token 上下文窗口，**超过 10 万 Token 后 Agent 表现开始急剧恶化**——它不再生成新策略，而是**机械重复历史动作**。这不是模型的能力问题，是上下文过载导致的注意力退化。

Anthropic 在他们的工程指南中给出了实操建议：

> "Start by testing a minimal prompt with the best model available to see how it performs on your task, and then add clear instructions and examples to improve performance based on failure modes found during initial testing."
> 
> ——先用最小 prompt + 最强模型测试，根据失败模式逐步添加指令。

**「预算管理」检查清单——添加信息前问自己：**

1. 这个信息是当前步骤**真正需要的**吗？→ 不需要就别加
2. 能不能让 Agent 在需要时**即时检索**（Just-in-Time），而不是预加载？→ 参考 Claude Code 的做法：维护轻量级标识符（文件路径、URL、查询），在需要时用工具动态加载
3. 这个 Token 增加的是**信号**还是**噪声**？→ Chroma 的研究表明，无关内容不是"中性的占位符"，它**会**影响模型行为
4. 上下文总量是否接近模型的**软上限**？→ 不是窗口大小的上限，而是性能开始退化的拐点（通常远小于窗口大小）

### 实践 2：System Prompt 找到"正确的高度"

Anthropic 观察到两种常见的 System Prompt 失败模式：

```text
❌ 太死板（硬编码 if-else）：
  "如果用户问账单 AND 账户是企业版 THEN 执行方案A..."
  → 脆弱，边界情况维护不过来

❌ 太模糊（假设共享上下文）：
  "用友善的方式帮助用户解决问题。"
  → 模型不知道你的标准是什么

✅ 正确的高度（具体但灵活）：
  - 足够具体：给模型清晰的行为边界和判断标准
  - 足够灵活：让模型用启发式方法处理未预见的情况
  - 用 XML 标签或 Markdown 标题分隔不同区块
```

Anthropic 把这称为 **"Right Altitude"**（正确的高度）—— 介于硬编码和过度模糊之间的 Goldilocks 区间。**具体怎么做？Anthropic 给出了结构化建议：**

1. **分区组织 Prompt**——用 XML 标签或 Markdown 标题把 Prompt 分成清晰的区块：`<background_information>`、`<instructions>`、`## Tool guidance`、`## Output description` 等。虽然随着模型越来越强，精确格式的重要性在降低，但清晰的分区仍然有助于模型理解你的意图。
2. **最小化但完整**—最小化不等于简短，而是每一条指令都有存在的理由。
3. **不要堆砌边界情况**——很多团队会把一堆 edge case 塞进 prompt，试图覆盖所有规则。Anthropic 明确不推荐这样做。取而代之的是：精选一组**多样的、规范的示例**来展示期望行为。对 LLM 来说，示例就是"一图胜千言"。
4. **迭代式开发**——先用最小 prompt + 最强模型测试，观察失败模式，然后针对性地添加指令。**不是一开始就堆满规则，而是在失败中逐步构建。**

Claude Code 创始人 Boris Cherny 在 Pragmatic Engineer 播客中也提到了 `claude.md` 的极简主义原则：**指令就是技术债。** 如果模型已经进步到能原生理解某个任务，对应的指令就应该被删除，以减少上下文噪声。如果你的 `claude.md` 超过几千 Token，考虑重头开始重新评估。

### 实践 3：保留错误，不要清除失败痕迹

这是 Manus 团队分享的**最反直觉**的经验。Peak Ji 在原文中专门用了一个小节叫 **"Keep the Wrong Stuff In"**：

> Agent 会犯错。这不是 bug，是现实。在多步骤任务中，失败不是例外，而是循环的一部分。

面对错误，很多人的第一反应是"清理上下文、重试"。Peak Ji 直接指出这是个坑：

> 擦除失败就是擦除证据。没有证据，模型就无法自适应。

**为什么保留错误有效？** 当模型在上下文中看到一个失败的动作以及对应的错误信息（比如 stack trace、错误码），它会**隐式更新内部信念**，把自己的先验概率从类似的动作上移开，从而降低重复犯错的概率。这就是上下文内学习（in-context learning）的力量。

Manus 团队认为，**错误恢复能力是真正 agentic 行为的最清晰标志之一**，但这个能力在学术研究和公开 benchmark 中严重被低估——大多数评测只关注理想条件下的任务成功率。

**实操建议：**
- ✅ 出错后保留完整的 action + error observation 在上下文中
- ✅ 如果上下文太长需要压缩，可以压缩成功的步骤，但**优先保留失败的步骤**
- ❌ 不要在出错后简单重试并清除痕迹——模型会失去"教训"
- ❌ 不要过度依赖 temperature 随机性来"碰运气"——让模型从证据中学习

### 实践 4：不要被自己的 Few-shot 套牢

> 📖 来源：[Manus - Context Engineering for AI Agents: Lessons from Building Manus](https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus)（2025.7）

LLM 是极其优秀的模式模仿者。Few-shot  在单次调用中是强大的技术，但**在 Agent 的长对话中会反噬**。当上下文中充满了相似的 action-observation 对时，模型会**机械地模仿已有模式**，即使当前情况已经不适用了。

Manus的具体例子：

> 比如用 Manus 审查 20 份简历，Agent 会陷入"节奏"——仅仅因为上下文中看到了类似的模式就重复相同的动作。这导致漂移、过度泛化、甚至幻觉。

**问题本质：Agent 的历史动作本身变成了隐式的 Few-shot 示例。** 前面处理 10 份简历的方式"教会"了模型后面 10 份也要这样处理——即使后面的简历有完全不同的特征需要关注。上下文越均匀、模式越一致，Agent 就越脆弱。

**Manus 的解决方案：引入结构化的多样性（Structured Variation）：**

```text
具体做法：

1. 序列化模板多样化
   → 不同的 action-observation 对使用不同的序列化格式
   → 同一个工具的返回结果用略微不同的结构呈现

2. 措辞微调
   → action 的描述用不同的措辞（同义替换）
   → observation 的呈现顺序做小幅变化

3. 格式差异
   → 交替使用 JSON/Markdown/纯文本格式
   → 字段顺序做随机调整
```

> 上下文越均匀，Agent 就越脆弱。

核心洞察：这种"受控噪声"不是在降低质量，而是在**打破模式锁定**，让模型在每一步都重新评估当前情况，而不是惯性地复制上一步的行为。

### 实践 5：工具设计要为 Token 效率服务

工具不仅要"能用"，还要**返回最少、最高信号的信息**。
```python
# ❌ 糟糕的工具设计——一次返回所有数据
def get_all_tickets():
    """返回 1000 条工单的完整对话历史"""  # 一次吃掉几千 tokens
    ...

# ✅ 好的工具设计——渐进披露
def search_tickets(query: str, limit: int = 5):
    """搜索相关工单，只返回 ID 和摘要"""  # 几百 tokens
    ...

def get_ticket_details(ticket_id: str):
    """获取单个工单的完整详情"""  # 按需加载
    ...
```

Anthropic 从他们的 SWE-bench 实践和内部 Slack 工具优化总结了**五条工具设计原则**：

**① 选对工具，不选多工具
**每个工具都应该有明确的、不重叠的用途**——太多工具或功能重叠会让 Agent 选错。

**② 命名空间化**
给工具加一致的前缀——`browser_navigate`、`browser_click`、`shell_exec`、`shell_read`。不只是可读性，还能让 logit masking 按前缀分组屏蔽（Manus 就是这么做的）。

**③ 返回有意义的上下文**
工具返回值**恰到好处**。一个简洁但信息量充足的 72 Token 返回值，远好于一个 5000 Token 的完整数据 dump。

**④ Token 效率优化**
实现分页、范围选择、过滤和截断，并设置合理的默认值。Claude Code 将工具返回值默认限制在 **25,000 Token**。如果必须截断，在返回中明确告诉 Agent："结果已截断，可以用更精确的查询重试。"——不要返回晦涩的错误码。

**⑤ Prompt-engineering 工具描述**
工具描述本身需要和 System Prompt 一样精心设计。
> 一个经验法则：想想你在人机交互（HCI）上投入了多少精力，然后**计划在 Agent-Computer Interface（ACI）上投入同样多的精力**。

### 实践 6：Context Rot 和四种上下文失败模式

> 📖 来源：[Drew Breunig - How Long Contexts Fail](https://www.dbreunig.com/2025/06/22/how-contexts-fail-and-how-to-fix-them.html)（2025.6）、[Drew Breunig - How to Fix Your Context](https://www.dbreunig.com/2025/06/26/how-to-fix-your-context.html)（2025.6）、[Chroma - Context Rot Research](https://research.trychroma.com/context-rot)（2025.7）、[Gemini 2.5 Technical Report](https://storage.googleapis.com/deepmind-media/gemini/gemini_v2_5_report.pdf)

Drew Breunig（Overture Maps Foundation 策略师，O'Reilly《Context Engineering Handbook》作者）系统性地总结了四种上下文失败模式。Chroma 团队的 Kelly Hong 等人则发明了 **"Context Rot"（上下文腐烂）** 这个术语，并用实验数据证明了这种效应的普遍性。

上下文腐烂（Context Rot）就是把大量无关或很少用的信息硬塞进AI的提示词或上下文里，导致AI“脑子”被污染、注意力分散、主任务受干扰、输出越来越差，就像食物放久了会烂掉一样。

| 失败模式                        | 表现                         | 根因      | 真实案例 |
| --------------------------- | -------------------------- | ------- | ---- |
| **Context Poisoning（中毒）**   | 一个幻觉进入上下文，被后续步骤反复引用，错误不断放大 | 缺少验证步骤  | Gemini 玩宝可梦时幻觉污染了"目标"字段，Agent 持续追求不可能的目标 |
| **Context Distraction（分心）** | 上下文太长，模型过度关注历史模式而忽略当前指令    | 没有及时压缩  | Gemini 超过 10 万 Token 后开始机械重复历史动作，不再生成新策略 |
| **Context Confusion（混乱）**   | 工具太多，描述重叠，模型选错工具           | 工具集膨胀   | Llama 3.1 8B 给 46 个工具时完全失败，但只给 19 个工具时成功 |
| **Context Clash（冲突）**       | 上下文中包含矛盾信息，模型推理出错          | 缺少一致性检查 | 微软/Salesforce 研究显示，多轮对话中早期错误答案留在上下文中，o3 准确率从 98.1% 暴跌到 64.1% |

**六种修复策略**——Drew Breunig 在后续文章《How to Fix Your Context》中提出了系统性的解决方案：

| 策略 | 说明 | 对应解决的失败模式 |
| --- | --- | --- |
| **RAG** | 选择性地添加相关信息，而非全量加载 | Confusion、Distraction |
| **Tool Loadout（工具装备）** | 只加载当前任务相关的工具定义（类似游戏中选择装备） | Confusion |
| **Context Quarantine（上下文隔离）** | 将任务隔离到独立的上下文线程中（子 Agent 模式） | Distraction、Clash |
| **Context Pruning（上下文剪枝）** | 用专门的模型移除不相关信息（如 Provence 工具） | Distraction、Confusion |
| **Context Summarization（上下文摘要）** | 将冗长的历史压缩为精炼摘要 | Distraction |
| **Context Offloading（上下文卸载）** | 将信息存储到上下文之外（scratchpad、文件系统） | Distraction、Poisoning |

Drew 特别强调了一个核心洞察：

>上下文不是免费的。每一个 Token 都会影响模型行为。大上下文窗口是强大的能力，但不是信息管理可以偷懒的借口。

**实操预防清单：**
- 每个工具调用后加一步**验证**（类似单元测试），防止 Context Poisoning
- **定期压缩**旧的 tool results（Manus 的 compact/summarize 策略），防止 Context Distraction
- 工具数量控制在 **20 个以内/Agent**（Drew 的研究显示超过 30 个工具时选择准确率开始下降，超过 100 个几乎必然失败），防止 Context Confusion
- 对多轮对话中的旧内容做**一致性检查**，发现矛盾及时清理，防止 Context Clash

### 实践 7：共享上下文而非拆分决策（Cognition 原则）

Cognition（Devin 团队）的联合创始人兼 CPO Walden Yan 在这篇博客中提出了两个核心原则，直接挑战了"多 Agent = 更强"的流行假设：

**原则 1：共享上下文（Share Context）**

>共享上下文，共享完整的 Agent 轨迹，而不只是单条消息。

Walden 用了一个具体的例子：让两个子 Agent 分别构建 Flappy Bird 的背景和小鸟。结果子 Agent 1 做出了像 Super Mario 的背景，子 Agent 2 做了一只和 Flappy Bird 风格完全不同的鸟。**问题不是能力不足，而是两个 Agent 看不到彼此的工作。**

即使你把原始任务传给所有子 Agent，问题依然存在——因为在真实系统中，上下文不只是用户的初始消息，还包括所有中间的工具调用、代码检查、问答历史。这些**隐式决策**（implicit decisions）会在并行工作时产生冲突。

**原则 2：动作携带隐式决策（Actions Carry Implicit Decisions）**

当子 Agent 1 选择了某种视觉风格，子 Agent 2 选择了另一种，这些选择都是在 coding 过程中隐式做出的，没有人显式地共享。**冲突的隐式决策导致了糟糕的集成结果。**

**Cognition 的结论：默认用单线程线性 Agent**
```text
推荐的架构优先级：

1. 首选：单线程线性 Agent（连续的上下文，不存在决策冲突）
   └── 缺点：较慢，但最可靠

2. 次选：引入压缩模型（Context Compressor）
   └── 当上下文溢出时，用 LLM 压缩历史而非拆分 Agent
   └── Cognition 甚至为此微调了专门的小模型

3. 谨慎使用：子 Agent 仅用于"只读查询"
   └── 参考 Claude Code：子 Agent 只回答问题，不写代码
   └── 好处是子 Agent 的调查工作不会污染主 Agent 的上下文
```

Walden 还特别提到了一个观点：**系统对用户应该感觉像是一个单一的 Agent**。即使内部有多个组件，也应该呈现为一个连续的决策者。真正的多 Agent 协作需要的是"能准确判断对方知道什么、不知道什么"的能力——这是当前模型还不具备的。

### 实践 8：为苦涩教训而建（Bitter Lesson-Pilled）

Manus 创始人 Peak Ji 和 Claude Code 创始人 Boris Cherny 都提到了 Richard Sutton 的"苦涩教训"（Bitter Lesson）对 Agent 开发的影响：

![](https://limbo.oss-cn-beijing.aliyuncs.com/wiki/20260414190404031.png)

> **不要在 Agent 的 harness（脚手架）中硬编码太多结构。** 模型在快速进步，今天需要的脚手架可能明天就成了性能瓶颈。

Manus 自 3 月发布以来已经重构了 5 次框架。他们的建议：

- **跨模型强度测试**：换一个更强的模型但性能没有提升，说明你的 harness 在限制 Agent
- **保持架构简单和无偏见**：越是"聪明"的框架设计，越难适应模型进步
- **优先 Context Engineering 而非 Fine-tuning**：CE 让产品迭代从"周级"变成"小时级"，而且不依赖特定模型

---

## 小结

这篇我们深入了三个 Context Engineering 的实战模式，并看了主流框架如何落地：

1. **渐进披露**：像 UI 设计一样分层加载信息——Discovery → Activation → Execution。Claude Code 用文件系统存储 Skills，Manus 把能力分成核心工具、沙箱命令、代码三层。**不是"你可能需要"的全塞进去，而是"你确实需要"时才加载。**
2. **上下文路由**：不同任务路由到不同的上下文配置。Manus 的可恢复压缩（compact vs summarize），文件系统作为无限外部记忆，todo.md 模式让 Agent 自己管理注意力。
3. **工具管理**：面对 MCP 带来的工具爆炸，用 Mask Don't Remove 替代动态增删——保持工具列表稳定以保护 KV Cache，用 `allowed_tools` 或 logit masking 限制可调用范围。一致的命名前缀（`browser_*`、`shell_*`）让分组屏蔽变得简单。
4. **KV Cache 是隐藏基础设施**：稳定前缀、追加式修改、确定性序列化——所有设计都要为缓存命中率服务。缓存命中的 Token 成本只有全价的 10%~50%。
5. **框架落地**：LangChain Middleware、LangGraph 图结构 + State、Deep Agent 内置渐进披露/压缩/隔离——三层抽象对应不同的控制粒度。
6. **生产最佳实践**：把上下文当预算管理（最小高信号集）、保留错误痕迹（Manus）、防止 Few-shot 锁定、设计 Token 高效的工具、警惕四种 Context 失败模式、共享而非拆分上下文（Cognition）、为模型进步留空间（Bitter Lesson）。

> 💡 **预告**：这篇多次提到 KV Cache 和 Prompt Cache，但只讲了"为什么重要"和基本原理。下一篇我们要**深入 Prompt Cache 的实现细节**——OpenAI、Claude、Qwen、豆包四大厂商各自是怎么做的？缓存触发条件、定价策略、最小 Token 阈值有什么不同？如何设计 Prompt 结构来最大化命中率？我们会做一次完整的横向对比。
