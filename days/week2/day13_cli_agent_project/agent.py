"""
Agent 核心 (ReAct + Function Calling)
======================================

把第 8-12 天学到的东西串到一起:

- Function Calling: 由 OpenAI Chat Completions 的原生 tools 接口完成
- ReAct 循环      : while 模型仍在请求工具调用 -> 执行 -> 把结果回灌, 直到出现自然语言回答
- 思考过程         : 通过 system prompt 提示模型在调用工具前先用一段简短文本说明意图,
                    这段文本会被 UI 以 "💭 Thinking" 高亮渲染
- 多轮对话         : 维护一份 messages list, 每轮把 user / assistant / tool 消息追加进去
- 异常恢复         : 工具异常一律转成字符串作为 tool message 回灌, 让模型自我修复, 同时设置最大迭代防死循环

外部只需要:
    agent = ReActAgent()
    text = agent.chat("北京今天天气怎么样？超过 30 度推荐冷饮")
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from openai import OpenAI
from openai.types.chat import ChatCompletionMessage

from app.config import settings
from app.llm import client as default_client

from . import tools as tools_module
from . import ui

# 用一段精炼的 System Prompt 引导 Agent 的行为方式
SYSTEM_PROMPT = """你是一个名为「小助手」的命令行 AI 助手, 擅长结合工具完成用户的提问。

你拥有以下工具:
- wikipedia_search: 查询百科知识
- calculator: 计算数学表达式
- weather_lookup: 查询中国大陆城市的实时天气

行为约定:
1. 在调用工具之前, 先用一段简短的【中文自然语言】写出你的思考过程, 解释:
   "为什么需要调用工具" 以及 "打算用什么参数"。这段文字会单独展示给用户。
2. 一次只调用最必要的工具, 拿到结果后再决定是否继续调用其它工具。
3. 不能用工具解决的问题 (例如闲聊、写作), 直接回答即可, 不要强行调工具。
4. 最终回答要简洁、清晰, 必要时使用 Markdown (列表、加粗) 增强可读性。
5. 涉及实时数据 (天气、新闻) 必须以工具返回结果为准, 不要凭记忆猜测。
"""

MAX_ITERATIONS = 20


@dataclass
class ReActAgent:
    """带 Rich UI 渲染的 ReAct Agent。"""

    model: str = settings.openai_model
    client: OpenAI = field(default_factory=lambda: default_client)
    max_iterations: int = MAX_ITERATIONS

    # 多轮对话的消息列表, 跨 chat() 调用持续累积
    messages: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.reset()

    # --------------------------------------------------------
    # 公共 API
    # --------------------------------------------------------

    def reset(self) -> None:
        """清空对话历史, 仅保留 system prompt。"""
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    def chat(self, user_input: str) -> str:
        """处理一条用户输入, 完成完整的 ReAct 循环, 返回最终文本。"""
        self.messages.append({"role": "user", "content": user_input})

        for step in range(1, self.max_iterations + 1):
            assistant_msg = self._call_llm()
            self.messages.append(self._serialize_assistant(assistant_msg))

            tool_calls = assistant_msg.tool_calls or []

            # 1) 抽出思考过程, 优先级:
            #    a. reasoning_content (Qwen/DeepSeek-R1 的"思维链"独立字段)
            #    b. content + tool_calls 同时存在时, content 即"调工具前的独白"
            thought = self._extract_thought(assistant_msg, has_tool_calls=bool(tool_calls))
            if thought:
                ui.render_thought(thought)

            # 2) 没有工具调用 -> assistant.content 即最终回答
            if not tool_calls:
                final = assistant_msg.content or "(模型没有给出回答)"
                ui.render_final_answer(final)
                return final

            # 3) 执行所有 tool_calls (OpenAI 支持并行多个), 把结果作为 tool 消息回灌
            for call in tool_calls:
                self._handle_tool_call(call, step)

        # 超过最大迭代仍没有最终回答 -> 强制收尾
        ui.render_error(f"达到最大迭代次数 {self.max_iterations}, 强制结束。")
        fallback = "抱歉, 我反复调用工具仍没能完成这个请求, 请换种方式重新提问。"
        self.messages.append({"role": "assistant", "content": fallback})
        ui.render_final_answer(fallback)
        return fallback

    # --------------------------------------------------------
    # 内部实现
    # --------------------------------------------------------

    def _call_llm(self) -> ChatCompletionMessage:
        with ui.render_thinking_status():
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                tools=tools_module.SCHEMAS,
                tool_choice="auto",
                temperature=0.2,
            )
        return response.choices[0].message

    @staticmethod
    def _extract_thought(msg: ChatCompletionMessage, has_tool_calls: bool) -> str:
        """抽取本轮的"思考过程"文本。

        - Qwen / DeepSeek-R1 等会把推理放在非标字段 reasoning_content 里;
          OpenAI SDK 不在类型中暴露, 但可以通过 model_extra / model_dump 拿到。
        - 标准 OpenAI: 当 tool_calls 与 content 同时返回时, content 就是
          "调工具前的独白", 此时把它当思考。
        - 没有 tool_calls 时, content 是最终回答, 不算思考。
        """
        # 1) reasoning_content (provider extension)
        extra = getattr(msg, "model_extra", None) or {}
        reasoning = (extra.get("reasoning_content") or "").strip()
        if reasoning:
            return reasoning

        # 2) content as "pre-action monologue"
        if has_tool_calls and msg.content and msg.content.strip():
            return msg.content.strip()

        return ""

    @staticmethod
    def _serialize_assistant(msg: ChatCompletionMessage) -> dict[str, Any]:
        """把 SDK 返回的 message 对象转成可放进 messages 列表的 dict。"""
        payload: dict[str, Any] = {"role": "assistant", "content": msg.content}
        if msg.tool_calls:
            payload["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in msg.tool_calls
            ]
        return payload

    def _handle_tool_call(self, call: Any, step: int) -> None:
        name = call.function.name
        # 模型可能给出非法 JSON, 这里宽容处理
        try:
            args = json.loads(call.function.arguments or "{}")
        except json.JSONDecodeError:
            args = {"_raw": call.function.arguments}

        ui.render_tool_call(name, args, step)

        fn = tools_module.TOOL_REGISTRY.get(name)
        if fn is None:
            result = f"错误: 未注册的工具 '{name}'"
        else:
            try:
                with ui.render_tool_status(name):
                    result = fn(**args)
            except TypeError as exc:
                # 参数对不上的友好错误, 让模型自己改正
                result = f"参数错误: {exc}"
            except Exception as exc:  # noqa: BLE001
                result = f"工具执行异常 ({type(exc).__name__}): {exc}"

        ui.render_tool_result(name, result, step)

        self.messages.append(
            {
                "role": "tool",
                "tool_call_id": call.id,
                "name": name,
                "content": result,
            }
        )
