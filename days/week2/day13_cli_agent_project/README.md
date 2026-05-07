# Day 13 · 第二周项目 — 命令行 AI 助手

> **目标**：把第二周学到的 Function Calling、ReAct、Structured Output 串成一个能跑、能用、好看的 CLI Agent。

---

## 1. 你将拥有什么

一个跑在终端里的 **「小助手」**，它会：

- 调用 **维基百科** 查百科知识
- 用 **Python 计算器** 求解数学表达式
- 通过 **公共天气 API** 查中国大陆城市天气
- 把整个 **「思考 → 调工具 → 看结果 → 再思考 → 回答」** 的过程，用 **Rich** 不同颜色、面板、emoji 展示出来
- 支持多轮对话、`/reset` 清空、`/exit` 退出

视觉效果（示意）：

```diagram
╭─ 🤖 Day 13 · 命令行 AI 助手 ───────────────────────────╮
│   模型  qwen3.5-flash                                  │
│   工具  wikipedia_search, calculator, weather_lookup   │
│   命令  /exit · /reset · /help                         │
╰────────────────────────────────────────────────────────╯
─────────────────────── Turn 1 ──────────────────────────
👤 You › 北京今天多少度？超过 30 度推荐一杯冷饮

╭─ 💭 Thinking ─────────────────────────╮  ← 黄色斜体
│ 用户问北京当前气温, 我需要先调...     │
╰───────────────────────────────────────╯
╭─ 🔧 Action #1 · weather_lookup ───────╮  ← 紫色面板
│ { "city": "北京" }                    │
╰───────────────────────────────────────╯
╭─ 📦 Observation #1 · weather_lookup ──╮  ← 灰色面板
│ 【北京】温度 25°C ...                 │
╰───────────────────────────────────────╯
╭─ 🤖 Assistant ────────────────────────╮  ← 绿色 + Markdown
│ 北京当前 25°C，没到 30°C，今天就...   │
╰───────────────────────────────────────╯
```

---

## 2. 项目结构

```
day13_cli_agent_project/
├── README.md          # 本教程
├── main.py            # CLI 入口 (REPL)
├── agent.py           # ReAct 循环 + Function Calling
├── tools.py           # 三个工具的实现 + JSON Schema
└── ui.py              # Rich 渲染层 (思考 / 工具 / 结果 / 回答)
```

四个文件、各司其职，**改一个不影响另外三个**——这就是 Agent 项目落地时最朴素的关注点分离：

| 模块 | 关心什么 | 不关心什么 |
| --- | --- | --- |
| `tools.py` | 这个工具怎么实现、参数 schema | Agent 怎么用它 |
| `agent.py` | ReAct 循环、消息维护、工具分发 | 怎么把过程显示给用户 |
| `ui.py`    | 用什么颜色、什么面板渲染什么事件 | 业务逻辑 |
| `main.py`  | 用户怎么输入、怎么处理 `/cmd` | LLM 与工具的细节 |

---

## 3. 工具实现细节

### 3.1 Wikipedia 搜索 — 直接调 MediaWiki API

第三方 `wikipedia` / `wikipedia-api` 库历史包袱重 + 在国内代理环境下行为诡异。我们直接两步调 MediaWiki Action API，逻辑透明、可控：

```python
# Step 1: opensearch -> 候选标题
GET /w/api.php?action=opensearch&search=量子计算&limit=3

# Step 2: extracts (exintro=1, exsentences=N) -> 取首段纯文本摘要
GET /w/api.php?action=query&prop=extracts&exintro=1&exsentences=3&titles=量子计算机
```

**关键点**：
- 必须带 `User-Agent`，否则维基会返回 HTML 反爬页。
- `httpx` 会自动读取 `HTTP_PROXY` / `HTTPS_PROXY` 环境变量，国内开发记得开代理。

### 3.2 计算器 — `simpleeval` 安全沙箱

千万不要用 `eval()` 让模型生成的字符串直接进 Python 解释器。`simpleeval` 是专门做"安全数学表达式求值"的库：

```python
from simpleeval import SimpleEval

evaluator = SimpleEval(
    functions={"sqrt": math.sqrt, "log": math.log, ...},   # 白名单
    names={"pi": math.pi, "e": math.e},
)
evaluator.eval("sqrt(2) + log(100, 10)")  # -> 3.4142...
```

只允许白名单里的函数和常量，模型再怎么"创造性发挥"也跑不出沙箱。

### 3.3 天气 — `wttr.in` 公共服务

[wttr.in](https://wttr.in) 是一个不需要 API Key 的天气服务，对中文城市名也友好：

```python
GET https://wttr.in/北京?format=j1&lang=zh
```

返回结构化 JSON，我们提取关键字段（温度/体感/风向/能见度）拼成中文摘要返回给模型。

> 中国大陆若需要更稳定/精度更高的天气，可换成 [心知天气](https://www.seniverse.com/) / [高德天气](https://lbs.amap.com/api/webservice/guide/api/weatherinfo) 等需注册 Key 的服务，工具签名不变即可热替换。

---

## 4. ReAct 循环是怎么跑起来的

把 `agent.py` 的核心循环抽出来看（伪代码版）：

```python
messages = [system_prompt, user_input]
for step in range(MAX_ITERATIONS):
    msg = llm.chat(messages, tools=SCHEMAS)   # 让模型决策
    messages.append(msg)

    if msg.content:                            # 模型在调工具前写的"独白"
        ui.render_thought(msg.content)         # ← 黄色面板

    if not msg.tool_calls:                     # 没有要调的工具 → 这就是最终回答
        ui.render_final_answer(msg.content)
        return msg.content

    for call in msg.tool_calls:                # 否则执行所有 tool_call
        ui.render_tool_call(call.name, call.args)
        result = TOOL_REGISTRY[call.name](**call.args)
        ui.render_tool_result(call.name, result)
        messages.append({"role": "tool", "content": result, ...})
```

核心要点（每一条都对应一类常见 bug）：

1. **每轮 assistant 消息都要追加回 `messages`**，下一轮模型才能看到自己说过什么。
2. **`tool_call_id` 必须严格对应**，否则 OpenAI 会拒绝整个请求。
3. **`MAX_ITERATIONS` 是死循环救命阀**。模型偶尔会陷入"调工具 → 不满意 → 再调 → ..."的死循环。
4. **工具异常一律转字符串回灌**，让模型自我修复，比直接 `raise` 好得多。
5. **思考过程的来源**：通过 System Prompt 显式要求模型"调工具前先写一段中文解释"，OpenAI Chat Completions 会把这段文字放在 `assistant.content` 里，与 `tool_calls` 并存——这就是我们渲染的"💭 Thinking"。

---

## 5. Rich UI 的事件 → 样式映射

| 事件 | Rich 样式 | 视觉作用 |
| --- | --- | --- |
| 启动 Banner | `Panel(border=cyan)` + Table.grid | 一眼看到模型/工具 |
| 用户输入提示 | `console.input("[bold cyan]👤 You[/]")` | 与 Assistant 区分 |
| 思考过程 | `Panel(yellow italic)` | 弱化、暗示"过程而非结论" |
| 工具调用 | `Panel(magenta)` + JSON `Syntax` 高亮 | 强调"这是动作" |
| 工具返回 | `Panel(bright_black)` 等宽 | 不抢戏的"原始数据" |
| 最终回答 | `Panel(green)` + `Markdown` | 视觉收束、最显眼 |
| 错误     | `Panel(red)` | 立即吸引注意 |
| 等待     | `console.status(spinner=...)` | 让用户知道没卡死 |

**为什么要做这些区分？** 当 Agent 走 5 步以上时，没有视觉锚点就是一片文字海。颜色 + emoji + 面板边框，让人能 1 秒钟在屏幕上定位"哪一段是思考、哪一段是结果"。

---

## 6. 如何运行

### 前置

`.env`（参考 [.env.example](../../../.env.example)）至少要有：

```
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1   # 或 OpenAI 官方
OPENAI_MODEL=qwen3.5-flash                                          # 任何支持 tool calling 的模型
```

> 模型必须支持 `tools` 参数（即 OpenAI 风格的 Function Calling）。Qwen / GPT-4o-mini / Claude (via OpenAI 兼容层) 都行。

### 启动

```bash
uv run python -m days.week2.day13_cli_agent_project.main
```

### 试试这些 prompt

```
1. 北京今天天气怎么样？超过 30 度的话推荐一杯冷饮
2. 阿兰·图灵是谁？他出生在哪一年？
3. 一杯 16 oz 美式 大约多少 mL？精确到 1 位小数
4. 帮我对比一下「上海」和「广州」现在的气温差
```

第 4 题会触发**两次 weather_lookup 调用**——可以观察到 Agent 自动并行/串行调用，并在最后做差。

---

## 7. 还可以怎么扩展

这个项目刻意保持小巧（< 500 行），方便你照着改：

- **加工具**：在 `tools.py` 里写函数 + 一份 schema → 注册到 `TOOL_REGISTRY` 即可，agent.py 一行不用改。
- **流式输出**：把 `chat.completions.create(stream=True)` 接入 `ui.console`，最终回答可以一字一字显示。
- **结构化最终答案**：让 Agent 最后返回 Pydantic 模型（呼应 Day 12），UI 层用 `Table` 渲染，例如旅游计划。
- **持久化对话**：把 `agent.messages` 序列化到文件，做 `--continue` 命令。
- **长对话压缩**：超过 N 轮时调用一次 LLM 把旧消息总结掉（呼应 Day 4 Context Engineering）。

---

## 8. 学到了什么

跑通这一天，你应该能讲清楚：

- ✅ 为什么 `tool_calls` 与 `tool_call_id` 必须匹配
- ✅ ReAct 的循环为什么不用 LangChain/LangGraph 也能写
- ✅ "思考过程"在 OpenAI 协议里到底是什么字段
- ✅ 怎么用 Rich 把一团文本切成"过程 vs 结论"
- ✅ 工具异常该 `raise` 还是该字符串回灌

带着这些理解去看下周的 LangChain，你会发现框架做的事情不神秘——它把这里的每一个分支都封装了一个名字而已。
