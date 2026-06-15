# Agent Dev 101

![Agent Dev 101](./welcome.png)

两个月系统化学习 AI Agent 开发，从 LLM 基础到生产级多 Agent 系统。

**每日投入**: 2–3 小时 · **总天数**: 55 天

---

## 学习计划

完整计划 → [blog/learning-plan.md](./blog/learning-plan.md)

| 周次 | 主题 | 核心交付物 |
| :---: | ------ | ---------- |
| Week 1 | LLM 核心概念 | 多轮对话 CLI + Context Engineering 笔记 |
| Week 2 | Function Calling + ReAct + 结构化输出 | 从零实现 ReAct Agent + CLI 助手 |
| Week 3 | LangChain 基础 + RAG | LangChain Agent + RAG 文档问答系统 |
| Week 4 | LangChain 进阶 + LangGraph | LangGraph Agentic RAG 系统 |
| Week 5 | 多 Agent 系统 + MCP 协议 | 多 Agent 协作系统 + MCP Server |
| Week 6 | Harness Engineering + 框架探索 | Harness 改进报告 + 新框架复现 |
| Week 7 | 评估、安全与部署 | 可部署的 Agent API 服务 |
| Week 8 | 总结与最佳实践 | AI Agent 开发最佳实践与踩坑指南 |

---

## 学习笔记

| 编号 | 笔记 |
| :---: | ------ |
| W1-D1-01 | [Token 和 Embedding 基础知识](./blog/W1-D1-01%20token%20和%20embedding%20基础知识.md) |
| W1-D1-02 | [Embedding 概念与实战](./blog/W1-D1-02%20Embedding%20概念与实战.md) |
| W1-D1-03 | [Chat Templates 与角色系统](./blog/W1-D1-03%20Chat%20Templates%20与角色系统.md) |
| W1-D2-01 | [LLM 模型参数避坑指南](./blog/W1-D2-01%20LLM%20模型参数避坑指南：Agent%20开发者最该知道的事.md) |
| W1-D2-02 | [API 调用实战：用 Python SDK 完成第一次多轮对话](./blog/W1-D2-02%20API%20调用实战：用%20Python%20SDK%20完成你的第一次多轮对话.md) |
| W1-D2-03 | [多轮对话与消息管理](./blog/W1-D2-03%20多轮对话与消息管理：Token%20计数、截断策略和对话历史的正确打开方式.md) |
| W1-D3-01 | [Prompt Engineering 回顾](./blog/W1-D3-01%20Prompt%20Engineering%20回顾：从会写提示词到理解"信息设计".md) |
| W1-D3-02 | [什么是 Context Engineering](./blog/W1-D3-02%20什么是%20Context%20Engineering：从"写好提示词"到"设计信息系统".md) |
| W1-D4-01 | [Context Engineering 核心模式与实践](./blog/W1-D4-01%20Context%20Engineering%20核心模式与实践：从理论到落地.md) |
| W1-D4-02 | [Prompt Cache 全解析](./blog/W1-D4-02%20Prompt%20Cache%20全解析：原理、厂商对比与最佳实践.md) |
| W1-D5-01 | [什么是 AI Agent：不只是能聊天，而是能"做事"的系统](./blog/W1-D5-01%20什么是%20AI%20Agent：不只是能聊天，而是能"做事"的系统.md) |
| W1-D5-02 | [Workflow vs Agent：不是所有问题都需要 Agent](./blog/W1-D5-02%20Workflow%20vs%20Agent：不是所有问题都需要%20Agent.md) |
| W1-D6-01 | [Agent 设计模式总览：六大模式一图看懂](./blog/W1-D6-01%20Agent%20设计模式总览：六大模式一图看懂.md) |
| W1-D6-02 | [从零理解一个最简 Agent：用伪代码走通 Agent Loop](./blog/W1-D6-02%20从零理解一个最简%20Agent：用伪代码走通%20Agent%20Loop.md) |
| W2-D8-01 | [Function Calling：让模型从"只会说"到"能动手"的关键一步](./blog/W2-D8-01%20Function%20Calling：让模型从"只会说"到"能动手"的关键一步.md) |
| W2-D9-01 | [完整走通 Function Calling：从单工具到多工具编排](./blog/W2-D9-01%20完整走通%20Function%20Calling：从单工具到多工具编排.md) |
| W2-D10-01 | [ReAct 模式深入：从论文核心思想到 Thought-Action-Observation 循环](./blog/W2-D10-01%20ReAct%20模式深入：从论文核心思想到%20Thought-Action-Observation%20循环.md) |
| W2-D11-01 | [从零手写 ReAct Agent：Prompt 模板、循环控制、踩坑与改进方向](./blog/W2-D11-01%20从零手写%20ReAct%20Agent：Prompt%20模板、循环控制、踩坑与改进方向.md) |
| W2-D12-01 | [结构化输出全攻略：从 Prompt 求着到 Schema 摁着，让 LLM 老老实实吐 JSON](./blog/W2-D12-01%20结构化输出全攻略：从%20Prompt%20求着到%20Schema%20摁着，让%20LLM%20老老实实吐%20JSON.md) |
| W2-D13-01 | [第二周项目：用 Function Calling + ReAct + Rich UI 拼一只能跑的命令行 AI 助手](./blog/W2-D13-01%20第二周项目：用%20Function%20Calling%20%2B%20ReAct%20%2B%20Rich%20UI%20拼一只能跑的命令行%20AI%20助手.md) |
| W3-D14-01 | [LangChain 入门：抛开"框架"滤镜，看清它到底替你做了什么](./blog/W3-D14-01%20LangChain%20入门：抛开%22框架%22滤镜，看清它到底替你做了什么.md) |
| W3-D15-01 | [LangChain 三件套：ChatModel + PromptTemplate + LCEL](./blog/W3-D15-01%20LangChain%20三件套：ChatModel%20%2B%20PromptTemplate%20%2B%20LCEL.md) |

### 其他笔记

- [一文读懂：Loop Engineering 是个啥东西](./blog/一文读懂：Loop%20Engineering%20是个啥东西.md)

---

## 快速导航

- **学习计划**: [blog/learning-plan.md](./blog/learning-plan.md)
- **所有笔记**: [blog/](./blog/)
- **代码实践**: [days/](./days/)
