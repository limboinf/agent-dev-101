# Prompt Cache 全解析：原理、厂商对比与最佳实践

---

> 摘要：上一篇我们反复提到 KV Cache 和 Prompt Cache——缓存命中率是 Agent 成本和延迟的头号优化指标。但 Prompt Cache 到底是怎么工作的？OpenAI、Claude、国产模型的缓存策略各有不同，搞混了会踩坑。这篇我们从 Transformer 的注意力机制出发，搞懂 KV Cache 的底层原理，然后逐一拆解各家厂商的缓存机制，最后总结最大化命中率的实践技巧。

## 一、KV Cache 的底层原理

### 从 Transformer 注意力说起

要理解 Prompt Cache，必须先知道 KV Cache。我们用最简短的方式过一遍。
Transformer 模型处理输入时，每个 Token 会经过注意力计算。对于输入序列中的每个 Token，模型会计算三个向量：

```text
输入 Token → 线性变换 → Q (Query)    ← "我在找什么"
                      → K (Key)      ← "我是什么"
                      → V (Value)    ← "我的内容"

注意力分数 = softmax(Q × K^T / √d) × V
```

- **Query（Q）**：当前 Token 要"查询"的信息
- **Key（K）**：每个位置的"索引"
- **Value（V）**：每个位置的"内容"

在生成阶段（逐 Token 输出），每生成一个新 Token，都需要和之前**所有 Token 的 K 和 V** 做注意力计算。如果不缓存，每生成一个 Token 就要重新算一遍所有输入 Token 的 K 和 V——这就是巨大的浪费。

#### KV Cache：缓存 Key 和 Value 张量
![](https://limbo.oss-cn-beijing.aliyuncs.com/wiki/20260415143757660.png)

**KV Cache 的核心思想：把已经计算过的 Key 和 Value 张量存起来，后续 Token 直接复用。**

```text
┌──────────────────────────────────────────────────────────┐
│  Prefill 阶段（处理输入 prompt）                           │
│                                                          │
│  Token_1 → [K₁, V₁]  ─┐                                 │
│  Token_2 → [K₂, V₂]  ─┤                                 │
│  Token_3 → [K₃, V₃]  ─┼──→  KV Cache = [(K₁,V₁),       │
│  Token_4 → [K₄, V₄]  ─┤         (K₂,V₂), (K₃,V₃),     │
│  Token_5 → [K₅, V₅]  ─┘         (K₄,V₄), (K₅,V₅)]     │
│                                                          │
├──────────────────────────────────────────────────────────┤
│  Decode 阶段（逐 Token 生成输出）                          │
│                                                          │
│  生成 Token_6:                                            │
│    Q₆ × [K₁..K₅]^T → 注意力分数 → × [V₁..V₅] → 输出     │
│    然后把 K₆, V₆ 追加到 Cache                             │
│                                                          │
│  生成 Token_7:                                            │
│    Q₇ × [K₁..K₆]^T → 注意力分数 → × [V₁..V₆] → 输出     │
│    复用之前所有的 K, V！只需要新算 K₇, V₇                  │
└──────────────────────────────────────────────────────────┘
```

这是**单次请求内**的 KV Cache。但 Prompt Cache 更进一步——它把 KV Cache **跨请求复用**。

### Prompt Cache：跨请求的 KV Cache 复用

**Prompt Cache 的核心机制：如果两个请求有相同的前缀（Prefix），第二个请求可以直接复用第一个请求的 KV Cache，跳过 Prefill 阶段。**

![](https://limbo.oss-cn-beijing.aliyuncs.com/wiki/20260415144137011.png)

```text
请求 A:
┌────────────────────────────────────────────────────────┐
│  [System Prompt] [Tool Defs] [History] [Query A]       │
│  ├──── 公共前缀 ──────────────┤ ├─ 不同 ─┤             │
│                                                        │
│  Prefill: 计算所有 Token 的 KV    → 耗时 800ms          │
│  存入缓存: prefix_hash → KV tensors                    │
└────────────────────────────────────────────────────────┘

请求 B（紧随其后）:
┌────────────────────────────────────────────────────────┐
│  [System Prompt] [Tool Defs] [History] [Query B]       │
│  ├──── 缓存命中！──────────────┤ ├─ 不同 ─┤            │
│                                                        │
│  Prefill: 只需计算 [Query B] 的 KV  → 耗时 50ms        │
│  前缀部分直接从缓存读取！                                 │
└────────────────────────────────────────────────────────┘
```
**关键约束：前缀匹配必须是精确的、逐 Token 的。** 哪怕中间改了一个 Token，从那个位置开始的所有缓存都会失效：

```text
请求 1: "你是一个AI助手。请帮我..." → [K₁..K₁₀₀] 全部缓存
请求 2: "你是一个AI助理。请帮我..." → "助手"→"助理" 从第 8 个 Token 开始不同
                                      → 只有 [K₁..K₇] 命中，K₈ 开始重算
```

**一个字的差异就能毁掉缓存。** 这就是为什么上一篇强调"稳定前缀"如此重要。

### 缓存带来的收益

| 指标                   | 无缓存  | 有缓存       | 改善   |
| -------------------- | ---- | --------- | ---- |
| **TTFT（首 Token 时间）** | 100% | 降低 50-85% | 响应更快 |
| **输入 Token 成本**      | 100% | 降至 10-50% | 大幅省钱 |

---

## 二、OpenAI 的 Prompt Cache

OpenAI 的 Prompt Cache 是所有厂商中**最省心的**——完全自动，不需要修改任何代码。

```python
# 不需要任何特殊标记或配置！只要请求有相同前缀，自动触发缓存
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": "你是一个..."},    # 稳定前缀
        {"role": "user", "content": "请审查以下代码:..."} # 变化部分
    ]
)

# 查看缓存命中情况
usage = response.usage
print(f"缓存命中 Token: {usage.prompt_tokens_details.cached_tokens}")
print(f"总输入 Token: {usage.prompt_tokens}")
```

### 关键参数

| 参数                 | 值                                         |
| -------------------- | ------------------------------------------ |
| **最小缓存长度**      | 1024 tokens                                |
| **缓存粒度**          | 128 tokens（每 128 token 为一个缓存单元）    |
| **缓存 TTL**          | 5-10 分钟（内存缓存），最长可达 24 小时       |
| **价格折扣**          | gpt-4o 50% 折扣；更新模型高达 90% 折扣       |
| **写入成本**          | 无额外费用                                   |
| **触发方式**          | 全自动                                      |

### prompt_cache_key：提升命中率的利器

OpenAI 有一个不太被注意的参数 `prompt_cache_key`。默认情况下，缓存路由基于请求前缀的哈希——但高并发时，不同用户的请求可能被路由到不同的服务器节点，导致缓存命中率不高。

```python
# 使用 prompt_cache_key 确保同一用户/会话的请求路由到同一缓存
response = client.responses.create(
    model="gpt-5",
    prompt_cache_key="user_12345_session_abc",  # 相同 key → 路由到同一缓存
    input=[
        {"role": "system", "content": long_system_prompt},
        {"role": "user", "content": current_query},
    ]
)
```

> 根据 OpenAI 的数据，使用 `prompt_cache_key` 可以将缓存命中率从 **60% 提升到 87%** 但是不同模型厂商可能兼容性不一样，还得看官方文档。

### Responses API vs Chat Completions API

OpenAI 推荐使用较新的 Responses API，因为它的缓存利用率比 Chat Completions API 高 **40-80%**。原因是 Responses API 在内部对消息的序列化方式更加缓存友好。

### allowed_tools 保护缓存

上一篇提到的 `allowed_tools` 技巧在这里发挥关键作用：

```python
# tools 数组始终不变 → 前缀稳定 → 缓存命中
tools = [tool_a, tool_b, tool_c, tool_d, tool_e]

# 第一步：只允许搜索工具
resp1 = client.responses.create(
    model="qwen3.5-flash",
    tools=tools,                              # 不变！
    allowed_tools=["browser_search"],          # 限制可调用范围
    input=messages,
)

# 第二步：只允许文件工具
resp2 = client.responses.create(
    model="qwen3.5-flash",
    tools=tools,                              # 还是不变！缓存命中
    allowed_tools=["file_read", "file_write"], # 不同的限制
    input=messages,
)
```

---

## 三、Claude（Anthropic）的 Prompt Cache

### 核心特点：自动模式 + 显式断点，写入有成本

Claude 的缓存机制比 OpenAI 更灵活，但也更复杂——因为**写入缓存要额外付费**。

### 核心参数：`cache_control` + `{"type": "ephemeral"}`

Claude 的 Prompt Cache 只有一个关键参数：**`cache_control: {"type": "ephemeral"}`**。`ephemeral` 是目前唯一支持的缓存类型，表示缓存是临时的，会自动过期。这个参数有两种用法：

**用法一：自动缓存（推荐）**

在请求体**顶层**加一个 `cache_control` 字段，系统自动把断点设在最后一个可缓存的 block 上，并随对话增长自动前移。多轮对话场景直接用这个就够了：

```python
import anthropic
client = anthropic.Anthropic()

response = client.messages.create(
    model="claude-opus-4-6",
    max_tokens=1024,
    cache_control={"type": "ephemeral"},       # 顶层声明，自动缓存
    system="你是一个专业的代码审查助手...",
    messages=[
        {"role": "user", "content": "我叫张三，我在做 ML 项目"},
        {"role": "assistant", "content": "你好张三！有什么可以帮你的？"},
        {"role": "user", "content": "我刚才说我在做什么？"}
    ]
)

# 查看缓存情况
print(f"缓存写入 Token: {response.usage.cache_creation_input_tokens}")
print(f"缓存读取 Token: {response.usage.cache_read_input_tokens}")
```

> 注意：不再需要 `anthropic-beta` 请求头，Prompt Cache 已经是 GA 功能。

**用法二：显式断点（精细控制）**

在具体的 content block 上放 `cache_control`，最多 **4 个断点**。适合需要分段缓存的场景（如 tools 定义和 system prompt 独立缓存）：

```python
response = client.messages.create(
    model="claude-opus-4-6",
    max_tokens=1024,
    system=[{
        "type": "text",
        "text": long_system_prompt,
        "cache_control": {"type": "ephemeral"}  # 断点 1
    }],
    tools=[
        # ... 工具定义 ...
        {
            "name": "last_tool",
            "description": "...",
            "input_schema": {...},
            "cache_control": {"type": "ephemeral"}  # 断点 2（放在最后一个 tool 上）
        }
    ],
    messages=[
        {"role": "user", "content": "请根据文档回答..."}
    ]
)
```

两种用法可以**混合使用**——显式断点锁住 system 和 tools，自动缓存处理对话历史，但总共不能超过 4 个断点。

### 关键参数

| 参数                 | 值                                              |
| -------------------- | ----------------------------------------------- |
| **支持模型**          | 所有在役 Claude 模型                               |
| **最小缓存长度**      | 1024 tokens（模型相关）                            |
| **缓存断点上限**      | 4 个（自动缓存占 1 个名额）                        |
| **写入成本**          | 1.25x 基础价格（5 分钟 TTL）或 2x（1 小时 TTL）   |
| **读取成本**          | 0.1x 基础价格                                     |
| **默认 TTL**          | 5 分钟，每次命中刷新；可选 1 小时（`"ttl": "1h"`） |
| **可缓存内容**        | system、messages、tools、images                   |

---

## 四、国产大模型的 Prompt Cache

### 总体情况：大部分都支持隐式缓存

好消息是，**大部分国产模型都已支持隐式（自动）缓存**。和 OpenAI 一样，只要你的请求有相同前缀，系统自动帮你缓存和复用，不需要改任何代码。

### Responses API：前缀缓存 + Session 缓存

以豆包（火山方舟）为例，它的 Responses API 支持两种缓存方式。核心思路很简单：**把重复发送的内容缓存起来，下次请求直接复用，命中缓存的输入 Token 有折扣优惠。** 适合多轮对话、工具调用、角色扮演等需要多次传入相同内容的场景。

**前缀缓存**——先把固定内容（如 system prompt、长文档）缓存，后续多个不同问题都能复用：

```python
from volcenginesdkarkruntime import Ark

client = Ark(base_url='https://ark.cn-beijing.volces.com/api/v3')

# 第一步：创建前缀缓存（把长文档缓存起来）
response = client.responses.create(
    model="doubao-seed-2-0-lite-260215",
    input=[{"role": "system", "content": "你是一名文学分析助手...（很长的小说内容）"}],
    caching={"type": "enabled", "prefix": True},   # 开启前缀缓存
)

# 第二步：后续请求通过 previous_response_id 复用缓存
second = client.responses.create(
    model="doubao-seed-2-0-lite-260215",
    previous_response_id=response.id,              # 引用缓存！
    input=[{"role": "user", "content": "用 5 个要点总结核心情节。"}],
)

# 第三步：换个问题，还是复用同一份缓存
third = client.responses.create(
    model="doubao-seed-2-0-lite-260215",
    previous_response_id=response.id,              # 同一个缓存 ID
    input=[{"role": "user", "content": "分析反讽手法的运用。"}],
)
```

**Session 缓存**——自动缓存多轮对话的历史上下文，每轮对话通过 `previous_response_id` 串起来，越往后缓存命中越多：

```python
# 第一轮：正常对话
resp1 = client.responses.create(
    model="doubao-seed-2-0-lite-260215",
    input=[
        {"role": "system", "content": "你是文学助手...（长文本）"},
        {"role": "user", "content": "总结核心情节。"}
    ],
    caching={"type": "enabled"},  # 开启 Session 缓存
)

# 第二轮：引用第一轮，历史上下文自动从缓存读取
resp2 = client.responses.create(
    model="doubao-seed-2-0-lite-260215",
    previous_response_id=resp1.id,
    input=[{"role": "user", "content": "以 Della 的视角写一篇日记。"}],
    caching={"type": "enabled"},  # 继续缓存
)

# 第三轮：引用第二轮，前面所有历史都命中缓存
resp3 = client.responses.create(
    model="doubao-seed-2-0-lite-260215",
    previous_response_id=resp2.id,
    input=[{"role": "user", "content": "Jim 读到这篇日记会怎么想？"}],
    caching={"type": "enabled"},
)

# usage 中 cached_tokens 会越来越大，成本越来越低
print(resp3.usage.model_dump_json())
```

> 在长文本场景中，缓存命中后输入费用可降低约 **80%**。对话轮次越多、上下文越长，节省越明显。

### 前缀缓存 vs Session 缓存的区别

简单理解：

- **前缀缓存**：一份固定内容，多个独立问题各自复用。像"一本参考书放在桌上，大家都来查"。
- **Session 缓存**：多轮对话串联，每轮自动把上下文续上。像"一场持续的讨论，不用每次都从头说起"。

---

## 五、厂商横向对比

|            | OpenAI              | Claude            | 国产模型（Qwen/豆包等）           |
| ---------- | ------------------- | ----------------- | ------------------------ |
| **触发方式**   | 全自动                 | 自动 + 显式断点（最多 4 个） | 隐式自动 + Responses API 缓存  |
| **写入成本**   | 免费                  | 1.25x～2x（按 TTL）   | 免费（隐式）                   |
| **读取折扣**   | 50%～90%（按模型）        | 90%               | ～80%                     |
| **默认 TTL** | 5-10min（最长 24h）     | 5min（可选 1h）       | 系统管理 / 自定义               |
| **代码改动**   | 零改动                 | 少量（cache_control） | 隐式零改动 / Responses API 少量 |
| **独特能力**   | prompt_cache_key 路由 | 多断点精控，读取仅 0.1x    | 前缀缓存 + Session 缓存        |
| **最佳场景**   | 快速上手、高并发 Agent      | 大文档分析、精细成本控制      | 多轮对话、工具调用、长会话            |

---

## 六、最大化缓存命中率的最佳实践

不管你用哪家的 API，以下实践都适用：

### 1. 稳定前缀 + 动态后缀

```python
# ✅ 正确的消息结构
messages = [
    # ──── 稳定前缀（被缓存）────
    {"role": "system", "content": system_prompt},    # 不变
    # tools 定义                                      # 不变
    # few-shot 示例                                   # 不变
    
    # ──── 动态后缀（每次不同）────
    {"role": "user", "content": "用户的新问题"},       # 变化
]
```

### 2. 追加式设计（Append-Only）

```python
# ❌ 修改历史消息 → 破坏缓存
messages[3]["content"] = "更新后的内容"

# ✅ 只在末尾追加 → 保护缓存
messages.append({"role": "assistant", "content": response})
messages.append({"role": "user", "content": new_query})
```

### 3. 保持工具定义不变

```python
# ❌ 每次请求动态构建工具列表
tools = get_relevant_tools(user_query)  # 每次不同 → 缓存失效

# ✅ 工具列表固定，用 allowed_tools 限制范围
tools = ALL_TOOLS  # 永远一样
allowed_tools = get_relevant_tool_names(user_query)  # 只改这个
```

### 4. 合理设置缓存断点（Claude/Qwen 显式模式）

```python
# 把断点设在"稳定内容"和"动态内容"的交界处
system_content = {
    "type": "text",
    "text": system_prompt,
    "cache_control": {"type": "ephemeral"}  # 断点 1: 系统提示结束
}

last_tool = {
    "name": "final_tool",
    "description": "...",
    "cache_control": {"type": "ephemeral"}  # 断点 2: 工具定义结束
}
# 断点之后的内容（对话历史、用户输入）每次不同，不被缓存
```

### 5. 监控缓存命中率

```python
def log_cache_metrics(response):
    """记录缓存指标，持续优化"""
    usage = response.usage
    total = usage.prompt_tokens
    
    # OpenAI
    cached = getattr(usage, "prompt_tokens_details", None)
    if cached:
        hit_rate = cached.cached_tokens / total * 100
        print(f"缓存命中率: {hit_rate:.1f}%")
        
    # 如果命中率 < 50%，需要检查：
    # 1. 前缀是否足够稳定？
    # 2. 工具定义是否在变动？
    # 3. 是否有时间戳等动态内容污染前缀？
```

---

## 七、常见误解澄清

在学习 Prompt Cache 的过程中，有几个容易搞混的概念：

> **误解一：Prompt Cache = 上下文压缩**
>
> 不是。缓存解决的是"重复计算"的问题——**同样的 Token 不用算两遍**。压缩解决的是"窗口容量"的问题——**用更少的 Token 表达同样的信息**。两者互补，但完全不同。

> **误解二：上下文窗口够大就不需要缓存**
>
> 即使窗口有 1M tokens，不用缓存意味着每次请求都要对所有输入 Token 做一遍 Prefill 计算。一次 200k tokens 的 Prefill 可能需要 10+ 秒——用户体验极差，成本也高。

> **误解三：缓存会影响模型输出质量**
>
> 不会。缓存复用的是 KV 张量——这些是数学计算的中间结果，和从头算的结果**完全一致**。缓存不是"近似"，而是"精确复用"。

> **误解四：KV Cache 存的是原始文本**
>
> 不是。KV Cache 存的是经过模型线性变换后的 Key 和 Value **张量（多维数组）**——是浮点数矩阵，不是字符串。所以你不能"读取"缓存内容来窥探别人的 prompt。

---

## 小结

这篇我们从底层原理到实践应用，全面拆解了 Prompt Cache：

1. **KV Cache 原理**：Transformer 注意力计算产生 Key/Value 张量，缓存它们可以跳过重复计算。Prompt Cache 是跨请求的 KV Cache 复用，要求**精确的前缀匹配**。
2. **厂商对比**：
   - **OpenAI**：全自动、零配置、免费写入，`prompt_cache_key` 提升路由命中率
   - **Claude**：`cache_control: {"type": "ephemeral"}` 一个参数搞定，自动 + 显式断点，读取仅 0.1x
   - **国产模型**：大部分支持隐式缓存开箱即用；Responses API 提供前缀缓存 + Session 缓存，适合多轮对话和工具调用
3. **最大化命中率**：稳定前缀、追加式修改、固定工具列表 + allowed_tools、合理设置断点、持续监控命中率。
4. **缓存 ≠ 压缩**，窗口大 ≠ 不需要缓存，缓存不影响输出质量，KV 是张量不是文本。

> 💡 **预告**：到这里，我们完成了 Context Engineering 的全部内容——从定义、四大支柱，到核心模式、实战模板，再到 Prompt Cache 的底层原理和厂商对比。下一篇我们进入一个全新的主题：**Agent 概念入门**。我们会回答一个根本问题——什么是 Agent？它和普通的 LLM 应用有什么本质区别？从 ReAct 循环到工具调用，从"对话系统"到"能自主行动的智能体"，我们正式踏入 Agent 开发的核心领域。
