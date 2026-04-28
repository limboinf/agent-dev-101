# 完整走通 Function Calling：从单工具到多工具编排

---

> 摘要：昨天学了怎么定义工具、怎么让模型"选"工具，但那只是在"点菜"。今天要"上菜"了——走通从请求到回复的完整闭环。走通这个流程的过程中，我踩了三个让人印象深刻的坑（尤其是消息顺序那个，调了一小时才搞明白）。搞定单工具之后，再来实现多工具编排：注册表模式、命名规范、错误处理——最终写出一个天气查询 + 计算器的完整 Agent，让它能处理"查天气 → 看温度 → 算差值"这种需要多步推理的任务。你会发现，今天写的代码和上周那个 Agent Loop 的伪代码，长得一模一样。

## 一、完整流程一图看懂

上一篇笔记我们只做了 Function Calling 的前半段——模型告诉我们"我想调 get_weather，参数是北京"。但问题来了：然后呢？

很多人陷入一个误区：天真地以为模型会"自动"执行工具。毕竟它都知道该调哪个函数了，直接跑一下不就行了？

当然不行。**模型只是一个文本生成器，它没有执行代码的能力。** 它只是"点了菜"，你得自己去"炒菜上菜"，然后把菜端回来给它看。

OpenAI 在文档里把这个过程总结为五步，我画了一张图：
![](https://limbo.oss-cn-beijing.aliyuncs.com/wiki/20260428081322188.png)

注意看：**模型被调用了两次**。第一次返回的不是文本回答，而是"我想调工具"的指令（tool_call）；你执行完工具后，带着结果第二次调用模型，它才给出最终回答。

**Function Calling 不是一次请求就完事，它是你的代码和模型之间的一个多轮对话。**

把五步再拎出来明确一下：

| 步骤             | 谁做的  | 做了什么                                   |
| -------------- | ---- | -------------------------------------- |
| ① 发请求          | 你的代码 | 把用户消息 + 工具定义发给模型                       |
| ② 返回 tool_call | 模型   | "我要调 get_weather，参数是 `{"city": "北京"}`" |
| ③ 执行工具         | 你的代码 | 拿着参数执行真正的函数，拿到结果                       |
| ④ 返回工具结果       | 你的代码 | 把结果以 tool message 格式塞回消息列表，再次调用模型      |
| ⑤ 最终回答         | 模型   | 基于工具结果生成自然语言回复（或者继续调工具）                |

第 ⑤ 步有个括号很关键——模型看了工具结果之后，**可能还想调另一个工具**。比如查了天气发现 35°C，然后它想调计算器算一下和 30°C 差多少。这就形成了一个循环。

是不是很眼熟？没错，这就是我们上篇笔记的那个 Agent Loop。

---

## 二、消息格式 — 代码怎么写

理解了流程，来看代码层面到底是怎么实现的。我把每一步拆开来演示。

### Step 1：带着工具定义发请求

```python
from app.llm import client
from app.config import DEFAULT_MODEL

messages = [
    {"role": "user", "content": "北京天气怎么样？"}
]

response = client.chat.completions.create(
    model=DEFAULT_MODEL,
    messages=messages,
    tools=tools,  # 昨天定义的工具列表
)
```

### Step 2：模型返回 tool_call

```python
msg = response.choices[0].message

# 检查：模型是不是想调工具？
if msg.tool_calls:
    tc = msg.tool_calls[0]
    print(f"工具名: {tc.function.name}")       # "get_weather"
    print(f"参数:   {tc.function.arguments}")   # '{"city": "北京"}'
    print(f"调用ID: {tc.id}")                   # "call_abc123"（自动生成）
```

这里有三个关键字段：
- `tc.function.name` — 模型选择的工具名
- `tc.function.arguments` — 参数的 JSON 字符串（注意是字符串，不是 dict）
- `tc.id` — 这次调用的唯一标识，后面返回结果时要用

### Step 3：执行工具，拼装 tool message

```python
import json

# !!!! 关键：先把 assistant 消息追加到历史
messages.append(msg)

# 解析参数并执行工具
args = json.loads(tc.function.arguments)
result = get_weather(args["city"])  # 执行真正的函数

# 追加 tool message
messages.append({
    "role": "tool",
    "tool_call_id": tc.id,    # 必须引用对应的 tool_call_id
    "content": str(result)     # 工具返回值，必须是字符串
})
```

### Step 4：再次调用模型，拿到最终回答

```python
response = client.chat.completions.create(
    model=DEFAULT_MODEL,
    messages=messages,
    tools=tools,
)
final_answer = response.choices[0].message.content
print(f"最终回答: {final_answer}")
# "北京今天天气晴朗，气温 28°C。"
```

到这里，一个完整的 Function Calling 闭环就走通了。

执行完之后，`messages` 列表长这样：

```text
messages = [
    {"role": "user",      "content": "北京天气怎么样？"},
    {"role": "assistant", "tool_calls": [...]},           # 模型的工具调用请求
    {"role": "tool",      "tool_call_id": "call_abc123",  # 工具返回的结果
                          "content": "晴, 28°C"},
    {"role": "assistant", "content": "北京今天..."}        # 最终回答（第二次调用才有）
]
```

四种角色的消息交替出现：user → assistant(tool_call) → tool → assistant(text)。模型每次都能看到完整的消息历史，所以它知道自己之前调了什么工具、拿到了什么结果。

---

## 三、踩坑实录 — 三个让我印象深刻的坑

### 坑 1：忘记把 assistant 消息追加回 messages

错误代码是这样的：

```python
# ❌ 
if msg.tool_calls:
    result = get_weather("北京")
    messages.append({
        "role": "tool",
        "tool_call_id": msg.tool_calls[0].id,
        "content": result
    })
    # 直接再调模型...
```

跑起来直接报错，大概意思是 "tool_call_id 找不到对应的调用"。我盯着代码看了半天没发现问题——tool_call_id 明明就是从 msg 里拿的，怎么会找不到？

后来才意识到：**我没有把 assistant 的消息（包含 tool_calls 字段的那条）追加到 messages 里。** API 要求 tool message 必须引用一个已经存在于消息历史中的 tool_call_id。你不把 assistant 消息加进去，tool_call_id 就不存在于历史中，自然报错。

```python
# ✅ 正确写法：先追加 assistant，再追加 tool
messages.append(msg)            # 先！这条消息里包含 tool_calls
messages.append({
    "role": "tool",
    "tool_call_id": msg.tool_calls[0].id,
    "content": result
})
```

上周 D6 的文章里其实已经提过这个坑了。但自己真写代码的时候还是一头栽进去——看来踩坑这事，光看别人讲不行，得自己亲自踩一遍才长记性。

### 坑 2：并行工具调用时 tool_call_id 搞混

当模型一次返回多个 tool_calls（比如同时查巴黎和东京的天气），你需要对每个 tool_call **分别** 追加对应的 tool message，而且 **tool_call_id 必须对应上**。

```python
# ✅ 每个 tool_call 都要有对应的 tool message
messages.append(msg)  # 一条 assistant 消息包含多个 tool_calls

for tc in msg.tool_calls:
    args = json.loads(tc.function.arguments)
    result = tool_map[tc.function.name](**args)
    messages.append({
        "role": "tool",
        "tool_call_id": tc.id,   # 每个都要用自己的 id
        "content": str(result)
    })
```

如果你只返回了一个 tool message，或者 id 对应错了，模型要么报错，要么给出莫名其妙的回答。

### 坑 3：工具返回值必须是字符串

```python
# ❌ 返回 dict
def get_weather(city):
    return {"city": city, "temp": 28, "weather": "晴"}
```

结果 API 报序列化错误。原因很简单：**tool message 的 `content` 字段必须是字符串。**
修复方法：
```python
# ✅ 返回字符串
messages.append({
    "role": "tool",
    "tool_call_id": tc.id,
    "content": json.dumps(result, ensure_ascii=False)  # dict → JSON 字符串
})
```

OpenAI 文档里还提了一个容易忽略的细节：如果你的工具没有返回值（比如 `send_email`），不要返回 `None`，而是返回一个有意义的字符串，比如 `"邮件发送成功"`。模型需要看到一个结果来判断下一步该做什么。

---

## 四、多工具编排 — 从一个工具到一打工具

搞定单工具完整流程之后，自然就会遇到一个问题：**当你有好几个工具时，代码怎么组织？**

不要 if/elif 硬写的：
```python
# ❌ 最初的笨办法
if tc.function.name == "get_weather":
    result = get_weather(...)
elif tc.function.name == "calculate":
    result = calculate(...)
elif .... # 工具越多，这里越长...
```

工具一多就受不了了。这个时候 "注册表"的模式就上场了

### 工具注册表模式

```python
# ✅ 用字典做工具注册表
tool_map = {
    "get_weather": get_weather,
    "calculate": calculate,
    "search_products": search_products,
}

# 通用的工具执行函数
def execute_tool(name: str, arguments: str) -> str:
    """执行工具并返回结果字符串"""
    if name not in tool_map:
        return f"未知工具: {name}"
    try:
        args = json.loads(arguments)
        result = tool_map[name](**args)
        return str(result)
    except Exception as e:
        return f"工具执行失败: {e}"
```

名字 → 函数的映射，干净利落。新增工具只需要在 `tool_map` 里加一行，不用改执行逻辑。

### 工具命名最佳实践

工具一多，命名就特别重要了。这方面 Anthropic 和 Manus 的经验都值得借鉴。

**Manus 的前缀规范：**

Manus 团队所有工具都用前缀分组：`browser_navigate`、`browser_click`、`browser_type`、`shell_exec`、`shell_view`。这样模型一看名字就知道这组工具是干嘛的，选择起来更准确。而且他们还利用前缀做了个巧妙的优化——通过 token logits 约束，可以强制模型在某个状态下只选某个分组的工具。

**Anthropic 的命名空间建议：**

当你的 Agent 同时连接了多个服务的 MCP Server 时（比如同时用 Asana 和 Jira），工具命名空间就更重要了。Anthropic 建议按服务前缀命名：`asana_search_tasks`、`jira_search_issues`，避免模型在两个服务的同名工具之间搞混。

整理一下命名规范：

| 维度 | ❌ 差的命名 | ✅ 好的命名 |
|------|-----------|-----------|
| 功能不清 | `search`、`get`、`do` | `search_products`、`get_weather` |
| 没有分组 | `navigate`、`click`、`type` | `browser_navigate`、`browser_click` |
| 多服务冲突 | `search_tasks`（哪个服务的？） | `asana_search_tasks`、`jira_search_issues` |
| 含义模糊 | `process_data` | `calculate_shipping_cost` |

### 工具数量控制

关于工具数量，有几个来自实战的经验值得记住：

- **OpenAI 建议：初始可用工具控制在 20 个以内。** 工具太多，模型的选择准确率会明显下降。
- **Vercel 的教训：他们曾经删掉了 80% 的工具，结果 Agent 的表现反而更好了。** 少即是多。
- **Anthropic 的合并建议：经常连续调用的工具，合并成一个。** 比如 `list_users` + `list_events` + `create_event` → 一个 `schedule_event` 搞定。

---

## 五、错误处理 — 工具执行失败怎么办

真实场景中，工具执行一定会出错。API 挂了、参数不对、超时——各种情况都可能发生。

我一开始的做法是简单粗暴地 `raise Exception`，然后整个 Agent 就崩了。后来发现正确的做法是：**把错误信息作为 tool message 返回给模型，让它自己决定怎么办。**

### 原则 1：返回有用的错误信息

```python
# ❌ 差的错误处理：返回 traceback
"Traceback (most recent call last):\n  File \"main.py\", line 42...\nKeyError: 'temperature'"

# ✅ 好的错误处理：返回可操作的信息
"查询失败：城市名 '北京市' 无法识别。请使用简称，例如 '北京' 而非 '北京市'。"
```

Anthropic 在他们的工具设计文档里专门强调了这一点：

> "如果工具调用出错，你可以在错误响应里 prompt-engineer，清晰地告诉模型具体哪里出了问题以及如何改进，而不是返回晦涩的错误码或堆栈跟踪。"

这个思路很妙——**错误信息本身就是给模型的"提示词"**。写好了，模型能自动调整参数重试；写烂了，模型只会一脸懵地继续出错。

### 原则 2：给模型一个重试的机会

```python
def execute_tool(name: str, arguments: str) -> str:
    if name not in tool_map:
        return f"未知工具 '{name}'。可用工具: {', '.join(tool_map.keys())}"
    try:
        args = json.loads(arguments)
        return str(tool_map[name](**args))
    except json.JSONDecodeError:
        return f"参数解析失败，请检查 JSON 格式: {arguments}"
    except TypeError as e:
        return f"参数类型错误: {e}。请检查参数名和类型是否正确。"
    except Exception as e:
        return f"工具执行出错: {e}"
```

把错误信息返回给模型后，它可能会：
1. 调整参数重新调用同一个工具
2. 换一个工具来解决问题
3. 直接告诉用户"抱歉，这个功能暂时不可用"

**不管哪种，都比你的程序直接崩掉好得多。**

### 原则 3：设置超时和最大迭代次数

上周 D6 讲 Agent Loop 的时候就强调过：**一定要设 max_iterations。** 没有兜底机制的循环是一颗定时炸弹。

```python
for i in range(max_iterations):
    response = call_llm(messages)
    if not response.tool_calls:
        return response.content  # 正常终止
    # ... 执行工具 ...

# 到达上限
return "抱歉，处理步骤过多，请简化您的请求。"
```

另一个要注意的是上周提到的**幂等性**：如果工具有副作用（发邮件、下单、转账），Agent 在超时重试时可能会重复执行。每个有副作用的工具都应该有幂等保护。

---

## 六、完整实战 — 天气 + 计算器 Agent

好了，把前面所有的知识点串起来，写一个完整的、能跑的 Agent。它有两个工具：查天气和做计算。

```python
import json
from app.llm import client
from app.config import DEFAULT_MODEL

# ========== 工具定义 ==========
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定城市的当前天气信息，包括温度和天气状况。当用户询问某个城市的天气时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名称，例如 '北京'、'上海'"
                    }
                },
                "required": ["city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "执行数学计算表达式并返回结果。当用户需要精确计算数学表达式时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "数学表达式，例如 '2 + 3 * 4'、'(100 - 32) * 5 / 9'"
                    }
                },
                "required": ["expression"]
            }
        }
    }
]

# ========== 工具实现 ==========
def get_weather(city: str) -> str:
    """模拟天气查询（实际项目中调用真实 API）"""
    fake_data = {
        "北京": "晴, 28°C, 湿度 45%",
        "上海": "多云, 32°C, 湿度 78%",
        "广州": "雷阵雨, 35°C, 湿度 85%",
    }
    return fake_data.get(city, f"暂无 {city} 的天气数据")

def calculate(expression: str) -> str:
    """安全的数学计算"""
    try:
        # 限制只能用数学运算，不能执行任意代码
        result = eval(expression, {"__builtins__": {}}, {})
        return str(result)
    except Exception as e:
        return f"计算失败: {e}。请检查表达式格式。"

# ========== 工具注册表 ==========
tool_map = {
    "get_weather": get_weather,
    "calculate": calculate,
}

# ========== Agent 核心逻辑 ==========
def run_agent(user_input: str, max_iterations: int = 5):
    """完整的 Function Calling Agent"""
    messages = [
        {"role": "system", "content": "你是一个有用的助手，可以查询天气和做数学计算。根据用户需求灵活使用工具。"},
        {"role": "user", "content": user_input}
    ]

    print(f"\n{'='*60}")
    print(f"用户: {user_input}")
    print(f"{'='*60}")

    for i in range(max_iterations):
        # 调用模型
        response = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=messages,
            tools=tools,
        )
        msg = response.choices[0].message

        # 没有工具调用 → 最终回答
        if not msg.tool_calls:
            print(f"\n[Agent] 经过 {i + 1} 轮后给出最终回答")
            print(f"助手: {msg.content}")
            return msg.content

        # 有工具调用 → 执行工具
        messages.append(msg)  # ⚠️ 先追加 assistant 消息！

        for tc in msg.tool_calls:
            fn_name = tc.function.name
            fn_args_str = tc.function.arguments
            print(f"\n  [第 {i+1} 轮] 调用工具: {fn_name}")
            print(f"           参数: {fn_args_str}")

            # 通过注册表执行工具
            if fn_name in tool_map:
                try:
                    fn_args = json.loads(fn_args_str)
                    result = tool_map[fn_name](**fn_args)
                except Exception as e:
                    result = f"工具执行出错: {e}"
            else:
                result = f"未知工具: {fn_name}"

            print(f"           结果: {result}")

            # 追加 tool message
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": str(result)
            })

    return "达到最大迭代次数，Agent 停止。"
```

来跑三个测试用例：

```python
# 测试 1：单工具调用
run_agent("北京今天天气怎么样？")

# 测试 2：另一个工具
run_agent("帮我算一下 (100 + 200) * 3 - 50")

# 测试 3：多步推理 — 这个最有趣！
run_agent("上海天气怎么样？如果温度超过30度，帮我算一下实际温度和30度差多少。")
```

测试 3 是最有意思的，因为它需要**两轮工具调用**：

```text
============================================================
用户: 上海天气怎么样？如果温度超过30度，帮我算一下实际温度和30度差多少。
============================================================

  [第 1 轮] 调用工具: get_weather
           参数: {"city": "上海"}
           结果: 多云, 32°C, 湿度 78%

  [第 2 轮] 调用工具: calculate
           参数: {"expression": "32 - 30"}
           结果: 2

[Agent] 经过 3 轮后给出最终回答
助手: 上海今天多云，气温32°C，湿度78%。温度超过了30°C，实际温度比30°C高了2°C。
```

看到了吗？

1. 第 1 轮：模型调了 `get_weather`，拿到了上海 32°C
2. 第 2 轮：模型看到 32 > 30，于是调了 `calculate` 算差值
3. 第 3 轮：模型整合两次工具结果，给出最终回答

**模型自己做了判断和决策。** 它看到了天气结果，自己判断"哦，32 > 30，用户说要算差值"，然后主动调了计算器。这就是 Agent 和普通 Chatbot 的区别——它不只是回答问题，它在**执行任务**。

---

## 七、回头看 — 这就是 Agent Loop

写完这段代码，回头看上周 D6 文章里的那段伪代码：

```python
while not done:
    response = call_llm(messages)       # 调 LLM
    if response.has_tool_calls:         # 有工具调用？
        results = execute_tools(        #   执行工具
            response.tool_calls
        )
        messages.append(results)        #   结果塞回消息列表
    else:                               # 没有工具调用？
        done = True                     #   循环结束
        return response                 #   返回最终回复
```

和今天 `run_agent` 里的 for 循环对比一下——**一模一样。**

上周那个是骨架，今天这个是有血有肉的版本。区别只是：
- 工具定义用了 JSON Schema
- 消息格式用了 OpenAI 的 tool_call / tool message 格式
- 加了工具注册表和错误处理

**Agent 的心脏就是这个循环。Function Calling 就是循环里的核心能力——让 LLM 能"长出手脚"做事。** 所有框架（LangChain、LangGraph、OpenAI Agents SDK）都只是在这个循环外面包了不同的壳。

---

## 小结

回顾一下今天搞明白的几件事：

1. **工具调用是一个多轮对话** — 不是一次请求就完事。完整流程是：发请求 → 收到 tool_call → 执行工具 → 把结果以 tool message 返回 → 模型给出最终回答（或继续调工具）
2. **消息顺序至关重要** — 必须**先追加 assistant 消息**（包含 tool_calls），**再追加 tool 结果**。搞反了就报错，而且错误信息根本看不出是顺序问题
3. **tool_call_id 是桥梁** — 每个 tool message 必须通过 `tool_call_id` 和对应的 tool_call 关联。并行调用时，每个结果都要对应自己的 id
4. **工具返回值必须是字符串** — dict 要 `json.dumps`，None 要返回 `"success"` 之类的有意义文本
5. **多工具管理用注册表模式** — `tool_map = {"name": func}` 的映射，干净且可扩展
6. **错误信息要对模型友好** — 返回可操作的错误描述（"请使用 '北京' 而非 '北京市'"），不要返回 traceback。错误信息就是给模型的"提示词"
7. **工具命名要有一致前缀** — `browser_xxx`、`shell_xxx`，帮助模型分组理解。这是 Manus 和 Anthropic 都验证过的经验
8. **今天的代码就是 Agent Loop 的血肉版** — 上周写的伪代码骨架，今天用 Function Calling 填满了。所有 Agent 框架的底层都是这个循环

一条可带走的经验：**Function Calling 的完整流程本身不难，但魔鬼在细节里——消息顺序、id 关联、返回值类型、错误处理——每个都能让你卡半天。把今天这个 `run_agent` 函数吃透了，后面不管用什么框架都只是在它外面加壳。**

> 💡 **预告**：到今天为止，我们已经有了一个能用多个工具完成多步任务的 Agent。但你可能发现了——模型的"思考过程"我们看不到，它在黑盒里做决策。明天我们进入 **ReAct 模式**——Thought → Action → Observation 循环。ReAct 的核心思想是让模型"边想边做"，每一步都先说出自己的推理过程，然后再决定行动。把今天学的 Function Calling 融入 ReAct 框架，Agent 就不只是"调工具"，而是"有推理过程地调工具"了。
