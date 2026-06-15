

---

> 摘要：昨天 D14 我们搞清楚了 LangChain 是什么、生态怎么分工、`create_agent` 怎么用。但一直在"看地图"，没真正下手写代码。今天 D15 要把 LangChain 最核心的三个组件**一个一个拆透**：**ChatModel**（统一模型接口）、**Messages**（LLM 对话的基本单元）、**LCEL**（管道符 `|` 串一切）。读完之后你会理解一次完整的工具调用消息流（Human → AI → Tool → AI），并且写出 `chain = model | parser` 这样的声明式管道。这是后面 Tool Agent、Memory、RAG 所有内容的工程基础。

---

## 一、ChatModel——"统一接口"的代价与收益

### 1.1 同一段意思，三种写法

第二周我们用裸 SDK 这样调用：

```python
from openai import OpenAI

client = OpenAI(api_key=..., base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")

resp = client.chat.completions.create(
    model="qwen3.5-flash",
    messages=[
        {"role": "system", "content": "你是一个翻译助手"},
        {"role": "user", "content": "把'Agent 是 LLM 的应用形态'翻成英文"},
    ],
)
print(resp.choices[0].message.content)
```

换成 LangChain 同样的事，是这样：

```python
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

model = ChatOpenAI(
    model="qwen3.5-flash",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    # api_key 走 OPENAI_API_KEY 环境变量
)

ai = model.invoke([
    SystemMessage("你是一个翻译助手"),
    HumanMessage("把'Agent 是 LLM 的应用形态'翻成英文"),
])
print(ai.content)
```

上面是**直接实例化具体类**的写法——类型提示好、IDE 补全强，适合你明确知道用哪家。

但 LangChain 官方现在更推荐另一种姿势——**工厂函数** `init_chat_model`：

```python
from langchain.chat_models import init_chat_model

model = init_chat_model(
    "qwen3.5-flash",
    model_provider="openai",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)
```

返回的对象和 `ChatOpenAI(...)` 完全一样，区别在于：**provider 是一个字符串参数，不是 import 路径**。

这意味着切换 Anthropic 时，连 `import` 都不用改：

```python
# 之前（直接实例化）：要换 import + 换类名
from langchain_anthropic import ChatAnthropic
model = ChatAnthropic(model="claude-sonnet-4-6")

# 现在（工厂函数）：只改字符串
model = init_chat_model("claude-sonnet-4-6", model_provider="anthropic")
# 下面所有 model.invoke(...) 都不用动
```

甚至可以直接写成 `{provider}:{model}` 前缀格式，一行搞定：

```python
model = init_chat_model("anthropic:claude-sonnet-4-6")
```

**两种姿势怎么选？**

| | `init_chat_model`（工厂函数，官方推荐） | `ChatOpenAI(...)`（直接实例化） |
| --- | --- | --- |
| **切换 provider** | 改字符串，不用动 import | 要换 import + 换类名 |
| **IDE 补全** | 差一些（返回基类类型） | 好（具体类参数全有提示） |
| **适用场景** | 配置驱动、运行时切换模型 | 明确用哪家、开发时求类型安全 |

这就是"统一接口"在工程上的真实收益——**模型供应商被你抽象掉了**，而 `init_chat_model` 把这个抽象做得更彻底。

### 1.2 不是没有代价——三个你要心里有数的"漏洞"

凡是抽象层，都会漏。LangChain 的 ChatModel 也漏。我列三个最常被人吐槽的：

1. **新参数滞后**：某厂商出了个新参数（比如 `reasoning_effort`），LangChain 的 wrapper 没跟上时，你只能走 `model_kwargs={"reasoning_effort": "high"}` 透传——绕过了类型检查。
2. **流式细节差异**：不同厂商流的 chunk 粒度、什么时候 emit `tool_call_chunks` 是不一样的，LangChain 帮你磨平到一定程度，但极致优化场景你仍然要看具体 provider。
3. **错误信息变长**：抽象多了一层，traceback 也多了一层，刚开始 debug 会觉得"怎么这么深"。

**结论**：抽象不是免费午餐。但对绝大多数应用来说——这点代价远低于自己手写厂商适配的成本。

---

## 二、Messages——LLM 对话的"细胞"

### 2.1 Message 的三要素：Role + Content + Metadata

第一节里你已经见过 `SystemMessage("...")` 和 `HumanMessage("...")`，但没细讲它们是什么。这一节拆透。

每条 Message 都由三部分构成：

| 要素 | 干什么 | 例子 |
| --- | --- | --- |
| **Role** | 这条消息是谁说的 | `system` / `user` / `assistant` / `tool` |
| **Content** | 实际内容 | 文本、图片、音频、工具调用…… |
| **Metadata** | 附加信息 | token 用量、消息 ID、厂商响应头 |

LangChain 用四种 Message 类型对应四种角色：

| 类 | Role | 谁产生的 | 一句话 |
| --- | --- | --- | --- |
| `SystemMessage` | system | 你写的 | 设定人设、规则、约束 |
| `HumanMessage` | user | 用户发的 | 用户输入 |
| `AIMessage` | assistant | 模型返回的 | 模型回复（**不只是文字**） |
| `ToolMessage` | tool | 工具执行的 | 工具调用结果回传 |

裸 SDK 里你写 `{"role": "user", "content": "..."}`，LangChain 里写 `HumanMessage("...")`。表面是换了个写法，实质上是**把消息从"一个 dict"升级成了"有类型、有属性、能携带结构化数据的对象"**。

下面重点拆两个最关键的——`AIMessage` 和 `ToolMessage`。`SystemMessage` 和 `HumanMessage` 太简单（基本就是 content 字符串），不用花时间。

### 2.2 AIMessage——模型返回的"百宝箱"

`model.invoke(...)` 返回的就是一个 `AIMessage`。新手只看 `.content`，但这个对象其实塞了很多东西：

```python
ai = model.invoke([HumanMessage("你好")])

ai.text               # "你好！有什么可以帮你的？"——纯文本，最常用
ai.content            # 同上，原始格式（可能包含多模态内容块）
ai.content_blocks     # 标准化内容块列表（text / reasoning / image ...）
ai.tool_calls         # 模型发起的工具调用列表（没调工具时为 [] 或 None）
ai.usage_metadata     # token用量{"input_tokens":8, "output_tokens":33, ...}
ai.response_metadata  # 厂商原始响应信息（model_name、finish_reason 等）
ai.id                 # 消息唯一 ID
```

**最需要关注的是 `tool_calls`**。当模型决定调用工具时，它不会直接输出文字，而是在 `AIMessage.tool_calls` 里放一个列表：

```python
# 模型决定调用 get_weather 工具
ai = model_with_tools.invoke([HumanMessage("北京天气怎么样？")])

print(ai.content)        # ""（空！模型没输出文字）
print(ai.tool_calls)
# [{
#     "name": "get_weather",         # 调哪个工具
#     "args": {"location": "北京"},   # 参数
#     "id": "call_abc123",           # 调用 ID——ToolMessage 要用它来配对
# }]
```

**这是整个 Tool Agent 机制的核心**：模型的"决策"不在 `.content` 里，在 `.tool_calls` 里。后面 D16 的所有内容都围绕这个字段展开。

另一个实用的属性是 `usage_metadata`——token 计费就靠它：

```python
ai.usage_metadata
# {'input_tokens': 8, 'output_tokens': 304, 'total_tokens': 312}
```

### 2.3 ToolMessage——工具执行结果的"回信"

模型在 `AIMessage.tool_calls` 里说"我要调 `get_weather`"，但你得真的去执行这个函数，然后把结果**塞回对话**让模型继续推理。`ToolMessage` 就是这个"塞回对话"的载体。

它有两个必填字段：

| 字段 | 干什么 |
| --- | --- |
| `content` | 工具执行的结果（字符串） |
| `tool_call_id` | **必须匹配** `AIMessage.tool_calls` 里的 `id` |

`tool_call_id` 是配对的钥匙——模型发出 `call_abc123`，你的 `ToolMessage` 必须带着 `tool_call_id="call_abc123"` 回来，模型才知道"这是那个调用的结果"。

```python
from langchain.messages import ToolMessage

tool_message = ToolMessage(
    content="北京今天 28°C，晴",     # 工具执行结果
    tool_call_id="call_abc123",       # 对应上面 AIMessage 里的 id
    name="get_weather",               # 工具名
)
```

`ToolMessage` 还有个可选字段 `artifact`——**存给程序用、不给模型看的数据**。比如 RAG 检索时，`content` 放给模型看的文本片段，`artifact` 放文档 ID、页码等元信息：

```python
tool_message = ToolMessage(
    content="It was the best of times...",      # 给模型看的
    tool_call_id="call_456",
    name="search_docs",
    artifact={"document_id": "doc_123", "page": 0},  # 给程序用的
)
```

### 2.4 完整消息流——一次工具调用，四条消息

把三种 Message 串起来看一遍完整的工具调用流程：

```python
from langchain.messages import HumanMessage, AIMessage, ToolMessage

messages = []

# 1️⃣ 用户提问
messages.append(HumanMessage("北京天气怎么样？"))

# 2️⃣ 模型决定调工具（AIMessage.tool_calls 不为空）
ai_msg = model_with_tools.invoke(messages)
messages.append(ai_msg)
# ai_msg.tool_calls = [{"name": "get_weather", "args": {"location": "北京"}, "id": "call_abc123"}]

# 3️⃣ 你执行工具，把结果包成 ToolMessage 塞回去
result = get_weather("北京")  # → "28°C，晴"
messages.append(ToolMessage(
    content=result,
    tool_call_id="call_abc123",
    name="get_weather",
))

# 4️⃣ 模型拿到结果，生成最终回复
final = model_with_tools.invoke(messages)
print(final.text)  # "北京今天 28°C，晴朗。"
```

![](https://limbo.oss-cn-beijing.aliyuncs.com/wiki/20260614113912930.png)

---

## 三、LCEL——用管道符 `|` 把三件事串成一行

### 3.1 "手工胶水"有多碍眼？

把前两节的内容拼在一起，你会写出这样的代码：

```python
messages = [SystemMessage("你是技术助理"), HumanMessage(q)]
ai = model.invoke(messages)
return ai.text
```

两行"手工胶水"——手动拼消息列表、手动取 `.text`。链一长就更难受：加个 parser 要手动传，加个重试要自己包，加个 fallback 要自己 if-else。**LCEL（LangChain Expression Language）的存在，就是把这些胶水全部干掉**。

### 3.2 管道符 `|` 的本质——Runnable 协议

`|` 不是 Python 的黑魔法运算符重载，它的本质是：**所有 LangChain 组件都实现了 `Runnable` 接口，`|` 就是把上一个的输出喂给下一个**。

最简单的链——`model | parser`：

```python
from langchain_core.output_parsers import StrOutputParser

chain = model | StrOutputParser()

result = chain.invoke("LangChain 是什么？")
# 等价于：StrOutputParser().invoke(model.invoke("LangChain 是什么？"))
```

`model` 吃进字符串（自动包成 `HumanMessage`），吐出 `AIMessage`；`StrOutputParser` 吃进 `AIMessage`，吐出 `str`。`|` 就是把前者吐的喂给后者吃的**胶水**。

如果中间要加一步"构建消息"，用 `RunnableLambda` 把普通函数包成 Runnable：

```python
from langchain_core.runnables import RunnableLambda

build_messages = RunnableLambda(lambda q: [
    SystemMessage("你是技术助理"),
    HumanMessage(q),
])

chain = build_messages | model | StrOutputParser()
chain.invoke("LangChain 是什么？")
```

**LCEL 帮你省掉了中间的类型转换和手动传递**。

### 3.3 Runnable 接口的完整能力

`|` 串起来的 chain，自动获得 Runnable 的全部能力：

| 能力 | 说明 |
| --- | --- |
| `chain.invoke(...)` | 同步执行 |
| `chain.stream(...)` | 流式执行——打字机效果 |
| `chain.batch([...])` | 批量执行 |
| `chain.ainvoke / astream / abatch` | 异步版本 |
| `.with_config(...)` | 传入运行时配置（如 tags、metadata） |
| `.with_retry(...)` | 自动重试 |
| `.with_fallbacks([...])` | 降级链 |

这意味着你不用为每种执行方式重写一遍逻辑——**一条 chain 自动拥有所有执行模式**。

### 3.4 OutputParser——结果解析这一格

上面的 `StrOutputParser()` 是最简单的 parser，只做一件事：把 `AIMessage` 的 `.content` 提取出来变成字符串。

实际工程中常用的还有：

| Parser | 干什么 |
| --- | --- |
| `StrOutputParser` | `AIMessage → str` |
| `JsonOutputParser` | `AIMessage → dict`（要求 LLM 输出 JSON）|
| `PydanticOutputParser` | `AIMessage → Pydantic Model`（带 schema 校验）|
| `CommaSeparatedListOutputParser` | `AIMessage → list[str]` |

### 3.5 完整示例——三件套一次性打通

```python
from langchain.chat_models import init_chat_model
from langchain.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda

model = init_chat_model(
    "qwen3.5-flash",
    model_provider="openai",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    temperature=0.3,
)

SYSTEM = SystemMessage("你是一个简洁的技术助理，回答不超过 30 字。")
history: list = []

def build_messages(q: str) -> list:
    return [SYSTEM] + history + [HumanMessage(q)]

chain = RunnableLambda(build_messages) | model | StrOutputParser()

def ask(q: str) -> str:
    answer = chain.invoke(q)
    history.extend([HumanMessage(q), AIMessage(answer)])
    return answer

print(ask("LangChain 最大的价值是什么？"))
print(ask("展开说一下'契约'的部分。"))
print(ask("我前面问了几个问题？"))
```

对比不用 LCEL 的版本（手工胶水）：

```python
def ask(q: str) -> str:
    messages = [SYSTEM] + history + [HumanMessage(q)]
    ai = model.invoke(messages)
    history.extend([HumanMessage(q), AIMessage(ai.text)])
    return ai.text
```

**区别只有两行**，但这个差距会随着链变长（加 parser、加 fallback、加 retry）急剧放大。LCEL 的价值不在 3 步链，而在 10 步链。

---

## 四、回头看——D15 最值得记住的三件事

| 组件 | 一句话本质 | 替你解决的痛点 |
| --- | --- | --- |
| **ChatModel** | 一组**统一的 Runnable 接口**包住所有厂商 | 模型可替换、并发可批处理 |
| **Messages** | LLM 对话的**基本单元**，Role + Content + Metadata | 消息可类型化、`tool_calls` 可标准化、多轮可累积 |
| **LCEL** | 用 `|` 把所有 Runnable **串成声明式管道** | 干掉手工胶水，一条链自动获得 stream/batch/retry |

而这三件事的背后，是 LangChain 整个框架的设计哲学——

> **抽象 LLM 应用里"能稳定下来的东西"，把"易变的东西"留给你配置。**
>
> 模型谁家、消息怎么拼、工具用哪些、检索怎么做——这些是易变的；
> 但 "调一次模型 / 构造一组 Message / 解析一段输出" 这三类动作的接口形状——是能标准化的。

---

## 五、踩坑清单

1. **`AIMessage.text` vs `.content`**：`.text` 是纯文本快捷方式，`.content` 是原始格式（多模态场景下是列表，不一定是字符串）。
2. **`tool_calls` 为空时不报错**：模型不调工具时 `ai.tool_calls` 是 `[]`，要先判断再遍历。
3. **`ToolMessage` 的 `tool_call_id` 必须严格匹配**：和 `AIMessage.tool_calls` 里的 `id` 一一对应，否则模型会"懵"——不知道这个结果对应哪个调用。
4. **不要一上来就 `create_agent`**：先把 ChatModel + Messages + LCEL 这一层吃透，后面的 Tool Agent 和 Memory 才不会觉得"框架是黑魔法"。
5. **`|` 不是奇技淫巧**：它的本质是 Runnable 协议，`a | b` 等价于"把 a 的输出喂给 b"。
6. **LCEL 的价值不在 3 步链，而在 10 步链**：3 步时手工胶水还行，10 步时 LCEL 的 `with_retry / with_fallbacks / batch` 自动能力就是救命的。

---

## 六、下一步：D16 给 Agent 装上工具

今天的三件套（ChatModel + Messages + LCEL）拼出了一个**能聊天、能管理对话状态、能管道化**的 chain。但它还不能"做事"——不能调 API、不能查数据库、不能发邮件。

明天 D16 要做的事：用 `bind_tools` 给 ChatModel 装上工具，让 chain 从"只会聊天"进化成"会调工具的 Agent"。

我们明天见。

---

## 参考与延伸

- LangChain 官方文档 — `Concepts` → `Chat Models` / `Messages` / `LCEL`
- 第二周 D8-D13 笔记 — ChatModel 解决的"模型可替换"问题，对应你第二周手写 SDK 的痛
- D14 笔记 — LangChain 是什么、生态分工、create_agent 快速入门
- 第三周后续：D16（Tool Agent）→ D17（Memory）→ D18-19（RAG）—— 一切都建立在今天这三件套上
