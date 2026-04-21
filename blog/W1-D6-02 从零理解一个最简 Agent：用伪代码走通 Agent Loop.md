# 从零理解一个最简 Agent：用伪代码走通 Agent Loop

---

> 摘要：上一篇我们建立了六大设计模式的全局视野。但六个模式听起来挺唬人，到底一个最简单的 Agent 长什么样？这篇我们把所有框架、模式、术语先放到一边，用伪代码和真实 API 走通一个最小可运行的 Agent——你会发现，所有 Agent 的心脏就是同一个 while 循环。理解了这个循环，后面不管学什么框架都只是在它外面加壳。

### 一、2句话搞明白Agent

Barry Zhang（Anthropic 工程师）把**Agent压缩两行就能说清**：

```python
env = Environment()
while True:
    action = llm.run(system_prompt + env.state)
    env.state = tools.run(action)
```

环境变化 → 模型观察 → 模型行动 → 重复。其他一切都是编排。

> **Agent = LLM + Memory + Planning + Tool Use**

而 Agent Loop 就是把这四个组件绑在一起的运行时。

![](https://limbo.oss-cn-beijing.aliyuncs.com/wiki/ChatGPT%20Image%202026%E5%B9%B44%E6%9C%8821%E6%97%A5%2017_05_17.png)

---

## 二、六行代码的"规范循环"

把所有框架的实现抽象一下，规范的 Agent 循环就是这样：

```python
while not done:
    response = call_llm(messages)       # 1. 把当前上下文发给 LLM
    if response.has_tool_calls:         # 2. 检查 LLM 是否想调用工具
        results = execute_tools(        # 3. 执行工具，拿到结果
            response.tool_calls         # 3.1 需要的参数等指导数据
        )
        messages.append(results)        # 4. 把结果塞回消息列表
    else:                               # 5. 没有工具调用 = LLM 觉得完成了
        done = True
        return response                 # 6. 返回最终回复
```

这里面最关键的洞察是：

- **工具调用 = 继续信号**。LLM 返回了 tool_calls，意味着"我还没搞定，需要更多信息或需要做一个操作"
- **纯文本回复 = 终止信号**。LLM 没有返回 tool_calls，而是直接给了文本回复，意味着"我有足够的信息来回答了"

**这就是 Agent 和 Chatbot 的本质区别——Chatbot 只调用一次 LLM，Agent 是 LLM 在循环里不断调用工具直到任务完成。**

---

## 三、手动走通一遍：北京天气查询

![](https://limbo.oss-cn-beijing.aliyuncs.com/wiki/ChatGPT%20Image%202026%E5%B9%B44%E6%9C%8821%E6%97%A5%2016_14_43.png)

---

## 四、用 Python 写一个真正能跑的最简 Agent

把上面的伪代码变成真实的 Python 代码，其实只需要 30 行左右。我用百炼 API（兼容 OpenAI 格式）来演示：

```python
import json
from openai import OpenAI

client = OpenAI(
    api_key="你的API Key",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

import json

# ---- 工具定义 ----
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定城市的当前天气",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名称"}
                },
                "required": ["city"]
            }
        }
    }
]

# ---- 工具实现 ----
def get_weather(city: str) -> str:
    fake_data = {"北京": "晴, 28°C", "上海": "多云, 32°C"}
    return fake_data.get(city, f"{city}：数据暂无")

# ---- 工具注册 ----
tool_map = {"get_weather": get_weather}

# ---- Agent 核心循环 ----
def run_agent(user_input: str, max_iterations: int = 10):
    messages = [
        {"role": "system", "content": "你是一个有用的助手，可以查询天气。"},
        {"role": "user", "content": user_input}
    ]

    for i in range(max_iterations):
        response = client.chat.completions.create(
            model="qwen3.5-flash",
            messages=messages,
            tools=tools,
        )
        choice = response.choices[0]
        msg = choice.message

        # 打印思考过程
        if msg.reasoning_content:
            print(f"[思考] {msg.reasoning_content}")

        # 打印工具调用详情
        if msg.tool_calls:
            for tc in msg.tool_calls:
                print(f"[工具调用] id={tc.id}, name={tc.function.name}, args={tc.function.arguments}")

        # 必须先把 assistant 消息追加到历史，再追加工具结果
        messages.append(msg)

        # 检查是否有工具调用
        if not msg.tool_calls:
            # 没有工具调用 → 循环结束
            print(f"[Agent] 循环 {i+1} 轮后完成")
            return msg.content

        # 执行工具调用
        for tool_call in msg.tool_calls:
            fn_name = tool_call.function.name
            fn_args = json.loads(tool_call.function.arguments)
            print(f"[Agent] 执行: {fn_name}({fn_args})")

            result = tool_map[fn_name](**fn_args)
            print(f"[Agent] 结果: {result}")

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": str(result)
            })

    return "达到最大迭代次数，Agent 停止"

# ---- 运行 ----
answer = run_agent("北京今天天气怎么样？如果超过30度推荐冷饮")
print(f"\n最终回答：{answer}")
```

运行效果：

![](https://limbo.oss-cn-beijing.aliyuncs.com/wiki/20260421163834334.png)

---

## 五、一个你一定会踩的坑

![](https://limbo.oss-cn-beijing.aliyuncs.com/wiki/ChatGPT%20Image%202026%E5%B9%B44%E6%9C%8821%E6%97%A5%2016_52_29.png)

写上面代码的时候，有一个**顺序问题**是新手最容易犯的错：

```python
# ❌ 错误顺序
messages.append(tool_result)    # 先加工具结果
messages.append(msg)            # 再加 assistant 消息

# ✅ 正确顺序
messages.append(msg)            # 先加 assistant 消息（包含 tool_calls）
messages.append(tool_result)    # 再加工具结果（引用 tool_call_id）
```

**你必须先把 assistant 的消息（包含 `tool_calls`）追加到历史，再追加工具结果。** 因为 API 要求 tool result 消息必须引用已存在的 `tool_call_id`。顺序搞反了，你会拿到一个莫名其妙的验证错误，而且错误信息根本看不出是这个原因导致的。


---

## 六、循环凭什么能停下来？

回顾一下前面的代码，循环停止有几种情况：

### 1. LLM 自己决定停

这是最正常的终止方式。当 LLM 判断信息足够了、可以回答用户了，它就不再生成 tool_calls，而是直接输出文本。框架检测到"这一轮没有工具调用" → 循环结束。

用不同 API 的判断方式略有不同：
- **OpenAI 风格**：检查 `msg.tool_calls` 是否为空
- **Anthropic 风格**：检查 `response.stop_reason == 'end_turn'`

但逻辑完全一样——**工具调用是继续信号，纯文本是终止信号**。

### 2. 达到最大迭代次数（兜底）

这是最重要的安全机制。如果不设上限，Agent 可能陷入死循环，Token 无限消耗。

生产环境的典型值是 **15-25 步**。到了上限后，不要直接静默停止——用一个叫 **"early stopping generate"** 的模式：*追加一条消息告诉 LLM"你已经达到最大步数了，请基于目前收集到的信息给出最佳回答"*，然后**不带工具**再调一次 LLM。这样模型还有机会做个总结，而不是让用户什么都看不到。

### 3. 其他停止条件

- **超时**：某个工具执行太慢或挂掉
- **成本预算**：Token 消耗超过预设阈值（比如 $2/次）
- **用户中断**：用户取消了请求

---

## 七、消息列表——Agent 的"短期记忆"

回头看代码，`messages` 列表其实就是 Agent 的短期记忆。每一轮循环都在往里面追加新信息：

```text
messages = [
    system_prompt,          # 角色设定（始终在最前面）
    user_message,           # 用户的原始问题
    assistant (tool_call),  # 第 1 轮：LLM 决定调用工具
    tool_result,            # 第 1 轮：工具返回结果
    assistant (tool_call),  # 第 2 轮：LLM 决定调用另一个工具
    tool_result,            # 第 2 轮：工具返回结果
    assistant (text),       # 第 3 轮：LLM 给出最终回答
]
```

**每一轮循环，LLM 都能看到之前所有的消息**——包括自己之前调用了哪些工具、工具返回了什么。这就是为什么它能基于工具结果做进一步推理。

但这也意味着一个问题：**消息列表会越来越长，Token 消耗越来越大**。

Manus 团队实测发现：**工具返回结果占了全部 Token 的 67.6%**，System Prompt 只占 3.4%。也就是说，优化你的 System Prompt 几乎没意义——**真正吃 Token 的是工具返回的数据**。

这就是为什么之前学的 Context Engineering 如此重要——压缩、路由、渐进披露，全都是为了管理这个不断膨胀的消息列表。

---

## 八、各大框架的 Agent Loop 长啥样？

既然核心循环都一样，不同框架的区别在哪？主要是循环**外面**套的东西不同：

| 框架 | 核心循环 | 独特之处 |
|------|---------|---------|
| **OpenAI Agents SDK** | `while(true)` + `runSingleTurn()` | 4 种分支（final_output / handoff / run_again / interruption），Agent 间传递用 `transfer_to_<name>` 工具实现 |
| **Claude Agent SDK** | 循环在子进程中运行 | Agent Loop 跑在 Claude Code CLI 里，通过 stdin/stdout 的 NDJSON 通信；自动 context compaction |
| **LangGraph** | 有向循环图替代 while | State + Nodes + Edges，每个节点转换时自动 checkpoint，支持中断和恢复 |
| **Vercel AI SDK** | `ToolLoopAgent` | 默认不循环（`stepCountIs(1)`），需要显式 opt-in；`prepareStep` 钩子可以每步换模型、换工具 |
| **smolagents** | 累积 typed steps | 模型写 Python 代码而非 JSON；到 `max_steps` 时自动合成回复而非静默停止 |

**核心都一样——while 循环 + 工具调用 + 消息追加。区别在安全机制、上下文管理和编排能力。**

---

## 九、100 行代码的震撼

![](https://limbo.oss-cn-beijing.aliyuncs.com/wiki/CleanShot%202026-04-21%20at%2016.56.37.png)

SWE-agent 团队做了一个实验：他们把完整的 SWE-agent（花了一年多时间开发的复杂系统）精简到只有 **100 行 Python 代码**——叫 mini-SWE-agent。它只给模型一个工具——bash，用正则表达式从模型输出中解析命令，没有结构化工具调用，没有 JSON Schema。结果？在 SWE-bench Verified 基准测试上得分 **74-76.8%**（取决于模型）。
而当时的最先进成绩大约是 80.9%。**100 行代码达到了最优水平的 95%。**

这说明什么？**循环本身不是瓶颈。** 真正的复杂度在工具设计、上下文管理和循环外的安全机制上。

Anthropic 自己也说了：

> "Agent 能处理复杂任务，但它们的实现通常很简洁。**本质上就是 LLM 在循环中根据环境反馈使用工具。**"

---

## 十、Agent Loop 的六种死法

虽然循环很简单，但在生产环境中它可能以各种方式挂掉。Steve Kinney 总结了六种常见的死法，我觉得现在就该知道，以后少踩坑：

1. **无限循环**——最常见。缺少终止条件、工具返回空结果导致模型反复重试、模型推理不出怎么走出当前状态。有人遇到过同一个回答重复了 58 次才被发现。
2. **上下文窗口溢出**——消息历史每轮都在增长。没有压缩或子 Agent 隔离，长时间运行的 Agent 会把上下文窗口撑爆，模型开始丢信息。
3. **工具混淆**——工具太多、描述重叠、命名模糊。模型选错工具，或者在两个看起来都行的工具之间来回切换。
4. **错误累积**——第 4 步的错误默默传播到后面所有步骤。到第 18 步，你得到一个自信、连贯、但完全错误的结果。
5. **框架锁定**——你对框架底层的理解是错的。出问题时你在错误的层调试。Anthropic 建议："确保你理解底层代码。对底层实现的错误假设是客户错误的常见来源。"
6. **缺少幂等性**——Agent 在超时后重试工具调用，可能发出重复邮件、创建重复工单、处理重复支付。每个有副作用的工具都需要幂等键。

---

## 小结

今天搞明白了最核心的一件事：

**所有 Agent 的心脏是同一个 while 循环**——调 LLM → 有工具调用就执行 → 把结果塞回消息列表 → 再调 LLM → 没有工具调用就结束。六行代码就是全部核心逻辑。

几个关键认知：

1. **工具调用是继续信号，纯文本是终止信号**。这是 Agent 知道何时停下来的机制
2. **消息列表就是短期记忆**。每轮循环都在追加，LLM 每次都能看到全部历史
3. **循环本身不难，难的是外面套的东西**——安全控制、上下文管理、工具设计、错误处理
4. **100 行代码可以达到 SOTA 的 95%**。循环不是瓶颈，工具和上下文才是
5. **先追加 assistant 消息，再追加 tool result**。顺序搞反会报莫名其妙的错
6. **一定要设 max_iterations**。没有兜底机制的 Agent 循环是一颗定时炸弹

一条可带走的经验：**如果你想真正理解一个 Agent 框架，先自己手写一个 30 行的 Agent Loop。遇到过它要解决的问题之后，你才会理解框架为什么那样设计。**

> 💡 **预告**：下周进入第二周——动手实现。我们会从 Function Calling / Tool Use 开始，深入理解模型是怎么"选择"调用哪个工具的，工具定义的 JSON Schema 怎么写才好用，以及多工具编排的技巧。今天写的这个 30 行 Agent 还只是骨架，下周给它加肌肉。
