# LLM 模型参数避坑指南：Agent 开发者最该知道的事

---

> 摘要：做 Agent 开发，模型参数调不好，轻则输出不稳定，重则 token 烧钱、工具调用失败。本文从 Agent 实战出发，讲清楚 Temperature、Top-p、max_tokens、Structured Output、tool_choice 等核心参数的用法和常见坑，帮你少走弯路。

## 一、先建立认知：LLM 是"采样机器"

LLM 每次生成文本，本质上是在做一件事——**预测下一个 Token**，然后从概率分布中采样。

```text
输入: "今天天气很"
模型内部: 好(35%) > 棒(25%) > 差(15%) > 热(12%) > ...
```

所有采样相关的参数（Temperature、Top-p 等）控制的不是模型"知不知道答案"，而是**如何从概率分布中选择**。

---

## 二、Temperature：你真正需要知道的

### 核心机制

- **Temperature 低** → 概率分布更陡 → 高概率词更容易胜出 → 输出更确定
- **Temperature 高** → 概率分布更平 → 低概率词也有机会 → 输出更随机
- **Temperature = 0** → 贪婪解码，每次选概率最高的词

### Agent 开发的推荐值

| 场景 | 推荐 Temperature | 理由 |
|------|-----------------|------|
| 工具调用 / Function Calling | `0` ~ `0.1` | 参数必须精确，不能"创意发挥" |
| 数据提取 / JSON 输出 | `0` | 结构化输出需要确定性 |
| 代码生成 | `0` ~ `0.2` | 逻辑正确性优先 |
| 通用对话 | `0.5` ~ `0.7` | 平衡自然度和稳定性 |
| 创意写作 | `0.8` ~ `1.2` | 需要多样性和意外感 |

### 常见坑：Temperature=0 不等于确定性输出

这是很多人的误区。2026 年 Sara Zan 的一篇深度分析讲得很清楚：

> **采样确定性 ≠ 系统确定性。**

即使 `temperature=0`，同一个 prompt 仍可能产生不同输出：


---

## 三、Top-p vs Top-k：二选一就够了

Top-k：只从概率最高的 k 个词里选

简单粗暴，但 k 是固定值，不够灵活。

Top-p（Nucleus Sampling）：动态选择累积概率达到阈值的最小候选集

```text
概率排序：好(35%) > 棒(25%) > 差(15%) > 热(12%) > ...
Top-p=0.8 → 35+25+15+12=87% ≥ 80% → 选前4个词
```

**Top-p 是 Top-k 的动态版本**，大多数场景更优，是目前主流 API 的默认选择。

### 实践原则

- **不要同时调 Temperature 和 Top-p**，OpenAI 官方建议只调一个
- Agent 开发中：**一般保持 `top_p=1.0` 也就是不用管，只调 Temperature 就够了**

---

## 四、max_tokens 的"坑王"陷阱

这可能是 Agent 开发中**出 bug 最多的参数**。

### 坑 1：`max_tokens` vs `max_completion_tokens`

OpenAI 从 o1 系列开始引入 `max_completion_tokens` 取代 `max_tokens`：

| 参数 | 含义 | 适用模型 |
|------|------|---------|
| `max_tokens` | 限制**生成**的 token 数 | 传统模型（gpt-4o 等） |
| `max_completion_tokens` | 限制**推理 + 生成**的总 token 数 | 推理模型（GPT-5、o3 等） |

**关键区别**：推理模型会先消耗大量 token 做内部推理（thinking），然后才生成可见输出。如果 `max_completion_tokens` 设太小，推理 token 用完了预算，你会得到**空响应**——钱花了，什么都没拿到。

```python
# ❌ 这样做，GPT-5 可能返回空内容
response = client.chat.completions.create(
    model="gpt-5",
    messages=[...],
    max_completion_tokens=500  # 推理就用掉了，没剩余给输出
)

# ✅ 给推理模型留足空间
response = client.chat.completions.create(
    model="gpt-5",
    messages=[...],
    max_completion_tokens=4000,  # 至少留够空间
    reasoning={"effort": "low"}   # 或者控制推理级别
)
```

### 坑 2：两个参数不能同时设

某些 provider 会报错：`max_tokens and max_completion_tokens cannot be set at the same time`。写兼容代码时要根据模型类型选择用哪个。

### 坑 3：max_tokens 不是"目标长度"

`max_tokens` 只是上限，模型遇到自然结束（EOS Token）就会停止。别指望设 `max_tokens=500` 就能拿到刚好 500 token 的输出。

### 坑 4：别忘了检查 finish_reason

```python
response = client.chat.completions.create(...)
choice = response.choices[0]

if choice.finish_reason == "length":
    # 输出被截断了！可能 JSON 不完整
    print("输出被 max_tokens 截断，数据可能不完整")
elif choice.finish_reason == "stop":
    # 正常结束
    pass
```

---

## 五、Structured Output：告别"祈祷式 JSON 解析"

在 Agent 开发中，你经常需要模型返回结构化数据（JSON）。过去的做法是在 prompt 里说"请返回 JSON"，然后祈祷它格式正确。现在有更好的方式。

### 方案对比

| 方案                                              | 保证有效 JSON | 保证符合 Schema | 推荐度 |
| ----------------------------------------------- | --------- | ----------- | --- |
| Prompt 里说"返回 JSON"                              | ❌         | ❌           | ⛔   |
| `response_format: {"type": "json_object"}`      | ✅         | ❌           | ⚠️  |
| `response_format: {"type": "json_schema", ...}` | ✅         | ✅           | ✅✅  |
| Function Calling / Tool Use                     | ✅         | ✅           | ✅✅✅ |

### 推荐做法：用 Structured Output 或 Tool Use

```python
from pydantic import BaseModel
from openai import OpenAI

client = OpenAI()

class UserInfo(BaseModel):
    name: str
    age: int
    city: str
    hobbies: list[str]

# 方式 1：Structured Output
completion = client.beta.chat.completions.parse(
    model="gpt-4o-mini",
    messages=[
        {"role": "user", "content": "张三，28岁，北京人，爱好跑步和阅读。"}
    ],
    response_format=UserInfo,
    temperature=0
)
user = completion.choices[0].message.parsed
print(user.name, user.age)  # 类型安全，不用手动 json.loads
```

对于 Agent 的工具调用场景，**Function Calling 本身就是 Structured Output 的最佳实践**——模型返回的参数天然是 Schema 约束的 JSON。

PS：这部分后期会详细讲解。

---

## 六、tool_choice：控制模型"用不用工具"

在 Agent 开发中，`tool_choice` 决定了模型是否调用工具：

| tool_choice | 行为 | 适用场景 |
|-------------|------|---------|
| `"auto"`（默认） | 模型自行决定是否调工具 | 通用 Agent 循环 |
| `"required"` / `"any"` | 必须调用某个工具 | 强制执行步骤、避免模型"偷懒"直接回答 |
| `{"type": "function", "function": {"name": "xxx"}}` | 强制调用指定工具 | 已知下一步该做什么 |
| `"none"` | 禁止调用工具 | 纯对话/总结阶段 |

例如：
```python
# openai sdk
response = client.chat.completions.create(
    model="qwen3.5-flash",
    messages=messages,
    tools=tools,
    tool_choice="required" # 默认 auto
)

# 或者Langchain
llm = ChatOpenAI(model="gpt-4o") 
tools = [get_weather, get_time] 
# auto：模型自决 
llm_auto = llm.bind_tools(tools, tool_choice="auto") 
# any：必须调用工具（但选哪个自决） 
llm_any = llm.bind_tools(tools, tool_choice="any") 
# 强制指定工具 
llm_forced = llm.bind_tools(tools, tool_choice="get_weather")
```
### 常见坑

- **模型跳过工具直接回答**：当你期望模型调工具但它直接给了文本回复时，用 `tool_choice="required"` 强制它
- **不同 provider 的参数名不同**：OpenAI 用 `tool_choice`，Anthropic 的 `tool_choice` 语法略有差异（`{"type": "any"}` vs `"required"`），写跨平台 Agent 时要注意适配


---

## 七、其他值得了解的参数

### stop（停止序列）

让模型在遇到指定字符串时停止生成，对控制输出格式有用：

```python
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "列出前3项："}],
    stop=["\n4."]  # 只要前3项，遇到"4."就停
)
```

### reasoning_effort（推理力度）

推理模型特有参数，控制模型在内部"思考"上花多少力气：

```python
# 简单任务用 low，省 token
response = client.chat.completions.create(
    model="gpt-5",
    messages=[...],
    reasoning={"effort": "low"}
)

# 复杂推理用 high
response = client.chat.completions.create(
    model="gpt-5",
    messages=[...],
    reasoning={"effort": "high"}
)
```

`reasoning_effort="minimal"` 在某些模型上表现很差（几乎禁用推理），建议至少用 `"low"`。

### presence_penalty / frequency_penalty

- `presence_penalty`：惩罚已出现的词（鼓励引入新话题）
- `frequency_penalty`：按出现频率惩罚（防止同一个词反复出现）

**注意**：推理模型（GPT-5 系列）**不支持这两个参数**。在 Agent 开发中这两个参数用得不多，通用场景保持默认即可。

---

## 九、常见误区总结

| 误区                    | 事实                                         |
| --------------------- | ------------------------------------------ |
| Temperature=0 输出就一定相同 | 浮点运算和 batch 差异导致仍可能不同                      |
| Temperature 越高模型越聪明   | 高温只增加随机性，不增加能力，反而更容易出错                     |
| max_tokens 设得越大越保险    | 推理模型中 token 预算包含推理消耗，设大了费钱，设小了空响应          |
| 所有模型参数都通用             | 推理模型不支持 temperature/top_p/penalty，必须做兼容    |
| JSON 输出靠 prompt 就行    | 用 Structured Output 或 Function Calling 才可靠 |

---

## 小结

做 Agent 开发，模型参数的核心原则就三条：

1. **确定性任务用低温或零温**——工具调用、数据提取、代码生成
2. **用 Structured Output 代替"祈祷式解析"**——response_format 或 tool use
3. **推理模型是另一套规则**——用 `max_completion_tokens` + `reasoning_effort`，别传 temperature

> 💡 **预告**：掌握了参数调优之后，下一步我们进入 API 调用实战——用 Python SDK 发起真实请求，手动维护消息列表，完成第一次完整的多轮对话体验。
