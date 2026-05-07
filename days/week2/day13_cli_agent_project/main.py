"""
Day 13 - 第二周项目: 命令行 AI 助手
=====================================

知识点:
- 综合运用 Function Calling + ReAct + Structured Output
- 真实可用的工具 (Wikipedia / Calculator / Weather)
- 命令行交互 + Rich 美化 (思考过程 / 工具调用 / 工具结果 / 最终回答 各自不同样式)
- Agent 工具注册与管理, 多轮对话历史维护

运行方式:
    uv run python -m days.week2.day13_cli_agent_project.main

可用命令:
    /exit   退出
    /reset  清空对话
    /help   显示帮助

示例提问:
    - 北京今天天气怎么样？如果超过 30 度推荐一杯冷饮
    - 帮我搜一下"图灵奖", 然后告诉我图灵生于哪一年
    - 计算 (12 * 7 + sqrt(2)) / 3 是多少
"""

from __future__ import annotations

import sys
from pathlib import Path

# 让脚本既能 `python -m ...` 也能 `python main.py` 执行
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from days.week2.day13_cli_agent_project import ui
from days.week2.day13_cli_agent_project.agent import ReActAgent
from days.week2.day13_cli_agent_project.tools import TOOL_REGISTRY


def _read_user_input() -> str | None:
    """带提示符地读一行用户输入, Ctrl-D / Ctrl-C 返回 None。"""
    try:
        return ui.console.input("\n[bold cyan]👤 You[/bold cyan] › ").strip()
    except (EOFError, KeyboardInterrupt):
        return None


def _handle_command(cmd: str, agent: ReActAgent) -> bool:
    """处理 /xxx 类型的内置命令, 返回 True 表示 main loop 应继续读取下一条输入。"""
    if cmd in {"/exit", "/quit", "/q"}:
        ui.render_system("再见 👋")
        sys.exit(0)
    if cmd == "/reset":
        agent.reset()
        ui.render_system("对话已清空, 开启新会话。")
        return True
    if cmd == "/help":
        ui.render_help()
        return True
    ui.render_error(f"未知命令: {cmd}, 输入 /help 查看可用命令。")
    return True


def main() -> None:
    agent = ReActAgent()

    ui.render_banner(model=agent.model, tools=list(TOOL_REGISTRY.keys()))

    turn = 0
    while True:
        user_input = _read_user_input()
        if user_input is None:
            ui.render_system("再见 👋")
            break
        if not user_input:
            continue

        if user_input.startswith("/"):
            _handle_command(user_input, agent)
            continue

        turn += 1
        ui.render_turn_rule(turn)

        try:
            agent.chat(user_input)
        except Exception as exc:  # noqa: BLE001
            ui.render_error(f"Agent 执行出错: {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    main()
