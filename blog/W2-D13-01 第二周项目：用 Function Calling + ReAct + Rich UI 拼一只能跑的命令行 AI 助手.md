# 第二周项目：用 Function Calling + ReAct + Rich UI 拼一只能跑的命令行 AI 助手

---

> 摘要：第二周从 D8 的 Function Calling、D10-D11 的 ReAct、到 D12 的结构化输出，把"让模型动手"这件事掰开了讲了五天。今天 D13 是周项目日——把这一周的散件全部焊到一起，做一个 **真的能在终端里跑的 CLI Agent「小助手」**：能查维基百科、能做数学计算、能查中国大陆城市天气，**思考过程 / 工具调用 / 工具返回 / 最终回答各自有不同颜色和面板的 Rich UI**，看一眼就知道 Agent 现在在干嘛。整个项目刻意控制在 4 个文件、不到 500 行代码——故意做小，方便你照着改。这篇笔记把项目的 **设计思路、踩坑、关键代码** 全部讲一遍，重点不是"代码贴出来你抄"，而是 **"为什么 ReAct 循环长这样"、"为什么思考过程是 assistant.content"、"为什么工具异常要回灌字符串而不是 raise"** 这些 Agent 工程里反复出现的小决策。读完之后你应该有信心：**不用任何 Agent 框架，也能从零搓一个能用的 Agent**——这是下周开始学 LangChain 之前必须先打通的"内功"。

---

## 一、为什么要"手搓"这一层

下周开始，我们就要进 LangChain / LangGraph 了。框架很香——`create_tool_calling_agent` 一行调用搞定一切。但 **如果你没手写过一遍 ReAct 循环，框架对你来说就是黑盒，调试时看 trace 都看不懂**。

这周项目的真正目标，是让你以后看 LangChain 源码时能说一句："噢，这就是我那 80 行 `agent.py` 套了三层抽象。" 

具体到这一天，我给自己定的小目标只有三条：

1. **真工具**——别用 mock。Wikipedia 真去查、计算器真求值、天气真调 API。
2. **真 ReAct**——不是单次 tool_call，要能多步调用、能基于上一步结果决定下一步。
3. **真 UI**——CLI 不能就是一坨 `print`。**思考、动作、观察、回答** 四类信息要在视觉上一眼能分清。

听上去都是基本功，但真要全部跑通且不翻车，能压住一周内能学到的所有知识点。

---

## 二、最终长这样

```
uv run python -m days.week2.day13_cli_agent_project.main
╭─────────────────────────── 命令行 AI 助手 ──────────────────────────╮
│                                                                                                                                               │
│  模型  qwen3.5-flash                                                                                                                          │
│  工具  wikipedia_search, calculator, weather_lookup                                                                                           │
│  命令  /exit 退出 · /reset 清空对话 · /help 帮助                                                                                                 │
╰──────────────── ReAct + Tool Calling + Rich UI ───────────────────╯
```

![](https://limbo.oss-cn-beijing.aliyuncs.com/wiki/20260507162611413.png)

![](https://limbo.oss-cn-beijing.aliyuncs.com/wiki/20260507162725450.png)

---

## 三、四个文件、各管一摊

```
day13_cli_agent_project/
├── tools.py      # 三个工具 + JSON Schema
├── agent.py      # ReAct 循环 + Function Calling
├── ui.py         # Rich 渲染层
└── main.py       # REPL 入口
```

**分层的原则只有一句**：每个文件改起来不影响别的文件。

| 模块 | 关心什么 | 不关心什么 |
| --- | --- | --- |
| `tools.py` | 这个工具的实现、参数 schema | Agent 怎么用它 |
| `agent.py` | ReAct 循环、消息维护、工具分发 | 怎么把过程显示给用户 |
| `ui.py`    | 用什么颜色 / 面板渲染什么事件 | 业务逻辑 |
| `main.py`  | 用户怎么输入、怎么处理 `/cmd` | LLM 与工具的细节 |

听上去废话，但 **80% 的早期 Agent 项目失败在"工具实现里写了 Rich print，UI 里又调了 LLM"**——没分层，改一处崩一片。

---

## 四、工具实现：三个真实可用的 Tool

### 4.1 Wikipedia 搜索 — 直接调 MediaWiki API

最早我装的是 PyPI 上的 `wikipedia` 库，结果在国内代理环境下直接报 `JSONDecodeError`——库内部用的是老 endpoint，对代理处理也不规范。换 `wikipedia-api` 也一样，它把 `httpx.Client(transport=httpx.HTTPTransport())` 写死，**等于绕开了 httpx 的环境变量代理读取**。

最后我直接两步调 MediaWiki Action API，逻辑透明、可控：

```python
def wikipedia_search(query: str, lang: str = "zh", sentences: int = 3) -> str:
    api = f"https://{lang}.wikipedia.org/w/api.php"
    headers = {"User-Agent": "agentic-agent-101/0.1 ..."}  # ★ 必带, 不然返 HTML

    with httpx.Client(timeout=15.0, headers=headers) as client:
        # Step 1: opensearch -> 候选标题
        _, titles, _, urls = client.get(api, params={
            "action": "opensearch", "search": query,
            "limit": 3, "namespace": 0, "format": "json",
        }).json()
        if not titles:
            return f"未找到与 '{query}' 相关的维基百科词条。"

        # Step 2: extracts -> 取首段纯文本摘要
        title, url = titles[0], urls[0]
        data = client.get(api, params={
            "action": "query", "prop": "extracts",
            "explaintext": 1, "exintro": 1,
            "exsentences": sentences, "redirects": 1,
            "titles": title, "format": "json",
        }).json()
        page = next(iter(data["query"]["pages"].values()))
        return f"【{title}】\n{page['extract']}\n\n来源: {url}"
```

**坑总结**：

1. Wikipedia 强制要求 `User-Agent`——不带就被反爬规则挡掉返 HTML，下游 `.json()` 直接炸。
2. 第三方 wiki 库别迷信，自己 `httpx` 直调更可控；遇到深度封装的库行为诡异时，**剥到底层 HTTP 反而最快**。
3. 国内开发别忘了 `httpx` 会自动读 `HTTP_PROXY` / `HTTPS_PROXY` 环境变量。

### 4.2 计算器 — `simpleeval` 安全沙箱

`simpleeval` 是专门做"安全数学表达式求值"的库——白名单函数 + 字面量解析，不可能跳出沙箱：

```python
from simpleeval import SimpleEval

evaluator = SimpleEval(
    functions={"sqrt": math.sqrt, "log": math.log, "sin": math.sin, ...},
    names={"pi": math.pi, "e": math.e},
)
evaluator.eval("sqrt(2) + log(100, 10)")  # → 3.4142...
```

外层 try/except 把 `Exception` 转字符串返回——**让模型看到错误信息后自我修正**，比 `raise` 让整个 Agent 挂掉好得多。这是 Agent 工具设计里的一个反复出现的模式：**异常要变成 Observation，不要变成程序崩溃**。

### 4.3 天气 — `wttr.in` 公共 API（无需 Key）

`wttr.in` 是个老牌天气服务，**对中文城市名也认**，最关键的是不用注册：

```python
def weather_lookup(city: str) -> str:
    url = f"https://wttr.in/{city}"
    params = {"format": "j1", "lang": "zh"}
    headers = {"User-Agent": "curl/8.0"}  # 不加 UA 会拿到 HTML 页

    with httpx.Client(timeout=10.0) as client:
        data = client.get(url, params=params, headers=headers).json()

    current = data["current_condition"][0]
    area = data["nearest_area"][0]
    desc = current.get("lang_zh", [{}])[0].get("value") or current["weatherDesc"][0]["value"]

    return (
        f"【{area['areaName'][0]['value']}】\n"
        f"- 天气: {desc}\n"
        f"- 气温: {current['temp_C']}°C (体感 {current['FeelsLikeC']}°C)\n"
        f"- 湿度: {current['humidity']}%\n"
        f"- 风向: {current['winddir16Point']} {current['windspeedKmph']} km/h\n"
    )
```

若想要更高精度 / 更稳定，换 [心知天气](https://www.seniverse.com/)、[高德天气](https://lbs.amap.com/api/webservice/guide/api/weatherinfo) 即可——**只要工具签名 `weather_lookup(city: str) -> str` 不变，agent.py 一行不用改**。这是 tool 抽象的好处：**实现可以热替换**。

### 4.4 工具 schema：模型怎么"看见"工具

光写函数还不够，得告诉模型这些工具的签名。这就是 OpenAI tools 参数要的 JSON Schema：

```python
SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "weather_lookup",
            "description": (
                "查询中国大陆城市的当前天气, 返回温度、体感、天气状况、风向风速等。"
                "城市名可用中文 (如 '北京'、'上海') 或拼音 (如 'Beijing')。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名称, 例如 '北京'"},
                },
                "required": ["city"],
            },
        },
    },
    # ... wikipedia_search / calculator
]
```

**`description` 不是文档，是 prompt 的一部分**。模型选不选你的工具、传什么参数，**几乎完全取决于你这段描述写得清不清楚**。我踩过的坑：

- 早期写 `description: "查天气"`——模型一会儿调用一会儿不调用，迷之随机。
- 改成 `description: "查询中国大陆城市的当前天气, 返回温度..."`——稳定调用率从 60% 直接到 99%。

**结论：工具的 description 要像写产品文档，把"什么场景用、参数怎么写、返回什么"全说清楚**。这是 D8 的核心思想，落到工程里就是这件小事。

---

## 五、ReAct 循环：80 行讲清楚 Agent 内核

`agent.py` 的核心循环抽出来看（去掉 UI 调用）：

```python
def chat(self, user_input: str) -> str:
    self.messages.append({"role": "user", "content": user_input})

    for step in range(1, self.max_iterations + 1):
        # 1) 让 LLM 决策: 要么直接回答, 要么发起 tool_call
        msg = self.client.chat.completions.create(
            model=self.model,
            messages=self.messages,
            tools=tools_module.SCHEMAS,
            tool_choice="auto",
            temperature=0.2,
        ).choices[0].message
        self.messages.append(self._serialize_assistant(msg))

        # 2) 模型在调工具前的"独白" -> 这就是思考过程
        if msg.content:
            ui.render_thought(msg.content)

        # 3) 没有 tool_call -> 这是最终回答, 收工
        if not msg.tool_calls:
            ui.render_final_answer(msg.content)
            return msg.content

        # 4) 有 tool_call -> 全部执行, 把结果回灌成 tool 消息
        for call in msg.tool_calls:
            args = json.loads(call.function.arguments or "{}")
            ui.render_tool_call(call.function.name, args, step)
            try:
                result = TOOL_REGISTRY[call.function.name](**args)
            except Exception as exc:
                result = f"工具执行异常 ({type(exc).__name__}): {exc}"
            ui.render_tool_result(call.function.name, result, step)
            self.messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "name": call.function.name,
                "content": result,
            })
    # 5) 超过最大迭代仍没收敛 -> 强制收尾
    return "抱歉, 我反复调用工具仍没能完成这个请求, 请换种方式重新提问。"
```

每一行都对应一类常见 bug，单独拎出来讲：

### 5.1 `messages` 必须每轮追加 assistant 消息

```python
self.messages.append(self._serialize_assistant(msg))
```

漏了这一行 → 下一轮 LLM 看不到自己上一轮说过什么 → 重复决策、死循环。**Agent 的状态全在 messages 里**，每一轮都要把 assistant 和 tool 的消息追加回去，**包括有 tool_calls 的那条 assistant 消息本身**。

### 5.2 `tool_call_id` 必须严格对应

```python
self.messages.append({
    "role": "tool",
    "tool_call_id": call.id,  # ★ 必须是 assistant.tool_calls[i].id
    ...
})
```

OpenAI 的协议要求：**每条 `role: tool` 的消息必须能在前一条 assistant 消息的 `tool_calls` 里找到匹配的 `id`**。漏一个、错一个，整个请求 400。

### 5.3 `MAX_ITERATIONS` 是死循环救命阀

模型偶尔会陷入"调工具 → 不满意 → 再调 → ..."的死循环。设个上限（我用 20）兜底——**到达上限就强制返回一句歉意，别让用户在终端干瞪眼**。

### 5.4 工具异常一律转字符串回灌

```python
try:
    result = TOOL_REGISTRY[name](**args)
except Exception as exc:
    result = f"工具执行异常 ({type(exc).__name__}): {exc}"
```

不要 raise。模型看到 `"工具执行异常: 城市 'XX' 不存在"` 之后，会自己改参数重试。**让模型在循环里"自我修复"，比让程序崩在用户面前好 100 倍**。

### 5.5 思考过程到底是什么字段

最容易被忽视的细节：**OpenAI Chat Completions 协议里，`assistant` 消息的 `content` 和 `tool_calls` 是可以同时存在的**。也就是说，模型可以在调工具前先写一段自然语言（"我打算调 weather_lookup 查北京"）再发起 tool_call。

```python
# 一条 assistant 消息可能长这样
{
    "role": "assistant",
    "content": "我需要先查一下北京的实时天气...",   # ← 这段就是"思考"
    "tool_calls": [{"id": "...", "function": {...}}]
}
```

我们在 System Prompt 里加了一条强制要求：

```
1. 在调用工具之前, 先用一段简短的【中文自然语言】写出你的思考过程,
   解释 "为什么需要调用工具" 以及 "打算用什么参数"。
```

模型听话照做，思考就出现在 `assistant.content` 里，被 UI 层渲染成黄色面板。**这就是"💭 Thinking" 的来源**——不是什么神秘的 reasoning 字段，就是协议里早就允许的普通 content。

> 注：GPT-o1 / DeepSeek-R1 这类 reasoning 模型有独立的 reasoning content 字段，那是另一回事。我们这里讲的是普通模型怎么"装出"思考。

---

## 六、Rich UI：为什么要给四类事件分四种样式

很多人写 CLI Agent 的 UI 就是 `print(f"调用 {name}...")` 完事。**当 Agent 走 5 步以上时，没有视觉锚点的输出就是一片文字海**——你在屏幕上 scroll 半天找不到"哪一段是思考、哪一段是结果"。

Rich 让我们能把 4 类事件用 4 种视觉风格区分开：

| 事件 | Rich 样式 | 视觉作用 |
| --- | --- | --- |
| 启动 Banner | `Panel(border=cyan)` + `Table.grid` | 一眼看到模型/工具 |
| 用户输入 | `console.input("[bold cyan]👤 You[/]")` | 与 Assistant 的 🤖 区分 |
| 思考过程 | `Panel(yellow italic)` | **弱化**——这是过程不是结论 |
| 工具调用 | `Panel(magenta)` + JSON `Syntax` 高亮 | **强调**——这是动作 |
| 工具返回 | `Panel(bright_black)` + 等宽 | **不抢戏**——原始数据 |
| 最终回答 | `Panel(green)` + `Markdown` | **视觉收束**——最显眼 |
| 错误     | `Panel(red)` | **立即吸睛** |
| 等待     | `console.status(spinner=...)` | **让用户知道没卡死** |

**色彩心理学小贴士**：

- 黄色 = 注意但非关键 → 思考过程（你可以快速扫过）
- 紫色 = 决策、行动 → 工具调用（重要事件）
- 灰色 = 数据、低权重 → 工具返回（原始信息，要看可以看）
- 绿色 = 成功、终点 → 最终回答（视觉上的"收束"）
- 红色 = 错误、警告 → 异常（立即吸引注意）

每个面板的实现非常简单，比如思考过程：

```python
def render_thought(text: str) -> None:
    if not text or not text.strip():
        return
    console.print(
        Panel(
            Text(text.strip(), style="yellow italic"),
            title="💭 Thinking",
            border_style="yellow",
            padding=(0, 1),
        )
    )
```

**不到 10 行代码，但用户体验直接上一个台阶**。Rich 这个库对 Agent 项目的性价比是真的高。

---

## 七、踩过的坑（实战集锦）

### 坑 1：`wikipedia` / `wikipedia-api` 在国内代理下都不靠谱

`wikipedia` 库内部 endpoint 老旧，`wikipedia-api` 库强制 `httpx.HTTPTransport()`（绕过 env proxy）。**结论：简单场景直接 `httpx` 调 MediaWiki Action API**——两步、二三十行、完全可控。

### 坑 2：`response.json()` 之前一定要 `raise_for_status()`

```python
# ❌ 错的
data = client.get(url).json()   # 服务器返了 HTML, 这里 JSONDecodeError

# ✅ 对的
r = client.get(url)
r.raise_for_status()             # 让 HTTP 错误以 HTTPError 抛出
data = r.json()
```

很多反爬服务会返 200 + HTML（"请验证你不是机器人"），不 raise 的话错误信息会被 `.json()` 屏蔽成"莫名其妙的 JSONDecodeError"。

### 坑 3：模型偶尔给非法 JSON 当 tool arguments

```python
# arguments 字段可能是个不完整 / 非 JSON 字符串
args = json.loads(call.function.arguments or "{}")
```

我加了 try/except 兜底——`json.loads` 失败时把原始字符串以 `_raw` 字段塞进去，让 UI 至少能渲染、错误也作为 Observation 喂回模型让它重试。**别让一个非法 JSON 把整个 chat 干掉**。

### 坑 4：`assistant.content` 为空时不要渲染空面板

模型在最后一步给最终回答时，往往 `content` 有内容但 `tool_calls` 为 None；中间步骤时反过来。**`render_thought("")` 会画一个空面板**——丑而且让人困惑。所以加一条防呆：

```python
def render_thought(text: str) -> None:
    if not text or not text.strip():
        return
    ...
```

小细节，但是直接决定 UI 体验。

### 坑 5：tool_call 里 `arguments` 是 string，不是 dict

```python
# OpenAI 返回的结构
{
    "function": {
        "name": "weather_lookup",
        "arguments": '{"city": "北京"}',  # ★ 字符串！不是 dict
    }
}
```

新人 100% 会踩——直接 `**call.function.arguments` 一定报错。必须先 `json.loads`。

### 坑 6：长 tool 输出会刷屏（但模型仍要看完整版）

我在 UI 里截到 1500 字符，但 **`messages.append` 时塞的是完整结果**。两套逻辑分开：**给人看的截短，给模型看的不动**。否则会出现"模型记住了完整数据但屏幕上看不见"的诡异调试体验。

---

## 八、扩展方向（留给你练手）

这个项目刻意做小，方便你照着改。下面几条可以作为后续 D14 之前的可选练习：

1. **加工具**：在 `tools.py` 写函数 + schema → 注册到 `TOOL_REGISTRY` 即可，agent.py 一行不用改。试试加一个 `read_file` / `web_fetch`。
2. **流式输出**：把 `chat.completions.create(stream=True)` 接上，最终回答可以一字一字打出来。需要在 UI 层用 `Live` 渲染。
3. **结构化最终答案**：让 Agent 最后用 `client.beta.chat.completions.parse(response_format=Pydantic)` 返回结构化数据（呼应 D12），UI 用 `Table` 渲染——比如旅游计划。
4. **持久化对话**：把 `agent.messages` 序列化到文件，加 `--continue` 命令——你就有了一个简易的 `claude-code` / `aider`。
5. **长对话压缩**：超过 N 轮时调一次 LLM 把旧消息总结掉，呼应 D4 的 Context Engineering。

---

## 九、小结

把今天打通的几件事拎出来：

1. **Agent 的内核就是一个 while 循环**——LLM 决策 → 执行工具 → 把结果回灌 → 继续。框架的所有抽象都建立在这之上。手写一遍，下周看 LangChain 时就知道每个 API 在做什么。
2. **工具的好坏，一半看 description**。`description` 不是文档，是 prompt 的一部分，写得越像产品说明，模型选用的命中率越高。
3. **思考过程不是魔法字段**——OpenAI 协议允许 `assistant.content` 和 `tool_calls` 同时存在，前者就是"调工具前的独白"。System Prompt 里强制要求模型先写 content，思考过程就出现了。
4. **工具异常要回灌字符串，不要 raise**。让模型在循环里自我修复，比让程序崩好得多。
5. **MAX_ITERATIONS 是死循环救命阀**——任何 ReAct 实现都必须有，少则几次，多则一两位数。
6. **CLI Agent 的 UI 至少要分 4 类样式**——思考 / 调用 / 返回 / 回答。Rich 让这件事变成 10 行代码，不做就是文字海，做了体验立刻翻倍。

一条可以带走的工程判断：**任何"能用框架"的项目都先手搓一遍最小版本**。手搓不是复古，是为了让框架对你不再是黑盒——这是从"会调 API"到"能 debug Agent"的分水岭。

> 💡 **预告**：本周到此结束。下周 D14 进入 W3 第三周，开始上 LangChain——你今天手搓的 80 行 ReAct 循环，会被 `create_tool_calling_agent` + `AgentExecutor` 包成一行调用。带着今天的理解去看，会发现框架并不神秘，它只是把这里的每一个分支都封装了一个名字而已。代码在 [`days/week2/day13_cli_agent_project/`](https://github.com/limboinf/agent-dev-101/tree/main/days/week2/day13_cli_agent_project)，clone 下来 `uv run python -m days.week2.day13_cli_agent_project.main` 直接跑。
