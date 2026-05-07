# ReAct 模式深入：从论文核心思想到 Thought-Action-Observation 循环

---

> 摘要：昨天我们用 Function Calling 写了一个能跑的小 Agent，但你会发现一个问题——**模型的思考过程是黑箱的**。它直接吐出 `tool_calls`，凭什么调这个工具？为什么是这些参数？你看不到。今天要补上的，就是这一块"思考的可见层"——ReAct（Reasoning + Acting）。这是 2022 年 Yao 等人在 ICLR 投出的那篇论文（arXiv:2210.03629），看似只是在 Action 之前多加了一句 Thought，却意外地解决了两件大事：CoT 的"幻觉"和 Act-only 的"瞎走"。这篇笔记我把论文里最关键的思想、轨迹示例、实验数字、失败模式都拆开讲一遍——读完你会理解为什么所有现代 Agent 框架（LangChain、LangGraph、OpenAI Agents SDK）的循环骨架其实都是 ReAct 的变体。

## 一、为什么 ReAct 是 Agent 史上最重要的论文之一？

![](https://limbo.oss-cn-beijing.aliyuncs.com/wiki/20260428084658644.png)

先抛一个判断：**如果让我在 2022–2024 这两年里挑一篇"必须读"的 Agent 论文，那一定是 ReAct**。不是因为它最复杂，恰恰相反——它的核心思想简单到一句话就能讲完：

> 让模型在每次行动前，先用一段自然语言"想一下"。

就这么个改动，干净利落地解决了当时两条主流路线各自的痛点：

- **纯 CoT（Chain-of-Thought）路线**：模型只想不做。但问题是 — **它是个静态黑箱**，模型只能用自己脑子里的知识在那儿"自言自语"。一旦碰到训练数据里没有的事实就出"幻觉"。
- **纯 Act-only 路线**：模型只做不想，能跟环境交互了，但**没有抽象目标，容易迷路**。

ReAct 把这两条路线缝在了一起：每一步先生成一段 **Thought**（推理痕迹，不影响外部环境），再生成一个 **Action**（真正动手），然后接收 **Observation**（环境反馈）。

**Thought 是给自己看的笔记，Action 是给世界发的命令，Observation 是世界对命令的回应。**

---

## 二、ReAct 的三个核心动作 

```text
问题：发明万维网（WWW）的人，目前在哪个机构任职？

Thought 1: 这是一个两个问题。我得先查"谁发明了万维网"，再查这个人现在的任职情况。
Action 1:  Search[World Wide Web inventor]
Observation 1: 万维网由蒂姆·伯纳斯-李（Tim Berners-Lee）于 1989 年在
              CERN 工作期间提出……

Thought 2: 发明者是 Tim Berners-Lee。下一步搜他本人，看现在在哪里工作。
Action 2:  Search[Tim Berners-Lee]
Observation 2: 没有找到 [Tim Berners-Lee]。相似条目：
              ['Sir Tim Berners-Lee', 'Tim Berners-Lee Foundation',
               'Berners-Lee', ...]

Thought 3: 直接搜没命中。换成消歧后的名字再试一次。
Action 3:  Search[Sir Tim Berners-Lee]
Observation 3: ……他目前是 MIT 计算机科学与人工智能实验室（CSAIL）教授，
              同时领导 W3C（万维网联盟）。

Thought 4: 信息齐了：MIT CSAIL 教授 + W3C 负责人。可以给最终答案了。
Action 4:  Finish[MIT CSAIL 教授，并领导 W3C]
```

有几个细节非常值得抠一下：

1. **Thought 1 是任务分解**：把"发明者目前在哪任职"拆成两步——先查"谁发明的"，再查"这个人现在在哪"。
2. **Thought 3 是异常处理**：Search 没命中 → 模型没卡死，而是切换策略（用 disambiguation 后的名字再搜一次）。
3. **Thought 4 是答案合成**：最后一步把前面所有 Observation 串起来，给出 `Finish`。

如果你把所有 Thought 抹掉只留 Action + Observation，这条轨迹瞬间变成 Act-only——模型很可能在 Search 失败那步就懵了。Thought 不只是"装饰"，它是模型给自己写的工作记忆（working memory）。

---

## 三、Thought / Action / Observation — 各自承担什么职责？

把三者职责说清楚，是写好 ReAct prompt 的前提。

### Thought：模型生成的、不影响环境的"自言自语"

论文里把 Thought 的作用归纳为五种，我把每种类型都用上篇笔记那个**天气 + 计算器 Agent**的例子重新写了一遍，更好理解：

| Thought 类型 | 作用                  | 例子                                                 |
| ---------- | ------------------- | -------------------------------------------------- |
| 任务分解       | 把目标拆成可执行的子目标        | "用户问温差，我得先查上海温度，再算它和 30 的差。"                       |
| 注入常识       | 把模型自己的世界知识引进来       | "气温超过 30°C 通常意味着炎热，用户大概率想知道差多少。"                   |
| 提取关键信息     | 从长 Observation 里挑重点 | "工具返回 '多云, 32°C, 湿度 78%'，我只需要 32 这个数字。"            |
| 跟踪进度       | 记录"我做到哪一步了"         | "天气已经查到了 32°C，还差一步：算 32 - 30。"                     |
| 异常处理       | 调整失败的计划             | "calculate 报参数错误，我换成传 '32 - 30' 而不是 '32-30°C' 试试。" |

发现了吗？**Thought 几乎全是模型在跟自己对话**——做计划、抓重点、纠错。它不解决问题，但它让"解决问题的过程"变得可观察、可控。


**关键点**：Thought **不进入环境**。它只是被追加进对话上下文，让模型在下一步 generation 时能看到自己之前的推理。这一点决定了 Thought 不需要任何"真实性"约束——就是模型自己的草稿纸，写错了也没关系，下一步还能改。


### Action：模型对外部世界发出的"指令"

如果说 Thought 是模型在自己脑子里嘀咕，那 Action 就是模型**伸手去碰真实世界**——调一个 API、查一次数据库、跑一段计算、发一封邮件。它会真的发生，也真的会留下痕迹，所以我们说它有"副作用"。

Action 有两条硬性约束：

**约束 1：必须是工具集里"认得"的操作，参数也得对得上签名。**

模型不能随手编一个工具名出来。它能用的 Action 只能从你给它注册的那一套里选，参数类型/字段也要符合工具的定义。比如昨天那个天气 + 计算器 Agent，能发出的 Action 只有这两种：

```text
get_weather(city="上海")
calculate(expression="32 - 30")
```

如果模型生成了 `get_weather("上海的天气")`，参数不符合签名 → 工具调用就会失败。

**约束 2：每发出一个 Action，环境必须回一个 Observation。无论成功还是失败。**

这是 ReAct 循环能转下去的根本前提。模型的每一步推理，都要靠上一步的 Observation 当输入；如果某次 Action 发出去之后**没有任何反馈**，模型就彻底瞎了——它不知道该重试、该换策略，还是该继续下一步。

举两个对比就很清楚：
- ✅ `calculate("32 - 30")` → 返回 `2`：模型拿到结果，可以接着 Thought "差 2 度，给用户回话"。
- ✅ `calculate("32 - 30°C")` → 返回 `Error: 表达式含非法字符 °C`：虽然失败，但模型知道是参数问题，下一步会改成 `calculate("32 - 30")` 重试。
- ❌ `send_email(...)` → 啥都不返回：模型不知道邮件发出去没，下一步要么死循环重发，要么直接放弃任务。

所以写工具时有个反直觉的原则：**不要让工具返回 `None` 或空字符串**，哪怕是"没什么可说的"也要明确说一句 `"邮件已发送"` / `"操作成功，无返回值"`。

### Observation：环境的反馈，是事实而非生成

Observation 不由 LLM 生成，**它是环境（Wikipedia API、计算器、文件系统、HTTP 接口、数据库）真实返回的内容**。这就是 ReAct 比纯 CoT "更可信"的根本原因——Observation 是 ground truth，模型再怎么会编也编不出 Wikipedia 的真实页面、编不出计算器算出的真实数字。

举个对比就很直观：
- **CoT 模式**：你问"32°C 比 30°C 高几度？" → 模型直接答"2°C"。看起来对，但万一题目稍微复杂点（比如华氏摄氏混着算），模型很容易自信地编一个错答案。
- **ReAct 模式**：你问同样的问题 → 模型 Thought "我要算 32 - 30" → Action `calculate("32 - 30")` → Observation `2` → 答 2°C。这次的"2"是计算器真实算出来的，而不是模型猜的。

记住这个三元组：**Thought 是主观的（模型自言自语），Action 是意图（模型想干什么），Observation 是客观事实（世界回了什么）。三者交错出现，构成 ReAct 的轨迹。**

---

## 四、循环的终止条件 — 不是无限想下去

ReAct 是个 while 循环，必须有终止条件。论文里规定了三种：

1. **模型主动 `Finish[answer]`** — 最常见的正常终止，模型认为信息够了，提交答案。
2. **达到最大步数 `max_steps`** — 论文里 HotpotQA 设的是 7 步，FEVER 是 5 步。超出就强制截断（一般会再让模型基于已有 Observation 给个 best-effort 答案）。论文里 footnote 提到："7 步以内能解 99% 的题，再多也不会变好。"
3. **环境/工具异常** — 极端情况下回退（比如连续 N 次工具失败）。

**为什么必须有 max_steps？** 因为 ReAct 有一个非常典型的失败模式：**重复行为陷阱（repetitive steps）**——模型会陷在同一个 Thought + Action 里出不来，比如反复调用同一个搜索词、反复尝试一个无效操作。所以你写代码时，`max_iterations` 不只是兜底，而是必备保险丝。

---

## 五、ReAct 的核心循环 — 用图说话

把前面讲的所有东西整合成一张流程图，这就是后面所有 Agent 框架的"心脏"：

```text
                  ┌─────────────────────────┐
                  │  User Question / Goal   │
                  └────────────┬────────────┘
                               │
                               ▼
        ┌────────────────────────────────────────────┐
        │  Prompt = SystemPrompt + Few-Shot          │
        │           + History (T₁-A₁-O₁ T₂-A₂-O₂ ...)│
        │           + Question                       │
        └────────────────────────┬───────────────────┘
                                 │
                                 ▼
                       ┌─────────────────┐
                       │     LLM call    │ ◄─────────────┐
                       └────────┬────────┘               │
                                │                        │
                                ▼                        │
              ┌───────── parse output ─────────┐         │
              │                                │         │
              ▼                                ▼         │
      ┌───────────────┐                ┌──────────────┐  │
      │ Thought + Act │                │ Thought +    │  │
      │ (continue)    │                │ Finish[ans]  │  │
      └───────┬───────┘                └──────┬───────┘  │
              │                                │         │
              ▼                                ▼         │
      ┌───────────────┐                ┌──────────────┐  │
      │ execute tool  │                │   RETURN     │  │
      │   in env      │                │   answer     │  │
      └───────┬───────┘                └──────────────┘  │
              │                                          │
              ▼                                          │
      ┌───────────────┐                                  │
      │  Observation  │                                  │
      └───────┬───────┘                                  │
              │                                          │
              └──── append T/A/O to history ─────────────┘
                       (until max_steps or Finish)
```

伪代码版本（D11 实战时这就是骨架）：

```python
def react(question, max_steps=7):
    history = []                    # 累积的 Thought / Action / Observation
    for step in range(max_steps):
        prompt = build_prompt(question, history)
        output = llm(prompt, stop=["Observation:"])  # 关键：在 Observation 处截断
        thought, action = parse(output)              # 解析出 Thought + Action

        if action.name == "Finish":
            return action.arg                         # 正常终止

        observation = execute(action)                 # 在环境里执行
        history.append((thought, action, observation))

    return "Reached max steps without Finish"        # 兜底
```

注意第 6 行那个 `stop=["Observation:"]` — 这是 ReAct prompt 的一个小但关键的实现细节：**让模型在生成 `Observation:` 之前就停下来**，不要让它自己幻想环境的反馈。这是论文里没明说但代码里必须有的细节。明天 D11 实战会反复用到。

---

## 六、ReAct 是 Agent 的"OS 内核" — 一个心智模型

学到这里，可以做一个心智模型上的飞跃了。回想一下昨天写的那个 `run_agent`——它其实就是一个"穿了 Function Calling 外套"的 ReAct 循环。把昨天的代码逐行映射到 ReAct 的概念上：

| 你昨天写的代码                                   | ReAct 概念    | 区别       |
| ----------------------------------------- | ----------- | -------- |
| 模型 chain-of-thought（虽然你看不见，但它内部"想"了）      | Thought     | 隐式而非显式输出 |
| `msg.tool_calls`（结构化的 JSON）               | Action      | 结构化而非文本协议 |
| `messages.append({"role": "tool", ...})`  | Observation | 用 message role 标记，本质一样 |
| `for i in range(max_iterations):`         | for-loop    | 完全一样     |
| `if not msg.tool_calls: return msg.content` | Finish      | 用"没调工具"代替显式 Finish |

是不是一一对应？**Function Calling 只是 ReAct 的"协议升级版"**——OpenAI 把"Thought / Action / Observation"这套文本协议，通过后训练直接刻进了模型权重里，所以你不用再写 prompt 让它按格式输出，直接给 tools 就行。但**循环骨架完全没变**。

再放大一层：所有现代 Agent 框架本质上都是 ReAct 的工程化包装。

| 概念          | ReAct 论文           | OpenAI Function Calling | LangChain / LangGraph        |
| ----------- | ------------------ | ----------------------- | ---------------------------- |
| Thought     | 自然语言推理痕迹           | 模型隐式推理                  | `agent_scratchpad` / 中间步骤    |
| Action      | `Search[x]` 文本     | `tool_calls` JSON       | `AgentAction` 对象             |
| Observation | Wikipedia API 返回   | `role: tool` 消息         | `AgentObservation`           |
| 循环驱动        | for max_steps loop | 多轮 chat completion      | `AgentExecutor.invoke()` 内部循环 |
| 终止信号        | `Finish[answer]`   | 没有 `tool_calls` 的 message | `AgentFinish`                |

不同的只有三件事：
1. **协议从文本变成了 JSON**（更稳定、更易解析）。
2. **Thought 从显式变成隐式**（模型可以不输出 Thought，但实际后训练里是有的）。
3. **加了一堆工程外壳**：状态机（LangGraph）、记忆（LangChain Memory）、工具注册中心、可观测性。

所以，如果你只能记住一件事，就记这个：**ReAct 是 Agent 的 while 循环。Function Calling 是这个循环里的"动作协议"。框架是循环外面的工程外壳。** 三者是同一根藤上的瓜。

---

## 七、几个常见误区

### 误区 1：以为 Thought 只是"装饰"，可以省

不能省。**任务越长程、动作越多，Thought 的价值越大。** 论文里在 ALFWorld（让 Agent 在文字游戏里完成"把刀放到台面上"这类多步任务）上，加了 Thought 的 ReAct 比 Act-only 高了整整 26 个百分点（71% vs 45%）；甚至比用 10 万条样本训练出来的模仿学习模型还要好近 1 倍。**短任务靠 CoT 的"硬想"也许够用，长任务必须靠 Thought 来分解和追踪状态。**

### 误区 2：以为 ReAct 比 CoT 一定强

不是。当任务能用模型内部知识解决时（比如简单的常识题），CoT 反而更高效——少了一次次外部 API 调用的延迟。**ReAct 的杀手锏是"必须查外部知识/操作外部世界"的场景**：比如查天气、查数据库、操作文件系统。这是 D5 那篇 Workflow vs Agent 的延伸——不是所有问题都需要 Agent，也不是所有 Agent 都需要 ReAct。

### 误区 3：以为 ReAct 解决了幻觉

只解决了一半。**ReAct 把"事实幻觉"几乎消除了**（因为每一步都有外部 Observation 兜底），但它带来了一个新毛病：**"鬼打墙"——重复推理错误**，模型有时候会卡在错误状态里出不来（上一节那个 `put knife 1` 的例子）。这就是为什么后来 Reflexion / Self-Refine 这类工作要给 Thought 加上反思层。

### 误区 4：以为 Thought 必须很长很完整

不必。论文里明确说，在 ALFWorld 这种动作密集型任务上 "reasoning traces 只需稀疏地出现在最关键的位置"（sparse reasoning）。每个 Action 前都强行写一大段 Thought 反而会浪费 Token、模糊重点。**Thought 是手段，不是目的——只在"需要做决策"的拐点处写就够了**，比如计划开始时、收到意外 Observation 时、要给最终答案前。

---

## 八、小结

回顾今天搞明白的几件事：

1. **ReAct 的核心思想一句话：让模型在每次 Action 前先用自然语言写一段 Thought**。Thought 是给自己看的工作记忆，Action 是给环境发的命令，Observation 是环境的事实反馈。
2. **三者职责不同**：Thought 主观（模型自言自语，不影响环境）、Action 是意图（进入环境）、Observation 是客观事实（环境真实回的内容，不能由 LLM 编）。
3. **HotpotQA 里只有三个动作**：`Search[x]` / `Lookup[x]` / `Finish[x]`。`Finish` 就是循环的终止信号——没有它，循环不知道何时停。
4. **循环必须有终止条件**：模型主动 Finish、达到 max_steps（论文用 7）、或工具异常兜底。否则容易陷入"鬼打墙"——同一段 Thought + Action 反复出现却没人打断。
5. **实现细节关键**：自己手写 ReAct 时，LLM 调用要在 `Observation:` 处截断（`stop=["Observation:"]`），不让模型自己幻想环境反馈——明天 D11 会反复用到这个技巧。
6. **ReAct = Agent 的"OS 内核"**：你昨天写的 Function Calling Agent，本质上就是个 ReAct 循环；所有 LangChain / LangGraph / OpenAI Agents SDK 的执行引擎也都是。Function Calling 只是把文本协议升级成了 JSON 协议，核心循环没变。

一条可以带走的经验：**ReAct 不是某个具体的库或 API，它是一种"在每次行动前显式推理"的范式。** 理解了这个范式，你看任何 Agent 框架都不再迷路——所有花里胡哨的功能，剥到核心都是这个 Thought → Action → Observation 循环。

> 💡 **预告**：今天我们把 ReAct 的"理论 + 论文"嚼透了，明天 D11 我们就要**从零用 Python 实现一个 ReAct Agent**——不靠任何框架，不用 OpenAI 的 Function Calling，纯靠 Prompt 工程让模型按 "Thought / Action / Observation" 格式输出，自己解析、自己分发工具、自己拼接历史。你会亲手撞见三个真实的坑：Prompt 模板里 stop word 怎么设、模型偶尔输出格式错乱怎么修、循环陷入重复怎么打断。把这一遍走完，未来你再用 LangChain 或 LangGraph，就只是在调"被人包好的 ReAct"而已。
