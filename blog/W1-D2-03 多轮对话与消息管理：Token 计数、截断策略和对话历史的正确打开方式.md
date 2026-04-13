# 多轮对话与消息管理：Token 计数、截断策略和对话历史的正确打开方式

---

> 摘要：上一篇我们跑通了 API 调用和多轮对话的基本操作，但你一定注意到了——消息列表会越来越长，Token 成本会越来越高。这篇我们专门解决这个问题：怎么数 Token、什么时候截断、对话历史到底该怎么管。这些看似"小事"的管理技巧，就是 Context Engineering 的起点。

## 一、问题从哪里开始的？

上一篇我们实现了一个交互式多轮对话，用起来挺爽的。但跑了十几轮之后，你会发现一个尴尬的事：

```text
第 1 轮发送: [system, user_1]                              → ~50 tokens
第 5 轮发送: [system, user_1, asst_1, ..., user_5]         → ~800 tokens
第 15 轮发送: [system, user_1, asst_1, ..., user_15]       → ~5000 tokens
第 50 轮发送: [system, user_1, asst_1, ..., user_50]       → ~20000 tokens
```

每一轮你都在为**所有的历史消息**付费。更糟的是：

1. **成本线性增长**：第 50 轮的输入 Token 是第 1 轮的几百倍
2. **上下文窗口有上限**：128k tokens 听着多，塞满了就直接报错
3. **信息被稀释**：模型的注意力是有限的，历史越长，关键信息越容易被"淹没"——这就是所谓的 "**Lost in the Middle**" 问题

所以，消息管理不是"锦上添花"，而是**多轮对话能不能正常运行的前提**。

---

## 二、第一步：学会数 Token

管理消息的前提是知道每条消息占多少 Token。如果你连消息列表总共多大都不知道，谈何管理？

1、**tiktoken** OpenAI官方开源BPE分词器，专为GPT系列模型设计；
2、从 API 响应的 usage 字段反查（一般模型厂商都支持 `response.usage`)
3、快速估算 1 token ≈ 0.75 个单词，100 tokens ≈ 75 个词，1 个汉字 ≈ 1.5–2 个 token（中文 token 效率低于英文）
4、一些Tokenizer 可视化工具
5、**使用 litellm 的 token_counter 统一**，强烈推荐，`litellm` 是目前覆盖模型最广的统一 LLM 调用库，内置了针对各主流模型的 token 计数支持，包括 OpenAI、Anthropic、Gemini、Qwen、DeepSeek等

```python
# 使用 litellm 的 token_counter 进行 token 计数
from litellm import token_counter

model = "qwen3.5-flash"
messages = [
    {"role": "system", "content": "你是一个有帮助的助手。"},
    {"role": "user", "content": "帮我用 Python 写一个二分查找算法。"},
]

# 计算 messages 的 token 数
token_count = token_counter(model=model, messages=messages)
print(f"Messages Token 数 : {token_count}")

# 也可以直接计算纯文本的 token 数
text = "帮我用 Python 写一个二分查找算法。"
text_token_count = token_counter(model=model, text=text)
print(f"纯文本 Token 数   : {text_token_count}")
```

---

## 三、截断策略：消息太长了怎么办？

知道怎么数 Token 之后，下一步就是：**超过阈值了怎么处理？**

### 策略一：固定条数截断（最简单）

保留最近 N 条消息，丢弃更早的：

```python
def truncate_by_count(messages: list[dict], max_messages: int = 20) -> list[dict]:
    """保留 system 消息 + 最近 N 条对话。"""
    system_msgs = [m for m in messages if m["role"] == "system"]
    non_system = [m for m in messages if m["role"] != "system"]

    if len(non_system) > max_messages:
        non_system = non_system[-max_messages:]

    return system_msgs + non_system
```

优点：实现简单，一行代码就能搞定。
缺点：**不管消息大小一刀切**

### 策略二：基于 Token 数截断（更精确）

按 Token 预算来决定保留多少消息：

```python
def truncate_by_tokens(
    messages: list[dict],
    max_tokens: int = 4000,
    model: str = "gpt-4o-mini",
) -> list[dict]:
    """基于 Tiktoken Token 预算，从最新消息往回保留，直到超出预算。"""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")

    # System 消息必须保留
    system_msgs = [m for m in messages if m["role"] == "system"]
    non_system = [m for m in messages if m["role"] != "system"]

    # 先算 system 消息占多少
    system_tokens = sum(len(encoding.encode(m["content"])) + 3 for m in system_msgs)
    remaining_budget = max_tokens - system_tokens - 3  # 减去回复前缀

    # 从最新的消息往回加，直到预算用完
    kept = []
    for msg in reversed(non_system):
        msg_tokens = len(encoding.encode(msg["content"])) + 3
        if remaining_budget - msg_tokens < 0:
            break
        kept.append(msg)
        remaining_budget -= msg_tokens

    kept.reverse()
    return system_msgs + kept
```

**Token 计算公式** `len(encoding.encode(content)) + 3` 每个消息的 Token 数通常包含内容本身及固定开销（角色标识符等，此处简化处理为 $+3$）

这个策略更精细——它保证了你发给模型的消息总量不会超过预设的 Token 预算。

### 策略三：滑动窗口 + 摘要（最优雅）

前两种策略的问题是：被丢掉的旧消息里可能有重要信息。滑动窗口 + 摘要的思路是：
1. 保留最近 N 轮的**完整消息**
2. 更早的消息不直接丢弃，而是用 LLM **压缩成一段摘要**
3. 摘要放在 system 消息之后、最近消息之前

这个策略的好处是**既控制了 Token 数量，又保留了历史上下文的关键信息**。代价是每次压缩需要一次额外的 API 调用。
```python
def summarize_messages(messages: list[dict], model: str) -> str:
    conversation_text = "\n".join(
        f"{m['role']}: {m['content']}" for m in messages)

    response = client.chat.completions.create(model=model,
        messages=[
            {"role": "system", "content": "请将以下对话压缩成简洁的摘要，保留关键信息和决策..."},
            {"role": "user", "content": conversation_text}
        ],
        temperature=0,
        max_tokens=600,
    )
    return response.choices[0].message.content


def sliding_window_with_summary(messages: list[dict],
    recent_count: int = 30,
    model: str = "gpt-4o-mini",
) -> list[dict]:
    system_msgs = [m for m in messages if m["role"] == "system"]
    non_system = [m for m in messages if m["role"] != "system"]

    if len(non_system) <= recent_count:
        return messages  # 不需要压缩

    # 旧消息 → 压缩成摘要
    old_messages = non_system[:-recent_count]
    recent_messages = non_system[-recent_count:]

    summary = summarize_messages(old_messages, model)
    # 摘要作为一条 system 消息插入
    summary_msg = {"role": "system","content": f"[对话摘要]\n{summary}"}
    return system_msgs + [summary_msg] + recent_messages
```



### 三种策略对比

| 策略         | 实现复杂度 | 信息保留 | 成本控制 | 适用场景       |
| ---------- | ----- | ---- | ---- | ---------- |
| 固定条数截断     | ⭐     | 低    | 粗略   | 快速原型、简单场景  |
| Token 预算截断 | ⭐⭐    | 低    | 精确   | 需要精确控制成本   |
| 滑动窗口 + 摘要  | ⭐⭐⭐   | 高    | 精确   | 长对话、信息不可丢失 |
实际开发中，我的建议是：**用litellm来统一统计token, 先按token截断跑起来，遇到问题了再升级到更复杂的策略**。过度设计在早期是最大的敌人。

---

## 四、"Lost in the Middle"：为什么消息顺序很重要

前面提到过 "Lost in the Middle"，这里展开说一下。

2023 年 Nelson Liu 等人的论文发现：当输入很长时，模型对**开头**和**结尾**的信息关注度最高，而**中间**的信息最容易被忽略。

```text
注意力分布（示意）:

高 ▕████                                    ████▏
   ▕███                                      ███▏
   ▕██                                        ██▏
   ▕█              ........                    █▏
低 ▕                ........                     ▏
   └───────────────────────────────────────────┘
   开头            中间                      结尾
```

这意味着什么？

1. **System Prompt 放在最前面是对的**——它在注意力最高的位置
2. **最新的对话放在最后面也是对的**——结尾的注意力同样高
3. **中间的历史消息效果最差**——如果有 30 轮对话，第 10-20 轮的内容可能被模型"忽略"

所以滑动窗口 + 摘要策略是合理的：与其让模型从一大堆历史消息中"找"关键信息，不如直接把关键信息压缩成摘要放在前面。

---

## 五、真正的 Agent 系统怎么做消息管理？来自 LangChain、Manus 和 Anthropic 的最佳实践

前面我们从零实现了消息管理的各种策略，那生产级的 Agent 系统到底是怎么做的？

### 1. LangChain / LangGraph：中间件模式，消息管理系统化

LangChain 在消息管理上的核心思路是：**把截断和摘要逻辑抽成中间件（Middleware），在模型调用前自动执行**。这样你的业务代码不需要关心消息管理，它在"底层"自动帮你处理了。

LangChain 提供了三种内置策略：

| 策略 | 做法 | 适用场景 |
|------|------|---------|
| `trim_messages` | 按 Token 数截断，保留最近的 N 条 | 简单对话，快速原型 |
| `RemoveMessage` | 精确删除特定消息（如过期的工具调用结果） | 需要细粒度控制 |
| `SummarizationMiddleware` | Token 超过阈值时自动用 LLM 压缩旧消息 | 长对话，不想丢信息 |

其中 `SummarizationMiddleware` 最值得关注：

```python
from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware
from langgraph.checkpoint.memory import InMemorySaver

agent = create_agent(
    model="qwen3.5-plus",
    tools=[],
    middleware=[
        SummarizationMiddleware(
            model="qwen3.5-flash",        # 用小模型做摘要
            trigger=("tokens", 12000),    # Token 超过 12000 时触发
            keep=("messages", 20),        # 保留最近 20 条完整消息
        )
    ],
    checkpointer=InMemorySaver(),
)
```

它的工作原理是：当消息列表的 Token 数超过 `trigger` 阈值时，自动把旧消息压缩成摘要，保留最近 `keep` 条消息不动。**这和我们前面手写的"滑动窗口 + 摘要"是完全一样的思路**——只是框架帮你做了封装。

### 2. Manus：文件系统即记忆，围绕 KV-Cache 设计一切

Manus 是这样：
```
上下文总量 = 模型上限（如 200K）
Pre-Rot Threshold = 上下文总量 × 70%（约 128K–140K）

触发条件：当前 token 数 >= Pre-Rot Threshold
压缩策略优先级：
  1. 可恢复压缩（删大内容，保留路径/URL）
  2. 摘要压缩（LLM 摘要早期历史，保留最近完整消息）
  3. 外部记忆（大输出写文件，只传路径给模型）
```
Manus 提出了 **"Pre-Rot Threshold"（预腐化阈值）** 的概念，**不要等到上下文窗口满了再压缩，而是在达到约 70% 时就主动介入。**

Manus 的消息管理有三个核心策略：

**策略一：Compact（压缩旧结果，保留引用）**

Manus 不会简单地丢弃旧的工具调用结果。它会把完整结果存到文件系统，然后把上下文里的旧结果替换为**紧凑引用**（比如只保留文件路径）：

```text
# 压缩前（完整结果在上下文里，占 2000 tokens）
Tool Result: [完整的网页内容...]

# 压缩后（只保留引用，占 50 tokens）
Tool Result: [已保存到 /tmp/search_result_1.md，可通过 read_file 查看]
```

这样旧信息没有真的丢失——Agent 需要时可以通过文件系统重新读取。这是一种**可恢复的压缩**，比粗暴截断高明得多。

**策略二：用 todo.md 操纵注意力**

如果你用过 Manus，你会发现它在处理复杂任务时总是会创建一个 `todo.md`，并且每完成一步就更新它。这不是花架子——**这是一个精心设计的注意力操纵机制**。

Agent 在长循环中最大的敌人是"迷失方向"。通过不断在上下文末尾重写 todo 列表，Manus 把全局目标推到了模型**注意力最强的位置**（还记得 "Lost in the Middle" 吗？结尾的注意力最高）。它本质上是在用自然语言**引导自己的注意力**。

**策略三：保持上下文 Append-Only**

为了最大化 KV-Cache 命中率，Manus 的上下文设计是**只追加不修改**的。任何对旧内容的修改都会导致缓存从修改点之后全部失效。这也是为什么他们不直接删除/替换旧的工具定义，而是用 logits masking 来"隐藏"不需要的工具。

> 一个常见的坑：在 System Prompt 开头放一个精确到秒的时间戳。看起来很贴心，但每次请求时间戳都不同，会导致整个 KV-Cache 失效。Manus 特别提醒要**保持 Prompt 前缀稳定**。


### 3. Claude：Compaction + 结构化笔记 + Sub-Agent 三板斧

Anthropic 在他们的 [Effective Context Engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) 文章中系统总结了 Agent 的上下文管理最佳实践，核心思路是三个层次递进：

**层次一：Compaction（上下文压实）**

当对话接近上下文窗口上限时，用 LLM 对整个消息历史做一次高保真摘要，然后用摘要开始一个新的上下文窗口继续工作。Claude Code 就是这么做的——它在压缩时会保留架构决策、未解决的 bug、实现细节，同时丢弃冗余的工具输出。压缩后还会附上最近 5 个访问过的文件内容，确保连续性。

一个最简单的 Compaction 手段是**清理工具调用结果**——模型已经基于工具结果做过决策了，深埋在历史里的原始结果还有什么用？直接清掉就好。

**层次二：结构化笔记（Agentic Memory）**

Agent 在工作过程中定期把关键信息写到外部文件（比如 `NOTES.md`）。这些笔记存在上下文窗口之外，需要时再拉回来。这和 Manus 的 `todo.md` 异曲同工。

**层次三：Sub-Agent 架构（上下文隔离）**

与其让一个 Agent 在巨大的上下文里维护所有状态，不如把任务拆给多个 Sub-Agent，每个 Sub-Agent 有自己干净的上下文窗口。主 Agent 只做高层规划，Sub-Agent 做深度的技术工作。每个 Sub-Agent 可能消耗几万个 Token 来深入探索，但最终只返回 1000-2000 Token 的精炼摘要。

Anthropic 的建议是：
- **Compaction** 适合需要大量来回交互的任务（保持对话流）
- **结构化笔记** 适合有清晰里程碑的迭代开发
- **Sub-Agent** 适合需要并行探索的复杂研究和分析

### 三家对比：异曲同工

| 维度 | LangChain | Manus | Anthropic/Claude |
|------|-----------|-------|-----------------|
| 核心思路 | 中间件自动化 | 文件系统 + KV-Cache 优化 | 压实 + 笔记 + Sub-Agent |
| 截断策略 | `trim_messages` / `SummarizationMiddleware` | Compact（压缩旧结果为引用） | Compaction（高保真摘要） |
| 长期记忆 | Checkpointer 持久化到 DB | 文件系统 + `todo.md` | 结构化笔记 `NOTES.md` |
| 工具结果处理 | `RemoveMessage` 精确删除 | 存文件 → 上下文只留路径引用 | 清理旧工具调用结果 |
| 多会话管理 | `thread_id` 线程隔离 | Sub-Agent 独立上下文 | Sub-Agent 架构 |
| 设计哲学 | 框架化、可组合 | 围绕缓存和性能极致优化 | 简单实用、让模型发挥 |

三家做法的底层逻辑完全一致：**上下文窗口是有限的稀缺资源，必须把最高信号的信息放在模型能看到的位置，把低信号的信息要么压缩、要么存到外部按需取用。**

你现在不需要马上实现这些复杂策略。但理解这些方向，能帮你在后面做 Agent 开发时少走弯路——知道"终点在哪"，才不会在起点过度设计或者方向跑偏。

---

## 六、小结

这篇我们解决了多轮对话的"后勤问题"：

1. **Token 计数**：用 tiktoken 算消息列表大小，是一切管理的前提
2. **截断策略**：三种方案（固定条数 / Token 预算 / 滑动窗口+摘要），按需选择
3. **消息管理器**：封装一个 `MessageManager`，让截断和持久化自动化
4. **"Lost in the Middle"**：理解模型注意力分布，解释了为什么消息顺序和压缩都很重要
5. **生产级最佳实践**：LangChain 的中间件自动化、Manus 的文件系统记忆和 KV-Cache 优化、Anthropic 的 Compaction + 笔记 + Sub-Agent 三板斧

关键心智模型：**消息列表不是"追加就完了"的数组，它是一个需要精心管理的有限资源**。你对它的管理水平，直接决定了 Agent 的成本、质量和稳定性。

> 💡 **预告**：消息管理是 Context Engineering 最朴素的一个切面。下一篇我们正式进入 **Context Engineering** 的完整世界——从"写好一句 Prompt"升级到"设计整个信息系统"，理解为什么 Andrej Karpathy 说"你是负责加载正确信息的操作系统"。
