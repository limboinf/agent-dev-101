# Agent 设计模式总览：六大模式一图看懂

---

> 摘要：前两天学了 Agent 的定义和感知-推理-行动循环，但那只是 Agent 的"骨架"。真正让 Agent 从一个"会循环的程序"变成"能解决复杂问题的系统"的，是各种设计模式。这篇先把六大模式（ReAct、Reflection、Tool Use、Planning、Multi-Agent、Human-in-the-Loop）的全貌铺开，搞清楚每种模式解决什么问题、适用什么场景，以及它们之间的关系。下一篇再逐个深入剖析。


## 一、六大模式的全景地图

我读了一堆资料之后，把 Agent 设计模式整理成六个。先上一张全景图：
![](https://limbo.oss-cn-beijing.aliyuncs.com/wiki/20260418124423295.png)


**为什么这样分层？**

- **Layer 1 基础能力层**：ReAct 和 Tool Use 是所有 Agent 的地基。ReAct 解决"怎么循环"，Tool Use 解决"循环里能做什么"。没有这两层，Agent 就是个空壳。
- **Layer 2 增强能力层**：Reflection 让 Agent 能从错误中学习，Planning 让 Agent 能处理复杂任务。这两层让 Agent 从"能做事"变成"做得好"。
- **Layer 3 协作与安全层**：Multi-Agent 解决单 Agent 搞不定的大任务，HITL 确保人类对高风险决策有控制权。

---

## 二、六大模式速览

### 1. ReAct — 推理 + 行动的经典范式

**一句话**：让 LLM 一边想一边做，Thought → Action → Observation 循环。

**解决什么问题**：纯推理（CoT）只想不做，容易产生幻觉；纯行动（Act-only）只做不想，容易走弯路。ReAct 把两者结合起来。

**起源论文**：*ReAct: Synergizing Reasoning and Acting in Language Models*
**典型场景**：知识问答（需要查资料才能回答）、网页导航、信息收集任务
**代表实现**：LangChain 的 `create_agent()`

---

### 2. Reflection — 让 Agent 学会"复盘"

**一句话**：Agent 执行完任务后自我评价，发现不足，下次改进。

**解决什么问题**：Agent 可能给出错误的答案但自己不知道。Reflection 让它"回头看一眼"，像学生做完题再检查一遍。

**起源论文**：*Reflexion: Language Agents with Verbal Reinforcement Learning*
**典型场景**：代码生成（跑测试 → 看报错 → 修复）、内容写作（写完自评 → 修改）
**代表实现**：Anthropic 的 Evaluator/Optimizer 模式、Claude Code 的迭代修复循环

---

### 3. Tool Use — 给 Agent "长手脚"

**一句话**：让 LLM 调用外部工具（API、数据库、搜索引擎等），突破纯文本的限制。

**解决什么问题**：LLM 本身不能上网、不能算数学、不能查数据库。Tool Use 让它突破这些限制。

**起源论文**：*Toolformer: Language Models Can Teach Themselves to Use Tools*
**典型场景**：几乎所有 Agent 都需要 Tool Use——搜索、计算、代码执行、数据库查询
**代表实现**：OpenAI Function Calling API、Anthropic Tool Use、MCP（Model Context Protocol）

---

### 4. Planning — 先规划再执行

**一句话**：把复杂任务分解成子任务，制定执行计划，然后按计划一步步来。

**解决什么问题**：复杂任务直接开干容易走偏。先做计划，把"做什么"和"怎么做"分开，能回头、能调整。

**起源论文**：*Plan-and-Solve Prompting*
**典型场景**：旅行规划、复杂代码开发、科学研究、多步骤推理
**代表实现**：Devin（先规划再编码）、BabyAGI（任务分解+优先级排序）

---

### 5. Multi-Agent — 分工协作

**一句话**：多个 Agent 各有专长，分工合作完成大任务。

**解决什么问题**：单 Agent 的上下文窗口有限、注意力会分散、工具太多容易乱。分工让每个 Agent 专注做自己最擅长的事。

**典型场景**：软件开发团队（产品经理+程序员+测试）、内容生产线（研究员+写手+编辑）
**代表实现**：AutoGen（微软）、CrewAI、LangGraph Multi-Agent

---

### 6. Human-in-the-Loop — 人把关

**一句话**：Agent 在关键决策点暂停，等人类审批或反馈后再继续。

**解决什么问题**：Agent 不完美，可能在关键步骤犯错。HITL 让人类在重要节点介入，确保安全和质量。

**关键论文**：*A Survey on Large Language Model based Human-Agent Systems*
**典型场景**：金融交易审批、医疗诊断确认、发送重要邮件前的人工审核
**代表实现**：LangGraph 的 `interrupt_before` / `interrupt_after`、AutoGen 的 `UserProxyAgent`

---

## 四、六大模式的关系：不是独立的，是组合的

这是我花了最长时间才搞明白的一点——**这六个模式不是"六选一"，而是"搭积木"**。

```text
                    模式组合关系图

    基础循环（ReAct）
         │
         ├── + Tool Use ────────→ 能做更多事
         │         │
         │         ├── + Reflection ──→ 做得更好
         │         │
         │         ├── + Planning ────→ 能做更复杂的事
         │         │
         │         └── Multi-Agent ────→ 多个 ReAct 循环协作
         │                                    │
         └──────────── + HITL ──────────────→ 关键节点人类把关
```

**用一个类比来理解：**

- **ReAct** 是"干活的方法"——边想边做
- **Tool Use** 是"工具箱"——锤子、扳手、螺丝刀
- **Reflection** 是"工作复盘"——做完检查一遍
- **Planning** 是"施工图纸"——先画蓝图再动手
- **Multi-Agent** 是"组建团队"——一个人干不完就找帮手
- **HITL** 是"监理签字"——关键节点得让人确认

一个真正复杂的 Agent 系统，往往是这些模式的组合。比如 Claude Code：
- 底层是 **ReAct** 循环（读文件 → 分析 → 修改 → 测试 → 发现问题 → 继续改）
- 通过 **Tool Use** 调用各种工具（文件编辑、终端执行、搜索）
- 有 **Reflection** 能力（测试失败后反思错误并修复）
- 偶尔需要 **HITL**（不确定的修改会问你）

---

## 五、各模式适用场景速查表

| 任务类型 | 推荐模式 | 理由 |
|---------|---------|------|
| 简单问答 | 不需要 Agent | 直接 LLM 调用就够了 |
| 需要查资料才能回答 | ReAct + Tool Use | 需要搜索外部信息 |
| 代码生成 | ReAct + Tool Use + Reflection | 生成 → 测试 → 修复 循环 |
| 复杂分析报告 | Planning + Multi-Agent | 需要拆分子任务、多角色协作 |
| 自动化流水线 | Workflow（不是 Agent） | 固定流程用 Workflow 更稳定 |
| 高风险决策 | Agent + HITL | 关键节点需要人类确认 |
| 创意内容 | Reflection + HITL | 需要反复打磨 + 人类品味 |

**一个实用判断法：**
- 任务简单、流程固定 → 用 Workflow
- 需要灵活决策但只涉及一种能力 → ReAct + Tool Use
- 需要自我纠错 → 加上 Reflection
- 任务复杂需要拆分 → 加上 Planning
- 一个人搞不定 → 加上 Multi-Agent
- 出了错代价很大 → 加上 HITL

---

## 小结

今天的目标是"建立全局视野"，搞清楚六件事：

1. **ReAct** 是 Agent 的地基——Thought → Action → Observation 循环
2. **Tool Use** 是 Agent 的工具箱——让 LLM 突破纯文本的限制
3. **Reflection** 是 Agent 的复盘机制——自我评价、自我改进
4. **Planning** 是 Agent 的战略能力——先规划再执行
5. **Multi-Agent** 是 Agent 的团队模式——分工协作
6. **Human-in-the-Loop** 是 Agent 的安全网——关键节点人类把关

**核心认知**：这六个模式不是"六选一"，而是"搭积木"。越复杂的任务需要组合越多模式。从 ReAct 开始，根据需要逐层叠加。

> 💡 **预告**：下一篇我们把六大模式逐个拆开，详细分析每种模式的原理、论文、实现方式和适用场景。
