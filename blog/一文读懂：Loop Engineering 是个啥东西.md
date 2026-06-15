> Loop Engineering 本质上是就是 `/goal` 一个「能自己发现任务、分配任务、验证结果、决定下一步并在满足条件后自动停止」的自动化循环系统;

2026年6月初，OpenClaw创始人提到 "You shouldn't be prompting coding agents anymore. You should be designing loops that prompt your agents." 

然后社区讨论，热火朝天，就出现了 「agentic loop」和「loop engineering」这类概念, 然后慢慢发酵热起来了，大家都说 loop engineering 要替代 Harness engineering 了..

![](https://limbo.oss-cn-beijing.aliyuncs.com/wiki/20260615175718410.png)

今天这篇文章，我将结合社区的一些讨论和我的理解，带大家了解一下 Loop Engineering 到底是一个什么样的东西，它和Harness Enginneering区别。

## Loop Engineering vs Harness Engineering

开头提到「大家都说 loop engineering 要替代 Harness engineering 了」，那它俩到底啥区别？一句话：**Harness Engineering 是给单个 agent「穿装备」，Loop Engineering 是在装备之上设计「自动驾驶」。**

具体来说：

- **Harness Engineering（装备层）**：关注的是怎么把一个裸模型包装成可靠的 agent——给它工具、给它记忆、给它安全护栏。业界有个公式：`Agent = Model + Harness`。这一层解决的是"一个 agent 怎么靠得住"。

- **Loop Engineering（编排层）**：在 Harness 之上再加一层——设计一个自主循环，决定 agent 什么时候启动、做什么、做完怎么验证、下一步往哪走。这一层解决的是"一群 agent 怎么自己跑起来"。

|维度|Harness Engineering|Loop Engineering|
|---|---|---|
|层级|底层：包裹单个 agent|上层：编排 agent 的循环|
|关注点|单次会话的能力和约束（工具、记忆、护栏、错误恢复）|多轮循环的自主性（触发、分配、验证、停止条件）|
|类比|外骨骼：让 agent 能「动手」|自动驾驶：让 agent 知道「何时动手、怎么动」|
|开发者干嘛|定义工具、护栏、上下文|设计触发条件、任务路由、验证与停止逻辑|

所以与其说 Loop 替代 Harness，不如说 Loop 建立在 Harness 之上——你得先有靠得住的「零件」（Harness 层），才能拼出能自转的「流水线」（Loop 层）。

## Loop 的核心构件

![](https://limbo.oss-cn-beijing.aliyuncs.com/wiki/20260615181220160.png)

围绕 coding agents，目前社区比较共识的几个构件大致包括：

1、触发器（Trigger）：是什么事件让 loop 启动？例如：定时任务、有人开了 PR、CI 挂了、收到一条 Slack 指令等。

2、任务发现 / 工作队列：Loop 如何“找到要干的活”？比如从 issue、日志、监控告警、待办列表中筛选出合适任务，写入队列或 Worktree。

3、子代理（Sub-agents）：不是一个大而全的 agent，而是多个角色分工：写代码的、写测试的、做评审的、做重构的，各司其职，互相制衡（类似 maker-checker）。

4、插件 / 工具（Plugins/Connectors）：让 agent 用 GitHub、Git、CI、数据库、Issue 系统、Slack 等外部工具，真正能“动手”，而不是只给出建议。

5、状态与记忆（State/Memory）：loop 需要能记录当前进度、历史尝试、决策依据，通常会落到 repo 的文件（如 STATE.md）、数据库或任务系统中。

6、验证与停止条件（Verification & Stop Condition）：定义「什么时候算完成」「失败如何判定」「最多循环多少次」「最多花多少 token / 费用」等，防止失控和成本爆炸。

这些模块加起来，就是 Addy 文章里提的「五个构件 + 记忆」的 loop 设计思路。

有人把 Loop 的过程高度压缩成一句话：
“Goal → Agent → Verify → Repeat until done，难点在于定义『完成是什么』。”

![](https://limbo.oss-cn-beijing.aliyuncs.com/wiki/20260615175747309.png)



那么这一套 Loop 有哪两种方式能够实现呢？下面我们来详细了解一下

## ONE AGENT VS A FLEET
“一人干到底”的单 Agent 循环，和“团队协同作战”的舰队（多 Agent）循环，本质是两种不同规模和架构的 AI 工作流设计：前者适合专注、范围清晰的任务，后者适合复杂、多角色、多步骤的大项目.

![](https://limbo.oss-cn-beijing.aliyuncs.com/wiki/20260615175932549.png)

### 基本定义

- 单 Agent 循环：一个 Agent 自己完成“发现需求 → 规划 → 执行 → 自检/验证 → 调整再执行”的完整闭环，就像一个人一边写代码、一边自测、自改，持续迭代到满意为止。

- 舰队/多 Agent 循环：有一个编排/Orchestrator Agent 负责接收目标，拆分子任务并分派给多个专业 Agent；每个 Agent 自己内部也跑“发现→规划→执行→验证”的循环，形成一棵任务树，直到顶层目标完成。


你可以把单 Agent 看成“全栈独立开发者”，舰队看成“有 PM、架构师、前端、后端、QA 的完整团队”。

### 单 Agent 循环的特点

- 一个大脑，一条主循环：所有推理、工具调用、记忆、反思都在同一个 Agent 的上下文里进行，状态集中、心智模型统一。
    
- 适合的任务：
    
    - 目标明确、路径基本线性的任务（例如：实现一个中等复杂度的函数、写一篇博客、整理一份报表）。
    - 对全局一致性要求高，希望一个“脑子”一直记着上下文，不需要切换角色。
        
- 优点：
    
    - 架构简单：实现、部署、监控、调试都比较直观（看一条调用链即可）。
        
    - 延迟和成本可控：通常只是一条推理链，token 模式比较稳定。[](https://redis.io/blog/single-agent-vs-multi-agent-systems/)
        
    - 行为可预测：不容易出现“多个 Agent 各说各话”的协调问题。
        
- 缺点：
    
    - 容易“脑子被撑爆”：当任务跨多个领域、多工具、多上下文时，一个 Agent 的上下文和推理链会变得非常复杂，容易丢线或性能下降。
        
    - 专业化受限：难以在同一次循环里用完全不同的 persona/策略去解决子问题，只能靠 prompt 动态切换。

### 舰队循环（多 Agent）的特点

- 任务分解 + 多角色协作：通常有一个 Orchestrator/Planner Agent 负责：
    
    - 解析高层目标
    - 规划子任务树
    - 选择合适的专业 Agent（编码、测试、检索、评审等）执行
    - 汇总并验证结果。

- 每个 Agent 是一个“局部循环单元”：它对自己那块目标做“发现 → 规划 → 执行 → 验证”的局部闭环，再把结果反馈回上层。
    
- 适合的任务：
    
    - 跨多个领域的复杂项目，例如：需要检索资料、写代码、跑测试、部署、做安全审计、写文档的完整开发流水线。
    - 有明确职能边界（安全、合规、审批等），或者需要多轮交叉验证的场景。
        
- 优点：
    
    - 专业化和可扩展性：可以为不同任务设计不同 Agent（不同工具集、不同长记忆、不同策略）。要增加能力，只需增加新角色和对应 Loop。
    - 复杂度承载能力更强：能并行处理不同子任务，整体吞吐和覆盖面更大。
    - 易于注入治理/审计：可以专门放一个“审计/安全 Agent”做最后的检查。

- 缺点：
    
    - 协调成本高：需要设计清晰的协议（消息格式、状态机、任务路由），否则容易出现死循环、任务遗失或结果冲突。
    - 调试复杂：错误可能发生在某个 Agent、或者在编排逻辑上，诊断路径较长。
    - 成本和延迟：多 Agent 意味着多 LLM 调用，如果 Loop 没设计好，可能产生很多冗余对话和 token 消耗。

下面这张表可以帮你快速判断：

|维度|单 Agent 循环适用场景|舰队循环/多 Agent 适用场景|
|---|---|---|
|任务复杂度|步骤较少、路径基本线性、依赖链简单|多步骤、多分支、跨多个子领域或系统|
|上下文范围|集中在一条主线、同一数据域|涉及多个数据源、多种工具、多种角色|
|质量需求|可接受“一个脑子”的判断和自检|需要多轮交叉验证、独立审查|
|开发成本|原型快速、实现简单、运维成本低|初期设计和实现成本高，需要编排、监控、日志系统|
|调试与治理|调试简单，一条链路就能复现问题|需要分 Agent 追踪、可观测性和分布式日志|
|性能与成本|延迟低、token 模式稳定|可能更贵更慢，但整体吞吐和任务成功率更高|
|可扩展性|扩展时可能越来越“胖”，prompt 很长|可以增加新 Agent/工具，保持模块化|

## 应用场景

例如：
![](https://limbo.oss-cn-beijing.aliyuncs.com/wiki/20260615180843163.png)
每个循环都有相同的骨架：
**目标 → 行动 → 检查 → 修复 → 重复直至完成。**

