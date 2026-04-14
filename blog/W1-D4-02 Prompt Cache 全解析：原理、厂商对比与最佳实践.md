# Prompt Cache 全解析：原理、厂商对比与最佳实践

---

> 摘要：上一篇我们反复提到 KV Cache 和 Prompt Cache——缓存命中率是 Agent 成本和延迟的头号优化指标。但 Prompt Cache 到底是怎么工作的？OpenAI、Claude、Qwen、豆包四家厂商的缓存策略差异巨大，搞混了会踩坑。这篇我们从 Transformer 的注意力机制出发，搞懂 KV Cache 的底层原理，然后逐一拆解四大厂商的缓存机制，最后总结最大化命中率的实践技巧。

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

### KV Cache：缓存 Key 和 Value 张量

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

Prompt Cache 的收益体现在两个方面：

| 指标              | 无缓存   | 有缓存          | 改善           |
| ----------------- | -------- | --------------- | -------------- |
| **TTFT（首 Token 时间）** | 100%     | 降低 50-85%     | 响应更快        |
| **输入 Token 成本**       | 100%     | 降至 10-50%     | 大幅省钱        |

对于一个每天处理 10 万次 Agent 请求、每次请求有 4000 tokens 公共前缀的系统来说，Prompt Cache 可以节省**数千美元/月**的成本。

---

## 二、OpenAI 的 Prompt Cache

### 核心特点：全自动、零配置、零额外费用

OpenAI 的 Prompt Cache 是所有厂商中**最省心的**——完全自动，不需要修改任何代码。

```python
from openai import OpenAI
client = OpenAI()

# 不需要任何特殊标记或配置！
# 只要请求有相同前缀，自动触发缓存
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": "你是一个专业的代码审查助手..."},  # 稳定前缀
        {"role": "user", "content": "请审查以下代码:\n..."}              # 变化部分
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
    model="gpt-4.1",
    prompt_cache_key="user_12345_session_abc",  # 相同 key → 路由到同一缓存
    input=[
        {"role": "system", "content": long_system_prompt},
        {"role": "user", "content": current_query},
    ]
)
```

> 根据 OpenAI 的数据，使用 `prompt_cache_key` 可以将缓存命中率从 **60% 提升到 87%**。

### Responses API vs Chat Completions API

OpenAI 推荐使用较新的 Responses API，因为它的缓存利用率比 Chat Completions API 高 **40-80%**。原因是 Responses API 在内部对消息的序列化方式更加缓存友好。

### allowed_tools 保护缓存

上一篇提到的 `allowed_tools` 技巧在这里发挥关键作用：

```python
# tools 数组始终不变 → 前缀稳定 → 缓存命中
tools = [tool_a, tool_b, tool_c, tool_d, tool_e]

# 第一步：只允许搜索工具
resp1 = client.responses.create(
    model="gpt-4.1",
    tools=tools,                              # 不变！
    allowed_tools=["browser_search"],          # 限制可调用范围
    input=messages,
)

# 第二步：只允许文件工具
resp2 = client.responses.create(
    model="gpt-4.1",
    tools=tools,                              # 还是不变！缓存命中
    allowed_tools=["file_read", "file_write"], # 不同的限制
    input=messages,
)
```

---

## 三、Claude（Anthropic）的 Prompt Cache

### 核心特点：自动模式 + 显式断点，写入有成本

Claude 的缓存机制比 OpenAI 更灵活，但也更复杂——因为**写入缓存要额外付费**。

### 两种模式

**模式一：自动缓存（推荐入门）**

只需在 API 请求头中加入一个参数，Anthropic 会自动决定缓存哪些内容：

```python
import anthropic
client = anthropic.Anthropic()

response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    extra_headers={
        "anthropic-beta": "prompt-caching-2024-07-31"  # 启用缓存
    },
    system=[{
        "type": "text",
        "text": "你是一个专业的代码审查助手...",
        "cache_control": {"type": "ephemeral"}  # 标记为可缓存
    }],
    messages=[
        {"role": "user", "content": "请审查以下代码..."}
    ]
)

# 查看缓存情况
print(f"缓存写入 Token: {response.usage.cache_creation_input_tokens}")
print(f"缓存读取 Token: {response.usage.cache_read_input_tokens}")
```

**模式二：显式断点（精细控制）**

你可以手动设置最多 **4 个缓存断点**，精确控制哪些部分被缓存：

```python
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    system=[{
        "type": "text",
        "text": long_system_prompt,
        "cache_control": {"type": "ephemeral"}  # 断点 1: 系统提示
    }],
    tools=[
        # ... 工具定义 ...
        {
            "name": "last_tool",
            "description": "...",
            "input_schema": {...},
            "cache_control": {"type": "ephemeral"}  # 断点 2: 工具定义末尾
        }
    ],
    messages=[
        {
            "role": "user",
            "content": [{
                "type": "text",
                "text": long_reference_doc,
                "cache_control": {"type": "ephemeral"}  # 断点 3: 参考文档
            }]
        },
        {"role": "assistant", "content": "我已阅读文档..."},
        {"role": "user", "content": "请根据文档回答..."}  # 断点后的内容不缓存
    ]
)
```

### 关键参数

| 参数                 | 值                                              |
| -------------------- | ----------------------------------------------- |
| **最小缓存长度**      | Sonnet: 1024 tokens; Opus/Haiku 4.5: 4096 tokens |
| **缓存断点上限**      | 4 个                                              |
| **写入成本**          | 1.25x 基础价格（5 分钟 TTL）或 2x（1 小时 TTL）   |
| **读取成本**          | 0.1x 基础价格                                     |
| **默认 TTL**          | 5 分钟，命中后刷新                                 |
| **可缓存内容**        | system、messages、tools                           |

### 成本计算示例

用 Anthropic 官方的 Pride and Prejudice（傲慢与偏见）Cookbook 举例，187k tokens 的小说全文作为上下文：

```text
首次请求（缓存写入）:
  输入: 187,000 tokens × 基础价 × 1.25 = 写入成本（较贵）
  
后续请求（缓存命中）:
  输入: 187,000 tokens × 基础价 × 0.1 = 读取成本（便宜 10 倍）
  TTFT: 从 ~11.5 秒 降至 ~3.5 秒（3.3x 加速）
  
结论: 只要同一 prefix 被查询 2 次以上，缓存就开始回本
```

---

## 四、Qwen（通义千问）的 Prompt Cache

### 核心特点：双模式（隐式 + 显式），互斥使用

Qwen 提供了两种缓存模式，它们**不能在同一个请求中混合使用**。

### 模式一：隐式缓存（自动模式）

系统自动识别重复前缀并缓存，开发者无需任何额外操作：

```python
from openai import OpenAI

client = OpenAI(
    api_key="your-dashscope-api-key",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

# 隐式缓存：系统自动处理，无需额外标记
response = client.chat.completions.create(
    model="qwen3-max",
    messages=[
        {"role": "system", "content": long_system_prompt},  # 自动缓存
        {"role": "user", "content": "你的问题..."},
    ]
)

# 查看缓存情况
print(f"缓存命中 Token: {response.usage.prompt_tokens_details.cached_tokens}")
```

| 参数             | 值                       |
| ---------------- | ------------------------ |
| **最小缓存长度** | 256 tokens               |
| **读取价格**     | 基础价的 20%              |
| **写入成本**     | 无额外费用                |
| **TTL**          | 系统自动管理              |

### 模式二：显式缓存（手动控制）

通过 `cache_control` 标记精确控制缓存位置，最多 4 个断点：

```python
response = client.chat.completions.create(
    model="qwen3-max",
    messages=[
        {
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": long_system_prompt,
                    "cache_control": {"type": "ephemeral"}  # 缓存断点
                }
            ]
        },
        {"role": "user", "content": "你的问题..."},
    ]
)

# 显式缓存的用量详情
usage = response.usage
print(f"缓存写入: {usage.prompt_tokens_details.cache_creation_tokens}")
print(f"缓存命中: {usage.prompt_tokens_details.cached_tokens}")
```

| 参数             | 值                                          |
| ---------------- | ------------------------------------------- |
| **最小缓存长度** | 1024 tokens                                 |
| **写入成本**     | 1.25x 基础价                                 |
| **读取价格**     | 基础价的 10%                                  |
| **TTL**          | 5 分钟，命中后刷新                            |
| **断点上限**     | 4 个                                         |

### 反向前缀匹配（Qwen 独有）

Qwen 的显式缓存有一个独特机制——**反向前缀匹配**。它不仅从头开始匹配前缀，还会检查最后 20 个 content block，从后向前查找最长匹配的缓存断点：

```text
常规前缀匹配（所有厂商）：从前往后匹配
  请求: [A][B][C][D][E]
  缓存: [A][B][C]
  匹配: [A][B][C] ✓ → 命中 3 个 block

Qwen 反向匹配（额外能力）：也从后往前检查最后 20 个 block
  请求: [A'][B'][C][D][E]   ← 前缀 A', B' 变了
  缓存: [C][D][E]
  反向匹配: [E][D][C] ✓ → 后缀也能命中！
```

**这意味着即使消息列表的开头发生了变化，只要尾部有足够长的相同内容，Qwen 仍然可以利用缓存。** 这对于对话历史不断增长、但工具调用结果等较新内容保持不变的场景特别有用。

### 支持的模型

- qwen3-max / qwen3-max-latest
- qwen-plus / qwen-plus-latest
- qwen-flash 系列（隐式缓存）
- qwen3-coder / qwen3-coder-plus

---

## 五、豆包（Doubao/火山方舟）的 Prompt Cache

### 核心特点：Context API 对象模式

豆包的缓存方式和其他三家都不同——它采用**显式创建缓存对象**的模式，先创建一个 Context，获得 `context_id`，然后在后续请求中引用这个 ID。

### 使用流程

```python
import requests

API_KEY = "your-api-key"
BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# 第一步：创建缓存上下文
create_resp = requests.post(
    f"{BASE_URL}/context/create",
    headers=HEADERS,
    json={
        "model": "doubao-1.5-pro-32k",
        "mode": "session",  # session 模式：缓存对话上下文
        "messages": [
            {"role": "system", "content": long_system_prompt},
            # 可以包含工具定义、few-shot 示例等
        ],
        "ttl": 3600  # 缓存 1 小时
    }
)
context_id = create_resp.json()["id"]
print(f"缓存上下文 ID: {context_id}")

# 第二步：在后续请求中引用缓存
chat_resp = requests.post(
    f"{BASE_URL}/chat/completions",
    headers=HEADERS,
    json={
        "model": "doubao-1.5-pro-32k",
        "context_id": context_id,  # 引用缓存！
        "messages": [
            {"role": "user", "content": "请帮我分析这段代码..."}
        ]
    }
)
```

### 两种缓存机制

**1. Context API（显式创建）**

| 参数             | 值                                    |
| ---------------- | ------------------------------------- |
| **支持模型**     | Doubao-1.5-pro-32k, Doubao-1.5-lite-32k |
| **创建方式**     | 先 POST 创建 context，获得 context_id   |
| **TTL**          | 自定义，支持按需续期                     |
| **成本节省**     | ~80% 输入 Token 成本                    |

**2. 透明缓存（自动模式）**

豆包也支持类似 OpenAI 的自动缓存，系统自动识别重复前缀。对于 Doubao-Seed-1.6 系列模型，还支持 Responses API 风格的缓存。

### 与其他厂商的区别

豆包的 Context API 模式更像传统的"会话管理"——你显式地创建、引用、销毁缓存对象。好处是控制力强、TTL 灵活；缺点是需要额外的代码来管理缓存生命周期。

---

## 六、四大厂商横向对比

```text
┌────────────┬──────────────┬──────────────┬──────────────┬──────────────┐
│            │   OpenAI     │   Claude     │   Qwen       │   豆包       │
├────────────┼──────────────┼──────────────┼──────────────┼──────────────┤
│ 触发方式   │ 全自动        │ 自动+显式断点│ 隐式+显式    │ Context API  │
│            │              │  (最多4个)   │ (最多4个)     │ +透明缓存    │
├────────────┼──────────────┼──────────────┼──────────────┼──────────────┤
│ 最小Token  │ 1024         │ 1024/4096    │ 256/1024     │ 模型相关     │
│            │              │ (按模型)     │ (按模式)     │              │
├────────────┼──────────────┼──────────────┼──────────────┼──────────────┤
│ 写入成本   │ 免费          │ 1.25x~2x    │ 免费/1.25x   │ 创建免费     │
│            │              │ (按TTL)      │ (按模式)     │              │
├────────────┼──────────────┼──────────────┼──────────────┼──────────────┤
│ 读取折扣   │ 50%~90%      │ 90%         │ 80%/90%      │ ~80%         │
│            │ (按模型)     │              │ (按模式)     │              │
├────────────┼──────────────┼──────────────┼──────────────┼──────────────┤
│ 默认TTL    │ 5-10min      │ 5min        │ 系统管理/5min│ 自定义       │
│            │ (最长24h)    │ (可选1h)    │ (按模式)     │              │
├────────────┼──────────────┼──────────────┼──────────────┼──────────────┤
│ 代码改动   │ 零改动        │ 少量改动     │ 零/少量      │ 需管理对象   │
│            │              │ (cache_ctrl) │ (按模式)     │ (context_id) │
├────────────┼──────────────┼──────────────┼──────────────┼──────────────┤
│ 独特能力   │prompt_cache  │ 多断点精控   │ 反向前缀匹配 │ Context      │
│            │_key路由      │ 读取仅0.1x  │ 双模式可选   │ 对象管理     │
├────────────┼──────────────┼──────────────┼──────────────┼──────────────┤
│ 最佳场景   │ 快速上手      │ 大文档分析   │ 国产模型集成 │ 会话型Agent  │
│            │ 高并发Agent  │ 精细成本控制 │ 灵活选择     │ 长TTL场景    │
└────────────┴──────────────┴──────────────┴──────────────┴──────────────┘
```

**选择建议：**

- **不想改代码、追求省心** → OpenAI（全自动，免费写入）
- **需要精细控制、大文档场景** → Claude（4 个断点，读取 0.1x 超便宜）
- **用国产模型、想要灵活度** → Qwen（双模式选择，反向匹配独有）
- **需要长 TTL、会话管理** → 豆包（Context 对象模式，TTL 可自定义）

---

## 七、最大化缓存命中率的最佳实践

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

## 八、常见误解澄清

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
2. **四大厂商对比**：
   - **OpenAI**：全自动、零配置、免费写入，`prompt_cache_key` 提升路由命中率
   - **Claude**：自动 + 显式断点（最多 4 个），写入 1.25x/2x，读取仅 0.1x
   - **Qwen**：双模式（隐式 256 token / 显式 1024 token），独有反向前缀匹配
   - **豆包**：Context API 对象模式，先创建再引用，TTL 灵活可控
3. **最大化命中率**：稳定前缀、追加式修改、固定工具列表 + allowed_tools、合理设置断点、持续监控命中率。
4. **缓存 ≠ 压缩**，窗口大 ≠ 不需要缓存，缓存不影响输出质量，KV 是张量不是文本。

> 💡 **预告**：到这里，我们完成了 Context Engineering 的全部内容——从定义、四大支柱，到核心模式、实战模板，再到 Prompt Cache 的底层原理和厂商对比。下一篇我们进入一个全新的主题：**Agent 概念入门**。我们会回答一个根本问题——什么是 Agent？它和普通的 LLM 应用有什么本质区别？从 ReAct 循环到工具调用，从"对话系统"到"能自主行动的智能体"，我们正式踏入 Agent 开发的核心领域。
