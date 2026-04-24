# Function Calling：让模型从"只会说"到"能动手"的关键一步

---

> 摘要：上周我们搞明白了 Agent 的心脏是一个 while 循环，也知道了循环里最关键的一步是"调用工具"。但工具调用到底是怎么发生的？模型怎么知道该调哪个工具？参数从哪来？这篇从我自己的一个尴尬经历出发，搞清楚 Function Calling（Tool Use）的核心机制——工具定义怎么写、好的描述 vs 烂的描述、模型选择工具的原理、以及 tool_choice 参数的用法。搞懂这些，你才能真正让模型"长出手脚"。

## 一、LLM 为什么需要"长手脚"

![](https://limbo.oss-cn-beijing.aliyuncs.com/wiki/ChatGPT%20Image%202026%E5%B9%B44%E6%9C%8822%E6%97%A5%2015_44_18.png)

Martin Fowler 有一句话说得特别到位：

> "LLM 本身不执行函数。相反，它识别合适的函数，收集所有必需的参数，并以结构化的 JSON 格式提供这些信息。"

这句话值得反复读三遍。**模型不是在"调用"函数，它只是在"告诉你"它想调哪个函数、传什么参数。真正执行函数的是你的代码。**

顺便理清一下几个容易混淆的术语：

| 术语 | 来源 | 含义 |
|------|------|------|
| **Function Calling** | OpenAI 最早使用 | 模型生成结构化的函数调用请求 |
| **Tool Use** | Anthropic 使用 | 和 Function Calling 本质一样，只是叫法不同 |
| **MCP** | Anthropic 提出 | 模型上下文协议（Model Context Protocol），是工具的标准化**连接方式**，解决的是工具怎么接入的问题 |

简单记：**Function Calling ≈ Tool Use**（只是不同厂商的叫法），**MCP** 是另一个层面的东西——它不是工具调用本身，而是让工具以统一的方式被发现和使用的协议。后面我们会单独讲 MCP，今天先聚焦 Function Calling 本身。

---

## 二、工具定义 — JSON Schema 怎么写

知道了 Function Calling 是什么之后，下一个问题是：**怎么告诉模型"你有哪些工具可用"？**

答案是 **JSON Schema**。你需要用一个标准化的 JSON 格式来描述每一个工具的名称、用途和参数。

![](https://limbo.oss-cn-beijing.aliyuncs.com/wiki/ChatGPT%20Image%202026%E5%B9%B44%E6%9C%8822%E6%97%A5%2016_56_17.png)

来看一个最经典的例子——查天气：

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定城市的当前天气信息，包括温度、天气状况等",
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
    }
]
```


---

## 三、踩坑重灾区 — 工具描述写得烂，模型就选错

这是我在学 Function Calling 过程中踩得最疼的坑，值得单独拿出来讲。

**反面教材：**

```python
{
    "name": "search",
    "description": "搜索",
    "parameters": {
        "type": "object",
        "properties": {
            "q": {"type": "string"}
        }
    }
}
```

这个工具定义有多烂？来数数：

1. `name` 叫 `search` —— 搜什么？商品？文章？用户？
2. `description` 写了个"搜索" —— 等于没写
3. 参数名叫 `q` —— 模型猜不出这是什么
4. 参数没有 `description` —— 模型完全不知道该传什么



**正面教材：**

```python
{
    "name": "search_products",
    "description": "根据关键词搜索商品，返回匹配的商品列表（最多10条）。当用户询问商品、想要购物或查找特定产品时使用此工具。",
    "parameters": {
        "type": "object",
        "properties": {
            "keywords": {
                "type": "array",
                "items": {"type": "string"},
                "description": "搜索关键词列表，例如 ['红色', '连衣裙']"
            },
            "max_results": {
                "type": "integer",
                "description": "返回结果数量上限，默认为10",
                "default": 10
            }
        },
        "required": ["keywords"]
    }
}
```

区别一目了然。我整理了一个对比表，以后写工具定义的时候可以对照着检查：

| 维度 | ❌ 烂的做法 | ✅ 好的做法 |
|------|-----------|-----------|
| **名称** | `search`、`func1`、`do_stuff` | `search_products`、`get_weather`、`send_email` |
| **描述** | "搜索"、"处理数据" | "根据关键词搜索商品列表。当用户想购物或查找产品时使用" |
| **参数名** | `q`、`a`、`data` | `keywords`、`city`、`email_address` |
| **参数描述** | 不写 | "城市名称，例如 '北京'、'上海'" |
| **示例** | 不给 | 在描述中给出示例值 |
| **使用场景** | 不说明 | "当用户询问天气时使用此工具" |

这不是我瞎总结的。OpenAI 官方文档里给了几条最佳实践，我觉得特别实用：

1. **写清楚、详细的函数名和参数描述** —— 模型全靠这些文字来理解工具
2. **让函数的用途直观明显** —— 不要让模型去"猜"
3. **参数值如果是有限集合，用 enum** —— 比如 `"enum": ["celsius", "fahrenheit"]`
4. **初始可用工具数量控制在 20 个以内** —— 工具太多模型会懵，准确率下降
5. **经常连续调用的工具，考虑合并成一个** —— 减少模型的决策负担

第 5 条特别有意思。Anthropic 在他们的文档里也提了类似的建议：

> "与其分别实现 `list_users`、`list_events` 和 `create_event` 三个工具，不如考虑实现一个 `schedule_event` 工具，它内部自动查找可用时间并创建事件。"

说白了就是：**不要让模型替你编排工具。** 如果两个工具总是一起用，就合并成一个，让代码逻辑来处理内部的调用顺序。

还有一个来自 Manus 团队（就是那个刷屏的 AI Agent 产品）的经验，也很有参考价值：

> "除非绝对必要，避免在迭代过程中动态添加或删除工具。"

他们还提到了一个工具命名规范：用前缀来分组，比如 `browser_navigate`、`browser_click`、`shell_exec`。这样模型一看名字就知道这组工具是干嘛的，选择起来更准确。

---

## 四、模型是怎么"选"工具的

搞清楚了工具定义怎么写之后，一个自然的问题是：**模型到底是怎么决定用哪个工具的？**

这里有个容易产生的误解——觉得模型"理解"了工具的功能然后做了一个智能决策。其实没那么神秘。

**本质上，模型是在做 token 预测。** 它看到了用户的输入、工具的定义（name + description + parameters），然后根据训练数据中学到的模式，生成一段结构化的 JSON 输出——里面包含要调用的工具名和参数值。

这个过程能成立，是因为模型在训练（或微调）阶段见过大量"用户意图 → 工具调用"的配对数据。所以当你写了一个好的工具描述，模型就更容易把用户意图"匹配"到正确的工具上。

**这也是为什么工具描述那么重要——它本质上是在帮模型做"意图匹配"。**

### tool_choice：控制模型的工具调用行为

OpenAI 提供了一个 `tool_choice` 参数，让你可以控制模型在什么程度上使用工具：

| 值                                                   | 含义           | 适用场景                      |
| --------------------------------------------------- | ------------ | ------------------------- |
| `"auto"`（默认）                                        | 模型自己决定是否调用工具 | 大多数场景，模型觉得需要就调，不需要就直接回答   |
| `"required"`                                        | 必须调用至少一个工具   | 你确定这个请求一定需要工具，不想让模型偷懒直接回答 |
| `"none"`                                            | 禁止调用工具       | 你只想要文本回复，不想触发任何工具         |
| `{"type": "function", "function": {"name": "xxx"}}` | 强制调用指定工具     | 你明确知道要用哪个工具，不想让模型自己选      |

大部分时候用 `auto` 就行。但有些场景下你需要精确控制——比如你做了一个"每日天气推送"功能，那就应该用 `required` 或者指定 `get_weather`，不然模型可能觉得"用户没问天气啊"就不调了。

### 并行工具调用

还有一个挺酷的特性：**模型可以在一次回复中返回多个 tool_calls。**

比如用户说："帮我查一下巴黎和东京的天气。"

模型不会先查巴黎、等结果、再查东京。它会**一次性返回两个 tool_calls**：

```json
{
  "tool_calls": [
    {
      "id": "call_1",
      "function": {
        "name": "get_weather",
        "arguments": "{\"city\": \"巴黎\"}"
      }
    },
    {
      "id": "call_2",
      "function": {
        "name": "get_weather",
        "arguments": "{\"city\": \"东京\"}"
      }
    }
  ]
}
```

你的代码拿到这两个调用后，可以**并行执行**它们——两个 API 请求同时发出去，等都返回了再把结果一起塞回消息列表。这样一来，两次工具调用的总耗时就是"最慢那个"的耗时，而不是两个加起来。

在代码里处理并行工具调用其实不难，关键是你的执行逻辑要支持——遍历所有 `tool_calls`，对每个都执行并收集结果：

```python
if msg.tool_calls:
    messages.append(msg)  # 先追加 assistant 消息
    for tc in msg.tool_calls:
        result = execute_tool(tc.function.name, tc.function.arguments)
        messages.append({
            "role": "tool",
            "tool_call_id": tc.id,
            "content": str(result)
        })
```

---

## 五、strict mode — 让工具调用更可靠

顺带提一个 OpenAI 提供的小功能：**strict mode**。

在工具定义里加上 `"strict": true`，模型的输出就**保证**符合你定义的 JSON Schema——不会多字段、不会少字段、不会类型错误。

```python
{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "查询指定城市的当前天气信息",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "城市名称"}
            },
            "required": ["city"],
            "additionalProperties": False  # strict mode 要求
        },
        "strict": True  # 开启严格模式
    }
}
```

开启 strict mode 有两个硬性要求：

1. **`additionalProperties` 必须设为 `false`** —— 不允许模型自由发挥加字段
2. **所有字段都要放在 `required` 里** —— 不允许有可选字段

代价是灵活性降低了一点，但好处是你的代码不用再做防御性的 JSON 解析了——模型输出一定是合规的。在生产环境中这个特性挺有用的，省得你写一堆 `try/except` 来处理模型输出的奇奇怪怪的 JSON。

---


## 小结

回顾一下今天搞明白的几件事：

1. **LLM 有三大天生缺陷** — 无法获取实时数据、无法精确计算、无法操作外部系统。Function Calling 就是给它补上这些能力的机制
2. **Function Calling 不是 LLM 在"执行"函数** — 它只是生成结构化的 JSON（工具名 + 参数），真正执行函数的是你的代码。Martin Fowler 那句话要记住
3. **工具描述是最容易踩坑的地方** — 描述写得好不好，直接决定模型能不能选对工具。名称要清晰、描述要详细、参数要有说明和示例
4. **OpenAI 建议初始工具数量控制在 20 个以内** — 工具太多，模型的"选择困难症"就会发作，准确率下降
5. **tool_choice 控制模型的工具调用行为** — `auto` 让模型自己判断，`required` 强制使用工具，`none` 禁止使用工具，还能指定具体工具
6. **模型可以并行调用多个工具** — 一次返回多个 tool_calls，你的代码可以同时执行它们，节省时间
7. **Anthropic 建议合并经常连续调用的工具** — 不要让模型替你编排工具，把编排逻辑放在代码里
8. **strict mode 让工具调用的输出更可靠** — 开启后模型输出保证符合 JSON Schema，代价是灵活性略低

一条可带走的经验：**写工具描述的时候，假装你在给一个聪明但啥也不懂的实习生写操作手册——名字要一看就懂，描述要说清楚什么时候用、参数要举例子。模型选错工具，90% 的原因是你的描述没写好。**

> 💡 **预告**：今天我们只做了 Function Calling 的"上半场"——模型告诉我们它想调什么工具。但真正的工具调用是一个完整的闭环：模型发出 tool_call → 你执行工具 → 把结果以 tool message 返回给模型 → 模型基于结果继续推理。明天 Day 9 我们就来走通这个完整流程，并且探索多工具编排的技巧——当一个任务需要调用好几个工具时，怎么让它们配合得更好。
