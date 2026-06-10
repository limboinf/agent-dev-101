# LangChain 入门：抛开"框架"滤镜，看清它到底替你做了什么

---

> 摘要：第二周我们手搓了 ReAct、Function Calling、结构化输出，写到 D13 的时候我自己也产生了一个隐隐的疑问——**"我两周前就能用 OpenAI SDK 调通一切了，凭什么从今天开始要拐到 LangChain 上？"** 这是每个从原生 API 跨到框架的人都要回答的问题。今天 D14 就是来回答它的。我不打算把官网那套"30 秒 Quickstart"再抄一遍——那种东西你看完只会得到"会跑"和"会忘"，不会得到"理解"。这篇笔记换一个角度：先把**"LangChain 到底是什么、生态怎么分工、`create_agent` 怎么用"**这三件事搞清楚。读完之后，你应该能笃定地说一句：**"框架不是魔法，它是一层我自己写也写得出来、但写出来会很烦的'契约层'。"** 这是后面一个月所有 LangChain / LangGraph 内容的认知底座。

---

## 一、先回答那个最尖锐的问题——"我都手写两周了，凭什么用 LangChain？"

我把这个问题拆成三个更具体的小问：

1. **如果只是调一次 LLM——LangChain 是不是多余？** 是的，多余。
2. **如果要写一个能切模型、能换 Prompt、能加工具、能续上 RAG 和 Memory 的应用——LangChain 是不是多余？** 不多余，**但你以为它解决的问题，和它真正解决的问题，往往不是一回事**。
3. **学完这周我会爱上 LangChain 吗？** 不一定。LangChain 1.0 之后裁掉了很多东西、也加了 Middleware 这种新的强抽象，社区情绪一直分裂。但**不学一遍你看不懂 LangGraph、看不懂 LangSmith trace、也看不懂招聘 JD 上一半的关键字**，所以"喜不喜欢"和"要不要学"是两件事。

下面我用一段对照来回答上面的第二问——LangChain 真正解决的，是这三类问题。

| 真问题             | 不用框架的痛点                                                                        | LangChain 给你的"契约"                                                  |
| --------------- | ------------------------------------------------------------------------------ | ------------------------------------------------------------------ |
| **模型可替换**       | 今天用 OpenAI、明天换通义千问、后天换 Claude，三套 SDK 三种消息格式，业务代码里到处是 `if provider == "openai"` | `ChatModel` 这一层统一接口：`invoke / stream / batch / bind_tools` 全部一致    |
| **Prompt 可工程化** | Prompt 是字符串拼接，变量靠 f-string，多人协作改一个 system prompt 要 grep 全仓                     | `PromptTemplate / ChatPromptTemplate` 把 Prompt 提升为"带 schema 的数据对象" |
| **组件可组合**       | 自己手写 `output → parse → 喂给下一步 → 错了重试` 一长串 if-else                               | LCEL 的管道符 `\|` 把上述东西变成一行                                           |

这三件事明天 D15 会展开讲透（ChatModel + PromptTemplate + LCEL），今天先建立全局认知。


## 二、LangChain 是什么？——它不是"Agent 框架"

### 2.1 一个常见的认知错误

> **LangChain 是一个为 LLM 应用（不只是 Agent）提供"标准接口 + 可组合组件"的中间层。Agent 只是它众多用法中的一个。**

它处于这样一个位置：

```diagram
╭───────────────────────────────────────────────────╮
│  你的业务代码（CLI / API 服务 / Web 应用）         │
╰────────────────────┬──────────────────────────────╯
                     │   想做一件事："把用户问题
                     │   交给某个 LLM，按某种 Prompt
                     │   组织上下文，再把结果用某种
                     │   方式解析"
                     ▼
╭───────────────────────────────────────────────────╮
│  LangChain：标准接口层                             │
│  · ChatModel       —— 模型这一格                   │
│  · PromptTemplate  —— Prompt 这一格                │
│  · OutputParser    —— 结果解析这一格               │
│  · Runnable / LCEL —— 把上面三格串起来             │
│  · Tools / Memory / Retrieval —— 进阶能力          │
╰────────────────────┬──────────────────────────────╯
                     │  各家 SDK 协议
                     ▼
╭───────────────────────────────────────────────────╮
│  OpenAI / Anthropic / DashScope / DeepSeek / ...    │
╰───────────────────────────────────────────────────╯
```

它**不是**：

- 不是一个 Agent runtime（那是 LangGraph 的职责）
- 不是一个推理引擎（推理仍然在你接的 OpenAI / Anthropic / 阿里云那边）
- 不是一个评估平台（那是 LangSmith）

它**是**：

- 一组**契约**：你写出 `model.invoke(prompt)`，背后是哪家模型都能跑
- 一组**乐高积木**：每块都实现一个 `Runnable` 接口，可以用 `|` 串起来
- 一个**生态总线**：成千上万的 `langchain-xxx` 集成包都遵循这套契约

### 2.2 它和"我自己封装一层"有什么本质区别？

我猜很多人心里都嘀咕过："不就是封装一层吗，我自己写一个 `def chat(model, prompt) -> str` 不就完了？"

写一个能跑的版本确实很容易。但当你**真要把这一层做到能切模型、能流式、能批处理、能带工具、能与 LangSmith 联动、能被 LangGraph 当节点用**——你就会发现，你最终重新发明了 LangChain，而且大概率比它还丑。

### 2.3 包结构小科普——免得你 import 错地方

LangChain 1.0 之后包做了拆分，刚上手很容易 import 错。记住这个心智模型：

| 包                                               | 装什么                                      | 什么时候装             |
| ----------------------------------------------- | ---------------------------------------- | ----------------- |
| `langchain-core`                                | 抽象基类、Runnable、消息类型、PromptTemplate        | 默认会被装上，**不要直接装它** |
| `langchain`                                     | 高层组件：`create_agent`、Chains、Retriever 抽象等 | 写应用一般装这个          |
| `langchain-openai` / `langchain-anthropic` / 等等 | 具体模型集成                                   | 用谁装谁              |
| `langgraph`                                     | 状态机/Agent 编排（D24 起单独讲）                   | 写复杂 Agent 装它      |

---

## 三、LangChain 生态一览

![](https://limbo.oss-cn-beijing.aliyuncs.com/wiki/20260610154323121.png)

LangChain 1.0 本身也构建在 LangGraph 之上，但用 LangChain 不需要懂 LangGraph;

**三者定位对比**：

| 对比维度    | Deep Agents                         | LangChain                              | LangGraph                    |
| ------- | ----------------------------------- | -------------------------------------- | ---------------------------- |
| 定位      | 代理 harness                          | 代理框架 framework                         | 编排运行时 runtime                |
| 核心价值    | 预置工具、提示、子代理                         | 抽象 + 集成（`create_agent`）                | 持久执行、流式、HITL、持久化             |
| 内置能力    | 规划 todo、虚拟文件系统（可插拔后端）、上下文自动压缩、子代理生成 | 模型/工具/中间件抽象、标准消息格式                     | 低层图编排、checkpointer、interrupt |
| 适用场景    | 长时间运行、复杂多步任务（研究/编码）                 | 快速构建、需要定制 harness                      | 确定性+代理混合的复杂工作流               |
| HITL 实现 | `interrupt_on` 参数                   | Human-in-the-loop 中间件                  | Interrupts                   |
| 子代理     | Subagents                           | Multi-agent subagents                  | Subgraphs                    |
| 同类对标    | Claude Agent SDK、Manus              | Vercel AI SDK、CrewAI、OpenAI Agents SDK | Temporal、Inngest             |

### 3.1 langchain 核心组件

langchain 官网说 **Agent = Model + Harness**，那 `create_agent` 是一款高度可配置的 harness。所以 create_agent 是核心入口。

![](https://limbo.oss-cn-beijing.aliyuncs.com/wiki/20260610155527766.png)

上图 create_agent 可对应如下代码：

```python
from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware, HumanInTheLoopMiddleware

agent = create_agent(
    model="anthropic:claude-sonnet-4-6",    # 模型节点
    tools=[search, run_query],              # 工具节点
    system_prompt="...",                    # 系统提示
    response_format=Answer,                 # 结构化输出(Pydantic)
    checkpointer=InMemorySaver(),           # State 持久化(短期记忆)
    middleware=[                            # 挂到图上的钩子
        SummarizationMiddleware(model="...", trigger=("tokens", 4000)),
        HumanInTheLoopMiddleware(interrupt_on={"send_email": True}),
    ],
)
```

整个 langchain 核心组件有：

![](https://limbo.oss-cn-beijing.aliyuncs.com/wiki/20260610155941294.png)

---

## 四、create_agent 快速入门

![](https://limbo.oss-cn-beijing.aliyuncs.com/wiki/20260610162450570.png)

`config` 是**运行时配置**，和 agent 定义解耦——同一个 agent 实例，靠 config 区分"这次调用属于谁的哪个会话"。

### config 的作用

`configurable.thread_id` 是给 **checkpointer 用的会话标识**。机制：

1. 每个执行步骤后，checkpointer 把整个 State（messages 等）快照存下来，**以 thread_id 为 key**
2. 下次用相同 thread_id invoke 时，先加载历史 State，新消息追加进去 → 模型看到完整对话历史
3. 换一个 thread_id = 全新会话，互不可见

### checkpointer 是必须的吗？

**不是。** 两种模式：

|           | 无 checkpointer      | 有 checkpointer                 |
| --------- | ------------------- | ------------------------------ |
| 状态        | 无状态，每次 invoke 互相独立  | 按 thread_id 持久化 State          |
| 多轮对话      | 自己拼完整 messages 历史传入 | 只传新消息，历史自动加载                   |
| thread_id | 不需要（传了也没用）          | **必须传**，否则报错                   |
| 额外能力      | 无                   | HITL 中断恢复、time travel、断点续跑都依赖它 |

## 运行时上下文

runtime.context
如下代码：
create_agent的 `context_schema` 和  invoke 方法的 `context` 参数，它们表示啥呢？

```python

@dataclass
class Context:
    user_id: str
    vip_level: int
    user_name: str
    
agent = create_agent(
    model=..
    tools=[],
    context_schema=Context,      # <- 这里 
    checkpointer=InMemorySaver() # 持久化：按 thread_id 持久化 State
)


agent.invoke(..., 
	context=Context(user_id='1001', vip_level=5, user_name='方先生')
)
```

解释下：

>两个参数是一对：`context_schema` 定义**结构**（建 agent 时声明），`context` 传**值**（每次 invoke 时注入）。本质是给工具和中间件做**依赖注入**——不用全局变量、不用硬编码，把"这次运行属于谁、用什么资源"在调用时塞进去。

### 和 State 的本质区别

|      | State（messages 等）             | Runtime Context       |     |
| ---- | ----------------------------- | --------------------- | --- |
| 性质   | 动态，循环中不断被改写                   | 静态，整个 run 内只读         |     |
| 持久化  | 被 checkpointer 按 thread_id 存档 | **不持久化**，每次 invoke 现传 |     |
| 装什么  | 对话历史、中间结果                     | user_id、数据库连接、权限、配置   |     |
| 谁在读写 | 模型节点、工具结果追加                   | 工具、中间件、动态 prompt 读取   |     |

一句话：**State 是对话的"内容"，Context 是这次运行的"环境"**。你代码注释里写的没错——thread_id 圈定对话范围，context 是运行时数据，二者通常一并传。

### 怎么读取：靠 Runtime 对象

这才是它的价值所在。三个典型消费方：

**1. 工具里读**（声明 `ToolRuntime` 参数，框架自动注入，模型看不到这个参数）：
```python
from langchain.tools import tool, ToolRuntime 

@tool 
def get_my_orders(runtime: ToolRuntime[Context]) -> str: 
	"""查询当前用户的订单""" 
	user_id = runtime.context.user_id
	return '....'
```


**2. 动态 system prompt**：
```python
from langchain.agents.middleware import dynamic_prompt

@dynamic_prompt
def my_prompt(request) -> str:
    name = request.runtime.context.user_id
    return f"你是助理，称呼用户为 {name}。"
```

**3. 中间件钩子里读**：`runtime.context.xxx`，比如按用户等级决定限流策略。

Runtime 对象上除了 `context` 还挂着：`store`（长期记忆）、`stream_writer`（自定义流式输出）、`execution_info`（thread_id/run_id）、`server_info`（部署到 LangSmith 时的 assistant_id）。

下面给一个特定的例子：

```python
from dataclasses import dataclass
from langchain.agents.middleware import dynamic_prompt
from langchain.tools import tool, ToolRuntime


@dataclass
class Context:
    user_id: str
    vip_level: int
    user_name: str
    

@tool
def get_my_orders(runtime: ToolRuntime[Context]) -> str:
    """
    获取用户的订单信息
    """
    uid = runtime.context.user_id
    print(f"工具调用：get_my_orders, ctx: {runtime.context}")
    if uid == '1001':
        return f"用户 {runtime.context.user_name} 的订单支付了100美金"
    else:
        return "订单不存在"


@dynamic_prompt
def personalized(request) -> str:
    ctx = request.runtime.context
    base = f"你是客服助理，称呼用户为{ctx.user_name}。"
    if ctx.vip_level >= 3:
        base += "该用户是 VIP， 称呼时候需要加上尊贵的VIP用户"
    return base


# 创建agent
agent = create_agent(
    model=llm,        # 模型可以是 "provider:model" 字符串标识，也可模型实例
    tools=[get_my_orders],
    context_schema=Context,
    middleware=[personalized],
    checkpointer=InMemorySaver() # 持久化：按 thread_id 持久化 State
)

# 运行时配置
# configurable.thread_id 是给 checkpointer 用的会话标识 
config = {'configurable': {'thread_id': '10010'}}


# thread_id 限定对话范围（消息历史、检查点）
# 而 context 承载工具和中间件在调用时读取的每次运行数据。二者通常会一并传递
result = agent.invoke(
    {'messages': [{'role': 'user', 'content': '你好, 看下我的订单'}]},
    config=config,
    context=Context(user_id='1001', vip_level=5, user_name='方先生')
)

print(result)
```

![](https://limbo.oss-cn-beijing.aliyuncs.com/wiki/20260610172743204.png)

更深入的理解，如图：

![](https://limbo.oss-cn-beijing.aliyuncs.com/wiki/20260610172817564.png)


如果你用**fastapi**, 还可以这样实战：**FastAPI 依赖注入作为langchain context 把请求级资源（DB session、本次任务 ID）透传到工具层，全程无全局变量：**

```python
from sqlalchemy.orm import Session

@dataclass
class Context:
    report_id: str
    hospital_id: str
    db: Session          # 任意 Python 对象都能放，不要求可序列化

@tool
def save_parsed_result(data: str, runtime: ToolRuntime[Context]) -> str:
    """保存解析后的结构化结果"""
    ctx = runtime.context
    ctx.db.add(ParsedReport(report_id=ctx.report_id,
                            hospital_id=ctx.hospital_id, payload=data))
    ctx.db.commit()
    return "已保存"

@app.post("/parse/{report_id}")
async def parse(report_id: str, db: Session = Depends(get_db)):
    return agent.invoke(
        {'messages': [{'role': 'user', 'content': '解析这份报告'}]},
        context=Context(report_id=report_id, hospital_id="h001", db=db),
    )
```


这些东西**不能放 State**——State 会被 checkpointer 序列化落盘，DB session 没法也不应该被序列化；context 不落盘，正好。

> **选型口诀**：会随对话变化、需要跨轮记住 → State；本次请求的"身份和资源"、调用前就确定、不该让模型碰 → Context


---

## 五、回头看——D14 最值得记住的三件事

| 知识点               | 一句话本质                                               | 为什么要先搞清楚               |
| ----------------- | --------------------------------------------------- | ---------------------- |
| **LangChain 是什么** | 它不是 Agent 框架，是 LLM 应用的**标准接口层**                     | 后面所有内容都建立在这个认知上        |
| **生态分工**          | LangChain（框架）+ LangGraph（运行时）+ Deep Agents（harness） | 知道什么时候用哪把刀             |
| **create_agent**  | Agent = Model + Harness 的高层封装                       | 它是 LangChain 1.0 的核心入口 |

而这三件事背后，是 LangChain 整个框架的设计哲学——

> **抽象 LLM 应用里"能稳定下来的东西"，把"易变的东西"留给你配置。**
>
> 模型谁家、Prompt 怎么写、工具用哪些、检索怎么做——这些是易变的；
> 但 "调一次模型 / 渲染一段 Prompt / 解析一段输出" 这三类动作的接口形状——是能标准化的。

---

## 六、下一步：D15 把 ChatModel + PromptTemplate + LCEL 三件套一起讲透

今天建立了全局认知：LangChain 是什么、生态怎么分工、`create_agent` 怎么用。但我们一直没深入那三个核心组件——**ChatModel（模型层）、PromptTemplate（提示层）、LCEL（管道层）**。

明天 D15 要做的是：
1. **ChatModel**：统一接口的代价与收益，消息对象 vs 裸 dict，五件套方法
2. **PromptTemplate**：从字符串到数据对象，partial / invoke / MessagesPlaceholder
3. **LCEL**：把上面两件的"手工胶水"全部干掉——`prompt | model | parser`

最终把三件事串成一条链：

```python
chain = prompt | model | StrOutputParser()
chain.invoke({"history": history, "question": q})
```

