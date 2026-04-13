# 从 Chat Template 到工具调用：理解 LLM 的消息与角色系统

---

> 摘要：这篇文章带你理解 LLM 的消息组织方式、角色分层，以及 Responses API 与工具调用协议背后的核心心智模型。

## 一、为什么要理解 Chat Templates？

LLM 接收一组**结构化消息**。这些消息通常包含：

- 不同的**角色**
- 不同的**内容类型**
- 严格的**顺序关系**
- 在某些场景下还会包含**工具调用信息**

这种把对话组织成结构化消息序列的方式，就可以理解为 **Chat Template**。

理解这一点非常重要，因为后面的很多能力都建立在它之上：

1. 多轮对话的上下文管理
2. System Prompt 的设计
3. Function Calling / Tool Use
4. LangChain / LangGraph 中的消息编排
5. Agent 的推理-行动循环

---

## 二、什么是角色系统？

所谓角色系统，就是把一段对话中的不同信息来源，按职责拆分成不同类型的消息。

经典的Chat Completions API 最常见的三类角色是：

- `System`：系统级指令，典型内容是角色设定、行为规则、输出约束
- `User`：用户输入，典型内容是问题、任务、补充信息
- `Assistant`：模型输出，典型内容是历史回答、示例回答

新的Responses API则更加细化了，引入了 `developer` 这个角色，它是什么呢？接下来我们会详细了解一下。

---

## 三、System / User / Assistant 各自负责什么？

### 1. System：定义行为边界

`System` 消息通常用来定义模型应该如何工作。

示例：

```json
{
  "role": "system",
  "content": "你是一名专业的 Python 助手，请用简洁、准确、面向初学者的方式回答。"
}
```

你可以把 `System` 理解成一份“操作手册”或者“岗位说明书”。

但要注意，`System` 并不适合塞入大量动态业务数据。它更适合放**长期稳定的规则**，而不是频繁变化的上下文。

### 2. User：表达当前任务意图

`User` 消息代表用户此刻真正要做的事情。

例如：
```json
{
  "role": "user",
  "content": "请帮我解释一下 Python 中的装饰器，并给一个简单例子。"
}
```

用户消息通常是任务驱动的，是模型回答的直接依据。

### 3. Assistant：保存模型历史输出

`Assistant` 消息表示模型在前几轮里已经说过的话。

例如：
```json
{
  "role": "assistant",
  "content": "装饰器本质上是一个接收函数并返回新函数的函数。"
}
```

很多人以为模型“记得”刚才的对话，其实并不是。

**模型本身默认是无状态的。** 所谓多轮对话，只是因为你把上一轮的 `assistant` 输出和 `user` 输入，一起重新发给了模型。

也就是说：

- 模型没有天然记忆
- 记忆是你通过消息列表模拟出来的

---

## 四、Chat Template 的本质是什么？

从开发者角度看，Chat Template 本质上就是：

**把一段上下文包装成一个按顺序排列的消息列表。**

例如：

```json
[
  {
    "role": "system",
    "content": "你是一名耐心的编程老师。"
  },
  {
    "role": "user",
    "content": "什么是闭包？"
  },
  {
    "role": "assistant",
    "content": "闭包是函数与其词法环境的组合。"
  },
  {
    "role": "user",
    "content": "能不能给我一个 JavaScript 例子？"
  }
]
```

这个结构比“把所有内容拼成一个大字符串”更清晰，因为它显式保留了：
- 谁说的
- 什么时候说的
- 这段内容属于规则、问题还是历史回答
它本质上是**上下文组织方式**。

---

## 五、OpenAI 是怎么处理角色系统的？

### 1. 传统 Chat Completions 视角

在很多教程里，你最先接触到的是这样的格式：

```python
from openai import OpenAI

client = OpenAI()

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "你是一个简洁的技术助手。"},
        {"role": "user", "content": "请解释一下什么是向量数据库。"}
    ]
)

print(response.choices[0].message.content)
```

在这个模式里，你最常见到的角色就是：

- `system`
- `user`
- `assistant`

这套模型对初学者非常友好，也足够帮助你理解多轮对话是如何构建的。

### 2. 新版 Responses API 的变化

OpenAI 现在更推荐使用 `Responses API`。在新版接口里，一个重要变化是：

- 会更强调**指令层级**
- `developer` 角色开始变得重要
- `input`：字符串或 message 数组；数组里 message 的 `role` 为 `system` / `developer` / `user` / `assistant`。
- `instructions`：在上下文最前面插入一条“系统说明”，跟 `system` 类似
例如：

```python
response = client.responses.create(
    model="gpt-5",
    input=[
        {
            "role": "developer",
            "content": "你是一个面向初学者的编程老师，回答时尽量使用短句和例子。"
        },
        {
            "role": "user",
            "content": "什么是 Chat Template？"
        }
    ]
)

print(response.output_text)
```

这里的核心认知是：

- `developer` 可以理解为**应用开发者提供的高优先级业务规则**
- `user` 是终端用户提出的任务
- `assistant` 是模型历史输出

所以在新版 OpenAI 语境里，与其死记“只有三种角色”，不如理解成：

**不同来源的指令，优先级并不相同。**

**注意事项**：
Qwen 兼容层**不是完全兼容 OpenAI Responses API**，有些字段（比如 `instructions`）
**可能只是“尽量支持”，不是强约束。**
也就是不同的模型厂商，对于 Response API 可能会不完全兼容。

例如下面一个 case：
![[Pasted image 20260410154033.png]]

也就是 Qwen 对 role 的理解 ≠ OpenAI

- OpenAI：
    - system > developer > user（强约束链）
- Qwen（实际表现）：
    - 更接近“聊天模型”
    - **role 语义不严格**
    - developer ≠ system（不一定最高优先级）

上面 role改成：system 则正常了；

### 3. 为什么 OpenAI Response API 要引入 Developer 角色呢

`developer` 角色是 OpenAI 在推出推理模型（o1 系列）及 Responses API 时引入的新消息角色，目的是在 **平台级约束（system）** 与 **用户输入（user）** 之间，提供一个专属于应用开发者的指令层。

为何需要这个新角色？

在旧版 Chat Completions API 中，只有 `system`、`user`、`assistant` 三种角色。`system` 承担了"平台规则"和"开发者业务逻辑"两大职责，职责边界模糊，难以区分"绝对不能违反的平台规则"和"可按需动态调整的业务指令"。

引入 `developer` 角色的核心原因有以下几点 ：

- **职责分离**：`system` 专注于平台级、不可变的规则（如安全策略、合规约束）；`developer` 专注于应用级的业务逻辑、行为风格、工具调用规范等，开发者无需修改核心 system prompt 即可动态注入指令
- **动态灵活性**：在 RAG、多工具调用等 Agent 场景中，开发者常需为每次请求注入不同的上下文或格式化要求，`developer` 消息天然适合承载这类"每次请求级别"的动态指令
- **模块化设计**：将 system prompt 保持简洁，把实现细节（如输出格式、函数调用规范）放入 `developer` 消息，提高可维护性

根据 OpenAI 官方文档及 Model Spec，优先级从高到低依次为 ：

| 角色          | 优先级 | 职责定位                |
| ----------- | --- | ------------------- |
| `system`    | 最高  | 平台级规则，绝对约束，不可被下层覆盖  |
| `developer` | 次高  | 应用/开发者级业务逻辑，不可被用户覆盖 |
| `user`      | 第三  | 终端用户输入，受上层约束限制      |
| `assistant` | 最低  | 模型生成的历史响应，仅作上下文参考   |

实践建议

- **`system`**：放置一条，内容为全局不变的平台规则或安全边界    
- **`developer`**：可以有多条，放置动态的业务逻辑、工具使用说明、输出格式要求等
- **`user`**：终端用户的实际输入
![[Pasted image 20260410161059.png]]

值得注意的是，Responses API 中的顶层 `instructions` 字段在语义上等同于 `developer` 级别的指令，优先级高于 `input` 中的用户消息，但低于 `system` 约束

### 4. OpenAI 中的工具调用

当你启用工具时，模型并不会真的去执行代码。它会先输出一个**结构化工具调用请求**。

在新版 `Responses API` 里，模型返回的 `output` 中可能出现 `function_call` 项。一个最关键的字段是：

- `name`：调用哪个工具
- `arguments`：工具参数，通常是 JSON 字符串
- `call_id`：**这次工具调用的唯一关联 ID**

简化后的返回结构可以理解成：

```json
{
  "type": "function_call",
  "name": "get_weather",
  "arguments": "{\"location\":\"Beijing\"}",
  "call_id": "call_abc123"
}
```

你的应用执行完工具后，不能只把“26°C，多云”这段文本扔回去，而是要显式告诉模型：

**这份结果对应的是哪一次工具调用。**

因此需要回传：

```json
{
  "type": "function_call_output",
  "call_id": "call_abc123",
  "output": "北京当前 26°C，多云"
}
```

也就是说，OpenAI 的工具调用流程本质上是：

```text
模型输出 function_call
→ 应用读取 name / arguments / call_id
→ 应用执行真实工具
→ 应用回传 function_call_output + call_id
→ 模型继续生成最终回答
```

这里的关键不是“模型会调工具”，而是：

- 模型生成**调用意图**
- 应用执行**外部副作用或查询**
- 双方通过 `call_id` 完成**调用与结果的配对**

如果一次响应里有多个工具调用，这个 `call_id` 就尤其关键。因为结果不是天然按顺序匹配的，而是应该按 ID 匹配。

另外，OpenAI 的 reasoning 模型在某些场景下不只是返回工具调用，还会返回 reasoning items。继续下一轮时，除了工具输出，还要保留必要的推理上下文项，否则模型可能丢失当前推理状态。

这部分在后续我们做 tools 工具调用的时候，会详细地有所讲解。

---

## 六、Anthropic 是怎么处理角色系统的？

### 1. Messages API 的结构特点

Anthropic 的 Claude API 也支持多轮对话，但它的组织方式和 OpenAI 有一点不同。

一个典型请求通常长这样：

```python
import anthropic

client = anthropic.Anthropic()

response = client.messages.create(
    model="xxx",
    max_tokens=1024,
    system="你是一名面向初学者的 AI 导师。",
    messages=[
        {"role": "user", "content": "请解释一下 System Prompt 的作用。"}
    ]
)

print(response.content[0].text)
```

你会发现：

- `system` 常常是一个顶层字段
- `messages` 里主要是 `user` 和 `assistant`

也就是说，Anthropic 不是简单把所有东西都塞到同一个 `messages` 数组里。

### 2. Anthropic 与 OpenAI 的一个关键差别

如果用一句话总结：

- OpenAI 更容易从“消息角色列表”角度理解
- Anthropic 更容易从“消息内容块 + agentic loop”角度理解

两者表面长得不一样，但底层思想是一样的：

**模型负责推理与决策，应用负责执行与回填结果。**

但在真正实现时，二者的关注点不同：

- OpenAI 更像是“输出 item 流”，你要识别 `function_call` 与 `function_call_output`
- Anthropic 更像是“内容块流”，你要识别 `tool_use` 与 `tool_result`
- OpenAI 用 `call_id` 关联
- Anthropic 用 `tool_use_id` 关联

所以如果你在封装一层统一 Agent Runtime，最先抽象的往往不是 `role`，而是：

- 调用 ID、工具名、参数、执行状态、 结果载荷
- 结果归属的消息位置

---

## 七、OpenAI 与 Anthropic 的角色系统对比

| 维度 | OpenAI | Anthropic |
| ---- | ------ | --------- |
| 上下文主结构 | `input` / `messages` 序列 | 顶层 `system` + `messages` |
| 常见角色 | `developer` / `system` / `user` / `assistant` | `user` / `assistant`，`system` 常为顶层参数 |
| 工具调用表示 | `function_call` / `function_call_output` | `tool_use` / `tool_result` |
| 关联字段 | `call_id` | `tool_use_id` |
| 参数位置 | `arguments`，通常是 JSON 字符串 | `input`，通常是结构化对象 |
| 结果回传方式 | 回传 `function_call_output` item | 在下一条消息中回传 `tool_result` block |
| 并行工具调用 | 常见，需按 `call_id` 分别处理 | 常见，需按 `tool_use_id` 分别处理 |
| 服务端工具 | 有部分内建工具能力 | 明确区分 client tools 与 server tools |
| 更适合理解方式 | 指令层级 + item 流 | 内容块协议 + agentic loop |

对于初学者来说，最重要的不是死记接口差异，而是抓住共同本质：

1. 消息是结构化的
2. 模型是无状态的
3. 多轮对话靠消息历史维持
4. 工具调用本质上是“模型提议，应用执行”

---

## 八、Tool 到底算什么？

学到这里，很多人会自然产生一个问题：

**Tool 是不是一种新的角色？**

从直觉上看，好像是，因为它也进入了消息流。

但更准确的说法是：

- 它不只是“一个标签”
- 它代表的是一次**结构化行动请求**或**行动结果回填**

在不同厂商里，工具相关信息的表现形式不完全一样：

- 在有些接口中，它像是特殊消息
- 在有些接口中，它像是特殊内容块
- 在 LangChain 里，它会被抽象成专门的消息类型

因此，更好的理解方式是：

**工具不是普通聊天文本，它是模型与外部世界交互的协议接口。**

---

## 九、为什么工具调用一定要靠 ID 匹配？

这是工具调用里最容易被忽略、但在工程里最关键的点之一。

很多初学者会以为：

```text
模型先调第一个工具
我执行完第一个工具
再把结果按顺序塞回去就好了
```

这个理解在最简单的 demo 里可能暂时能工作，但一旦进入真实场景，就会出问题。原因有三个。

### 1. 模型可能一次返回多个工具调用

例如模型可能同时请求：

- 查天气
- 查日历
- 查航班价格

这时候如果只靠数组顺序，而不是靠 ID，你很容易把结果回填错位。

### 2. 工具执行可能并发，完成顺序未必一致

即使模型按 A、B、C 顺序请求工具，实际执行时也可能是：

- B 最先完成
- C 第二个完成
- A 最后完成

如果没有 `call_id` 或 `tool_use_id`，系统就很难知道“这份结果到底对应哪一次调用”。

### 3. 展示层、日志层、追踪层都依赖稳定主键

在 UI 中你常常需要显示：

- “正在调用天气工具…”
- “天气工具已完成”
- “航班查询失败”

这些状态变化本质上都是围绕某一次具体调用展开的，所以一定需要一个稳定的调用 ID 作为主键。

换句话说，工具调用里的 ID，作用非常像数据库主键或前端组件的 `key`：

- 用来关联请求与结果
- 用来支撑并发执行
- 用来支撑状态更新
- 用来支撑日志追踪与可观测性

所以真正成熟的 Agent Runtime，一般都会在内部维护一个统一结构，例如：

```json
{
  "id": "call_abc123",
  "name": "get_weather",
  "args": {"location": "Beijing"},
  "status": "completed",
  "result": "北京当前 26°C，多云"
}
```

无论底层来自 OpenAI 还是 Anthropic，最后都会被归一化成这种“带 ID 的工具调用记录”。

---

## 十、LangChain 是怎么统一这一套东西的？

当你开始同时接 OpenAI、Anthropic、Google 等不同模型时，会发现每家的消息格式都略有不同。

LangChain 的价值之一，就是把这些差异统一抽象起来。

### 1. LangChain 的四种核心消息类型

在 LangChain 中，你会经常见到这些类型：

- `SystemMessage`
- `HumanMessage`
- `AIMessage`
- `ToolMessage`

示例：

```python
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="qwen3.5-flash", temperature=0.7, max_tokens=1000)

messages = [
    SystemMessage("你是一名清晰、耐心的 AI 导师。"),
    HumanMessage("一句话解释 什么是 Chat Template。")
]

response = llm.invoke(messages)
print(response.content)
```

这里的好处是：

- 你不用总是纠结底层厂商的 JSON 长什么样
- 你可以统一用消息对象组织上下文
- 切换模型提供商时，代码结构更稳定

### 2. ToolMessage 的作用

在 LangChain 里，`AIMessage` 可以包含工具调用请求，而 `ToolMessage` 负责把工具执行结果送回模型。

这和我们前面讲的 OpenAI / Anthropic 思想是一致的，只不过 LangChain 把它整理成统一接口了。

更重要的是，LangChain 没有忽略“调用 ID”这个工程核心，而是把它保留下来了：

- `AIMessage.tool_calls[*].id` 表示某次工具调用的唯一标识
- `ToolMessage.tool_call_id` 表示这条结果对应哪一次工具调用

例如：

```python
from langchain.messages import AIMessage, ToolMessage

ai_message = AIMessage(
    content="",
    tool_calls=[
        {
            "name": "get_weather",
            "args": {"location": "Beijing"},
            "id": "call_123"
        }
    ]
)

tool_message = ToolMessage(
    content="北京当前 26°C，多云",
    tool_call_id="call_123"
)
```

这个例子很直观地说明：

- `AIMessage` 表示模型提出“我要调工具”
- `ToolMessage` 表示程序把结果送回来
- `tool_call_id` 保证结果不会配错调用对象

这意味着 LangChain 做的并不只是“字段改名”这么简单，而是在帮你建立一个跨模型统一的数据契约。

### 3. 前端如何展示工具调用信息？

很多教程只讲“怎么让模型调用工具”，但在真实产品里，你通常还要考虑：

- 用户如何知道 Agent 正在做什么
- 一个工具是在执行中、已完成，还是执行失败
- 多个工具并行时，界面如何不乱
- 是展示原始 JSON，还是展示可读卡片

一个比较成熟的展示模型，通常会把每次工具调用都抽象成：

- `id`
- `name`
- `args`
- `state`：`pending` / `completed` / `error`
- `result`

然后在聊天 UI 中把它渲染成“工具卡片”。例如：

- 调用中：显示 `Running get_weather(Beijing)…`
- 成功：显示天气结果卡片
- 失败：显示错误卡片与失败原因

LangChain 前端文档本身也推荐这种模式：把 `toolCalls` 单独抽出来渲染，而不是把工具调用过程混成一大段普通聊天文本。

这背后的设计原则很重要：

1. **工具调用是状态流，不只是文本流**
2. **工具调用应该可追踪，而不是只在日志里偷偷发生**
3. **展示时最好按 `call.id` 进行更新，而不是重新插入一条模糊的文本消息**

如果你以后要做自己的 Agent UI，可以优先考虑下面这种展示策略：

- 普通回答：按聊天消息展示
- 工具调用：按结构化卡片展示
- 并行工具：每个调用一张卡片，独立更新状态
- 未知工具：回退成可折叠 JSON 视图

这种设计会明显优于在聊天里输出：

```text
我现在要调用天气工具……
我现在得到了结果……
```

因为真正稳定的 UI 应该由协议事件驱动，而不是依赖模型额外生成解释文本。

### 4. ChatPromptTemplate 又是什么？

LangChain 里还有一个非常重要的东西叫 `ChatPromptTemplate`。

它的作用是：

**声明式构造一组消息。**

例如：

```python
from langchain.prompts import ChatPromptTemplate

prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一名 AI 助手，请用简洁语言回答。"),
    ("human", "请解释一下 {topic}。")
])

messages = prompt.format_messages(topic="角色系统")
```

你可以把它看作“消息版的 Prompt 模板”。

它不是直接生成一个大字符串，而是生成一组结构化消息。

### 5. LangChain 启用 Responses API

```python
# 启用 Responses API

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="qwen3.5-flash", 
                 use_responses_api=True)   # 关键参数

prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一位专业的{domain}顾问，回答请简洁专业。"),
    ("human", "{question}")
])

chain = prompt | llm

response = chain.invoke({"domain": "AI", "question": "一句话解释：AI会吃掉一切吗？"})
print(response.text)
```


### 6. Responses API 核心优势**服务端会话状态**

> Responses API 的核心优势是**服务端会话状态**，通过 `previous_response_id` 串联上下文，无需客户端手动维护历史消息列表

![[Pasted image 20260410163458.png]]


另外，它还可以绑定一些内置工具。这些内置工具会根据不同的模型厂商而有所不同。就比如以“千问”这个大模型来说：

Alibaba Cloud Responses API 提供以下内置工具 ：

|工具类型|说明|
|---|---|
|`web_search`|网络搜索|
|`web_extractor`|网页内容抓取|
|`code_interpreter`|代码解释器|
|`text_to_image`|文生图|
|`image_to_image`|图生图|
|`knowledge_base_search`|知识库检索|


以下模型支持 Responses API + 内置工具 ：
- `qwen3.5-plus` / `qwen3.5-plus-2026-02-15`
- `qwen3.5-flash` / `qwen3.5-flash-2026-02-23`
- `qwen3-max` / `qwen3-max-2026-01-23`

如下测试：
![[Pasted image 20260410164553.png]]

可以看到`content` 是一个列表，包含多个不同 `type` 的块，代表模型的**完整思考+执行链路**：

```python
content = [
  { type: "reasoning" },        # 第一步：内部推理
  { type: "web_search_call" },  # 第二步：调用 web_search 工具
  { type: "reasoning" },        # 第三步：整理搜索结果的推理
  { type: "text" },             # 第四步：最终回复给用户
]
```

|块类型|说明|
|---|---|
|`reasoning`|模型内部思考过程，含 `summary` 字段，对应 `enable_thinking` 输出|
|`web_search_call`|工具调用记录，含 `action.sources`（实际访问的 URL 列表）和 `status: completed`|
|`text`|最终输出文本，`text` 字段是给用户看的实际内容|

```python
for block in response.content:
    block_type = block.get("type")

    if block_type == "reasoning":
        for s in block.get("summary", []):
            print(f"[🤔思考] {s['text'][:80]}...")

    elif block_type == "web_search_call":
        sources = block["action"].get("sources", [])
        print(f"[🔍搜索] 共访问 {len(sources)} 个来源")
        for s in sources[:3]:  # 只打印前3个
            print(f"  - {s['url']}")

    elif block_type == "text":
        print(f"\n[👌最终回复]\n{block['text']}")
```

![[Pasted image 20260410164901.png]]

---

## 十一、一个最小但非常重要的心智模型

如果把这一节内容压缩成一句话，那就是：

> 你不是在和模型直接聊天，你是在持续构造一个消息列表，然后把这个消息列表发给模型。

这句话背后有四层重要含义：

1. **模型默认无状态**
   每次请求本质上都是一次新的推理。

2. **多轮对话是你模拟出来的**
   你把历史消息重新传进去，模型才“像是记得”。

3. **角色决定了消息的职责**
   System / Developer 放规则，User 放任务，Assistant 放历史输出。

4. **工具调用让模型不只是会说，还会请求行动**
   它可以调用搜索、数据库、计算器、浏览器等外部能力。

进一步说，工具调用不是“模型多说了一句话”，而是把对话系统升级成了一个**带外部执行回路的状态机**。

一旦你从这个角度理解消息系统，你就会发现：

- Chat Template 负责组织上下文
- 角色系统负责分配语义职责
- 工具调用协议负责把推理接到外部世界
- 调用 ID 负责让整个系统在并发和多步执行下仍然保持一致性

这个心智模型一旦建立起来，后面学习：

- Function Calling
- ReAct
- Agent
- LangChain
- LangGraph
- Context Engineering

都会顺很多。

---

## 十二、常见误区

### 误区 1：把所有信息都放进 System Prompt

`System` 更适合放稳定规则，不适合塞入大量动态检索结果或用户上下文。

### 误区 2：以为模型自己记得历史对话

模型并不会“自动保存记忆”，除非你把历史消息再次传给它。

### 误区 3：把工具调用理解成模型真的在执行函数

模型不会直接运行你的代码，它只是输出结构化调用意图。

### 误区 4：忽略消息和工具描述的 Token 成本

工具 schema、历史消息、工具结果都会进入上下文，都会占用 Token。

### 误区 5：把工具结果当成“普通字符串追加”

真正稳定的做法不是简单拼接文本，而是通过 `call_id` 或 `tool_use_id` 明确关联到原始调用。

### 误区 6：只关注模型层，不关注展示层和日志层

一旦进入产品化阶段，工具调用必须同时考虑：

- 模型怎么生成调用
- Runtime 怎么执行调用
- UI 怎么展示调用状态
- Tracing / Logging 怎么追踪调用耗时与错误

---

## 十三、小结

- **Chat Template 的本质，不是“聊天格式”，而是结构化上下文的组织方式**
- **角色系统的核心，不是记住几个单词，而是理解不同消息来源的职责与优先级**：`system` / `developer` / `user` / `assistant` 各自承担的平台约束、开发者规则、用户任务与历史输出并不相同
- **Responses API 把这套思路进一步推进了**：一方面通过 `developer` 与 `instructions` 强化指令分层，另一方面通过 `previous_response_id` 提供服务端会话状态，减少客户端手动拼接完整历史的负担
- **但工程上不能只看“接口长什么样”**：不同厂商即使兼容 OpenAI 风格，在 `role` 语义、字段支持、内置工具能力上也可能存在差异，因此真正可靠的系统要基于协议理解，而不是只基于表面字段名
- **Tool Use / Function Calling 的本质，是模型提出结构化行动请求，应用负责真实执行，再把结果按协议回填**
- **无论是 OpenAI 的 `call_id`，还是 Anthropic 的 `tool_use_id`，本质上都在解决同一个问题**：让并发调用、多步执行、UI 状态更新、日志追踪都能稳定对齐到同一次工具调用
- **LangChain 的价值，则在于把这些底层差异统一抽象成消息对象、工具调用记录与可组合的 Prompt 结构**，让你可以把重点放在业务流程，而不是反复适配不同厂商协议
- **所以从产品视角看，消息系统、角色系统、工具调用协议、前端展示、Tracing 与可观测性，其实是一整套连在一起的运行时设计**

> 💡 **预告**：理解了这一层之后，下一步就可以继续进入 API 调用实战、多轮对话管理，以及第二周更核心的 Function Calling / Tool Use 与 Agent Runtime 设计。

---
