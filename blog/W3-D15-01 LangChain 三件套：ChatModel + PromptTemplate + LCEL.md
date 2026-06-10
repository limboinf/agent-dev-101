# LangChain 三件套：ChatModel + PromptTemplate + LCEL，把"手工胶水"全部干掉

---

> 摘要：昨天 D14 我们搞清楚了 LangChain 是什么、生态怎么分工、`create_agent` 怎么用。但一直在"看地图"，没真正下手写代码。今天 D15 要把 LangChain 最核心的三个组件**一个一个拆透**：**ChatModel**（统一模型接口）、**PromptTemplate**（把 Prompt 当数据管）、**LCEL**（管道符 `|` 串一切）。读完之后你会写出一行 `chain = prompt | model | parser` 并且**完全理解它的每一层在干什么**。这是后面 Tool Agent、Memory、RAG 所有内容的工程基础。

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

如果哪天换 Anthropic，业务代码里**只改一行**：

```python
from langchain_anthropic import ChatAnthropic
model = ChatAnthropic(model="claude-3-5-sonnet-latest")
# 下面所有 model.invoke(...) 都不用动
```

这就是"统一接口"在工程上的真实收益——**模型供应商被你抽象掉了**。

### 1.2 ChatModel 的"五件套"接口——一定要记住

所有 ChatModel 都实现了 `Runnable` 接口。`Runnable` 这个名字先按下不表（第三节 LCEL 详谈），你只要知道**它强制每个组件都暴露这五个方法**：

| 方法 | 干什么 | 返回 | 一句话场景 |
| --- | --- | --- | --- |
| `invoke(input)` | 同步调一次 | `AIMessage` | 最常用 |
| `stream(input)` | 同步流式 | 迭代器，每个元素是 `AIMessageChunk` | 终端打字机效果 |
| `batch([inputs])` | 同步批量 | `list[AIMessage]` | 一次跑 100 条数据 |
| `ainvoke / astream / abatch` | 上面三个的 async 版 | 同上 | FastAPI / 服务端高并发 |
| `bind_tools(tools)` | 把工具绑到模型上 | 一个新的 Runnable | Function Calling |

这五件套的存在意义在于：**只要你写的代码用的是这五个方法之一，它就和"模型是谁"完全解耦**。

来个并发批处理的小例子，体会一下"统一接口"带来的工程便利：

```python
prompts = [
    [HumanMessage("一句话解释 Token")],
    [HumanMessage("一句话解释 Embedding")],
    [HumanMessage("一句话解释 Function Calling")],
]

# 一次性把 3 个请求并发出去，框架内部帮你管协程池
results = model.batch(prompts, config={"max_concurrency": 3})
for r in results:
    print("-", r.content)
```

裸 SDK 写这个东西，至少要 20 行 `asyncio.gather`、还得自己处理速率限制和异常聚合。

### 1.3 消息对象 vs 裸 dict——一个长得像奇技淫巧、实则非常关键的设计

裸 SDK 里我们传 `{"role": "user", "content": "..."}`，LangChain 里传 `HumanMessage("...")`。

第一眼看：**多此一举**。

但你认真想想，这两种东西是有本质区别的：

| 维度 | 裸 dict | Message 对象 |
| --- | --- | --- |
| **类型安全** | 字段名敲错也跑得起来，运行时才崩 | IDE 直接补全，错一个字段编辑器就标红 |
| **序列化** | 各家厂商格式不一样（OpenAI 的 tool_call_id vs Anthropic 的 stop_reason）| 框架替你转换成目标厂商的格式 |
| **可扩展** | 加个字段全代码改 | `HumanMessage(name=..., additional_kwargs=...)` 内置好了 |
| **可遍历** | 你得肉眼分辨 role | `isinstance(msg, AIMessage)` 一眼出 |

最重要的一条是**序列化**。Anthropic 的 Tool Call 长这样：

```python
{"type": "tool_use", "id": "toolu_01...", "name": "get_weather", "input": {...}}
```

OpenAI 长这样：

```python
{"role": "assistant", "tool_calls": [{"id": "call_...", "function": {...}}]}
```

如果你写裸 SDK 想兼容两家——欢迎陷入"格式转换地狱"。LangChain 做的事是：**所有厂商的工具调用，无论原生格式怎么丑，统一在 `AIMessage.tool_calls` 这个标准字段里给你**。这是它能"模型可替换"最关键的一块拼图。

### 1.4 不是没有代价——三个你要心里有数的"漏洞"

凡是抽象层，都会漏。LangChain 的 ChatModel 也漏。我列三个最常被人吐槽的：

1. **新参数滞后**：某厂商出了个新参数（比如 `reasoning_effort`），LangChain 的 wrapper 没跟上时，你只能走 `model_kwargs={"reasoning_effort": "high"}` 透传——绕过了类型检查。
2. **流式细节差异**：不同厂商流的 chunk 粒度、什么时候 emit `tool_call_chunks` 是不一样的，LangChain 帮你磨平到一定程度，但极致优化场景你仍然要看具体 provider。
3. **错误信息变长**：抽象多了一层，traceback 也多了一层，刚开始 debug 会觉得"怎么这么深"。

**结论**：抽象不是免费午餐。但对绝大多数应用来说——这点代价远低于自己手写厂商适配的成本。

---

## 二、Prompt Templates——把 Prompt 从"字符串"升级成"数据对象"

### 2.1 一个反例先上：你为什么会嫌字符串拼接难受？

下面这段代码我估计大家都写过：

```python
def build_prompt(role: str, question: str, examples: list[str]) -> str:
    examples_text = "\n".join(f"- {e}" for e in examples)
    return f"""你是一个{role}。
请参考以下示例：
{examples_text}

用户问题：{question}
"""
```

跑得起来，但**"它是个字符串"是这段代码所有问题的源头**：

- 我怎么知道它需要哪些变量？只能 grep 找 `{xxx}`
- 我怎么部分填充？比如 role 在初始化时就定了，question 才在每次请求时填
- 我怎么和别人共享一个 system prompt？复制粘贴
- 我怎么把它和 ChatModel 优雅地串起来？还是手动 `model.invoke(template.format(...))`

**Prompt Template 的存在，就是为了把 Prompt 从"裸字符串"升级成"带 schema、可部分填充、可组合、可被 Runnable 串起来的数据对象"**。

### 2.2 PromptTemplate vs ChatPromptTemplate——分清场景

LangChain 里这俩长得像，用途差很多：

| 类 | 输出 | 用在哪 |
| --- | --- | --- |
| `PromptTemplate` | 一段 **字符串** | Completion 风格的接口 / 给某个工具传字符串 |
| `ChatPromptTemplate` | 一组 **Message 列表**（System + Human + ...）| 现代 ChatModel，**99% 场景用它** |

**先看 ChatPromptTemplate 的标准写法**：

```python
from langchain_core.prompts import ChatPromptTemplate

prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个{role}，回答必须用{language}。"),
    ("human", "{question}"),
])

messages = prompt.invoke({
    "role": "翻译助手",
    "language": "中文",
    "question": "Translate: 'Agents are LLMs with hands.'",
})

print(messages.to_messages())
# [SystemMessage("你是一个翻译助手，回答必须用中文。"),
#  HumanMessage("Translate: 'Agents are LLMs with hands.'")]
```

注意三个细节：

1. `("system", "...")` 这种 tuple 写法是**糖**，框架会自动把它转成 `SystemMessagePromptTemplate`。
2. 模板里的 `{role}` 用的是 Python `str.format()` 的语法（默认）。如果你 prompt 里要写花括号字面量，要写 `{{` 转义。
3. `prompt.invoke({...})` 返回的不是 list，而是 `ChatPromptValue`——一个**两面派**对象，既可以 `.to_messages()` 给 ChatModel 用，也可以 `.to_string()` 拉成字符串。

### 2.3 三种"填变量"的姿势——别只会一种

很多人只会 `prompt.invoke({...})`，但实际工程里另外两种同样高频。

**姿势 1：partial（部分填充）**

```python
# 应用启动时把 role / language 钉死
preset = prompt.partial(role="翻译助手", language="中文")

# 后续每次请求只需要传 question
preset.invoke({"question": "..."})
```

适用场景：**"全局常量型"变量**——比如系统角色、输出语言、当前用户身份。先 `.partial` 钉死，之后调用方就少传几个参数，也少出错。

**姿势 2：format / format_messages（一次性渲染）**

```python
text_messages = prompt.format_messages(role="翻译助手", language="中文", question="...")
```

返回直接是 `list[BaseMessage]`。这个写法在**和老代码混用、或者把 Prompt 当 string 用**时非常方便。

**姿势 3：invoke（标准 Runnable 接口）**

就是上面那个例子。**它的存在是为了能被串进 LCEL 管道**，是工程化的主流写法。第三节 LCEL 会展示。

### 2.4 MessagesPlaceholder——多轮对话的关键拼图

光有 system + human 两条还不够。真实 Agent 都是多轮，需要把"历史对话"塞进 prompt。这时候要用 `MessagesPlaceholder`：

```python
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage

prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个{role}。"),
    MessagesPlaceholder("history"),       # ← 历史消息插槽
    ("human", "{question}"),
])

history = [
    HumanMessage("我叫小明"),
    AIMessage("你好小明！"),
]

msgs = prompt.invoke({
    "role": "客服",
    "history": history,
    "question": "我刚才说我叫什么？",
}).to_messages()

for m in msgs:
    print(type(m).__name__, "-", m.content)
# SystemMessage   - 你是一个客服。
# HumanMessage    - 我叫小明
# AIMessage       - 你好小明！
# HumanMessage    - 我刚才说我叫什么？
```

**这一段的精髓**：Prompt 模板不再是"一段字符串"，而是一个**带"插槽"的结构**——固定的部分写死，动态的部分（历史、检索结果、工具列表）通过 placeholder 注入。

后面 D17 的 Memory、D18-19 的 RAG、D26 的 LangGraph，本质都在往不同的 placeholder 里塞东西。

---

## 三、LCEL——用管道符 `|` 把三件事串成一行

### 3.1 "手工胶水"有多碍眼？

把前两节的内容拼在一起，你会写出这样的代码：

```python
msg_value = prompt.invoke({"history": history, "question": q})
ai = model.invoke(msg_value.to_messages())
return ai.content
```

三行"手工胶水"——每一步都手动调 `.invoke()`、手动转类型、手动取 `.content`。**LCEL（LangChain Expression Language）的存在，就是把这三行变成一行**。

### 3.2 管道符 `|` 的本质——Runnable 协议

`|` 不是 Python 的黑魔法运算符重载，它的本质是：**所有 LangChain 组件都实现了 `Runnable` 接口，`|` 就是把上一个的输出喂给下一个**。

```python
from langchain_core.output_parsers import StrOutputParser

chain = prompt | model | StrOutputParser()

result = chain.invoke({"history": history, "question": q})
```

等价于手动写：

```python
step1 = prompt.invoke({"history": history, "question": q})
step2 = model.invoke(step1.to_messages())
step3 = StrOutputParser().invoke(step2)
# step3 == result
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
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser

model = ChatOpenAI(
    model="qwen3.5-flash",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    temperature=0.3,
)

prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个简洁的{role}，回答不超过 30 字。"),
    MessagesPlaceholder("history"),
    ("human", "{question}"),
]).partial(role="技术助理")

chain = prompt | model | StrOutputParser()

history: list = []

def ask(q: str) -> str:
    answer = chain.invoke({"history": history, "question": q})
    history.extend([HumanMessage(q), AIMessage(answer)])
    return answer

print(ask("LangChain 最大的价值是什么？"))
print(ask("展开说一下'契约'的部分。"))
print(ask("我前面问了几个问题？"))
```

对比不用 LCEL 的版本（手动胶水）：

```python
def ask(q: str) -> str:
    msg_value = prompt.invoke({"history": history, "question": q})
    ai = model.invoke(msg_value.to_messages())
    history.extend([HumanMessage(q), AIMessage(ai.content)])
    return ai.content
```

**区别只有两行**，但这个差距会随着链变长（加 parser、加 fallback、加 retry）急剧放大。LCEL 的价值不在 3 步链，而在 10 步链。

---

## 四、回头看——D15 最值得记住的三件事

| 组件 | 一句话本质 | 替你解决的痛点 |
| --- | --- | --- |
| **ChatModel** | 一组**统一的 Runnable 接口**包住所有厂商 | 模型可替换、并发可批处理、消息可类型化 |
| **PromptTemplate** | 把 Prompt 从字符串**升级成数据对象** | 变量可插入、可部分填充、可组合、可串进管道 |
| **LCEL** | 用 `|` 把所有 Runnable **串成声明式管道** | 干掉手工胶水，一条链自动获得 stream/batch/retry |

而这三件事的背后，是 LangChain 整个框架的设计哲学——

> **抽象 LLM 应用里"能稳定下来的东西"，把"易变的东西"留给你配置。**
>
> 模型谁家、Prompt 怎么写、工具用哪些、检索怎么做——这些是易变的；
> 但 "调一次模型 / 渲染一段 Prompt / 解析一段输出" 这三类动作的接口形状——是能标准化的。

---

## 五、踩坑清单

1. **Prompt 模板里的字面花括号要 `{{ }}` 转义**：写 JSON 示例的时候特别容易踩。
2. **`prompt.invoke({...})` 返回的是 `ChatPromptValue`，不是 list**：要用 `.to_messages()` 才能直接喂给 ChatModel；不过 LCEL 串起来时这步会自动完成。
3. **`partial` 的"部分填充"是 LangChain 模板的杀手锏**：把"启动时就定的常量"和"每次调用才传的变量"分开——代码可读性立刻提升一档。
4. **不要一上来就 `create_agent`**：先把 ChatModel + PromptTemplate + LCEL 这一层吃透，后面的 Tool Agent 和 Memory 才不会觉得"框架是黑魔法"。
5. **`|` 不是奇技淫巧**：它的本质是 Runnable 协议，`a | b` 等价于"把 a 的输出喂给 b"。
6. **LCEL 的价值不在 3 步链，而在 10 步链**：3 步时手动胶水还行，10 步时 LCEL 的 `with_retry / with_fallbacks / batch` 自动能力就是救命的。

---

## 六、下一步：D16 给 Agent 装上工具

今天的三件套（ChatModel + PromptTemplate + LCEL）拼出了一个**能聊天、能模板化、能管道化**的 chain。但它还不能"做事"——不能调 API、不能查数据库、不能发邮件。

明天 D16 要做的事：用 `bind_tools` 给 ChatModel 装上工具，让 chain 从"只会聊天"进化成"会调工具的 Agent"。

我们明天见。

---

## 参考与延伸

- LangChain 官方文档 — `Concepts` → `Chat Models` / `Prompts` / `LCEL`
- 第二周 D8-D13 笔记 — ChatModel 解决的"模型可替换"问题，对应你第二周手写 SDK 的痛
- D14 笔记 — LangChain 是什么、生态分工、create_agent 快速入门
- 第三周后续：D16（Tool Agent）→ D17（Memory）→ D18-19（RAG）—— 一切都建立在今天这三件套上
