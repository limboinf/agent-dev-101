"""
UI 层 (基于 Rich)
==================

把 Agent 内部的不同事件用不同视觉样式渲染出来, 让用户一眼分辨:

- 用户输入        : 青色边框 + 👤
- 模型思考        : 黄色斜体 + 💭  (think tag / 推理过程)
- 工具调用        : 紫色面板, 显示函数名和参数  + 🔧
- 工具返回        : 灰色面板, 等宽显示原始结果   + 📦
- 模型最终回答    : 绿色边框 + 🤖
- 系统提示/错误   : 红色 + ⚠️

所有渲染统一通过 module-level 的 `console` 对象, 方便测试时替换。
"""

from __future__ import annotations

import json
from typing import Any

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

# 全局唯一 Console, 整个 CLI 都从这里输出
console = Console()


# ============================================================
# 启动 Banner
# ============================================================

def render_banner(model: str, tools: list[str]) -> None:
    """打印欢迎面板, 列出当前模型与可用工具。"""
    table = Table.grid(padding=(0, 2))
    table.add_column(style="bold cyan", justify="right")
    table.add_column(style="white")
    table.add_row("模型", model)
    table.add_row("工具", ", ".join(tools))
    table.add_row("命令", "[bold]/exit[/] 退出 · [bold]/reset[/] 清空对话 · [bold]/help[/] 帮助")

    console.print(
        Panel(
            table,
            title="🤖 [bold cyan]Day 13 · 命令行 AI 助手[/bold cyan]",
            subtitle="[dim]ReAct + Tool Calling + Rich UI[/dim]",
            border_style="cyan",
            padding=(1, 2),
        )
    )


# ============================================================
# 分隔轮次
# ============================================================

def render_turn_rule(turn: int) -> None:
    console.print(Rule(f"[dim]Turn {turn}[/dim]", style="bright_black"))


# ============================================================
# 用户输入 (实际上 prompt_toolkit/input 已经回显, 这里仅用于回放)
# ============================================================

def render_user(text: str) -> None:
    console.print(Panel(text, title="👤 You", border_style="cyan", padding=(0, 1)))


# ============================================================
# 思考过程 (模型的内部独白)
# ============================================================

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


# ============================================================
# 工具调用 (Action)
# ============================================================

def render_tool_call(name: str, args: dict[str, Any], step: int) -> None:
    pretty_args = json.dumps(args, ensure_ascii=False, indent=2)
    body = Syntax(pretty_args, "json", theme="monokai", background_color="default")

    console.print(
        Panel(
            body,
            title=f"🔧 Action #{step} · [bold magenta]{name}[/bold magenta]",
            border_style="magenta",
            padding=(0, 1),
        )
    )


# ============================================================
# 工具返回 (Observation)
# ============================================================

def render_tool_result(name: str, result: str, step: int) -> None:
    # 太长时截断, 避免刷屏 (模型仍能看到完整结果)
    display = result if len(result) <= 1500 else result[:1500] + "\n…(已截断)"
    console.print(
        Panel(
            Text(display, style="white"),
            title=f"📦 Observation #{step} · [bold]{name}[/bold]",
            border_style="bright_black",
            padding=(0, 1),
        )
    )


# ============================================================
# 模型最终回答
# ============================================================

def render_final_answer(text: str) -> None:
    console.print(
        Panel(
            Markdown(text or "(无回答)"),
            title="🤖 Assistant",
            border_style="green",
            padding=(1, 2),
        )
    )


# ============================================================
# 系统/错误提示
# ============================================================

def render_system(msg: str) -> None:
    console.print(f"[bold cyan]ℹ[/bold cyan]  {msg}")


def render_error(msg: str) -> None:
    console.print(
        Panel(
            f"[bold red]{msg}[/bold red]",
            title="⚠️  Error",
            border_style="red",
            padding=(0, 1),
        )
    )


# ============================================================
# 帮助
# ============================================================

def render_help() -> None:
    table = Table(title="可用命令", border_style="cyan")
    table.add_column("命令", style="bold magenta")
    table.add_column("说明", style="white")
    table.add_row("/exit", "退出对话")
    table.add_row("/reset", "清空对话历史 (开启新会话)")
    table.add_row("/help", "显示本帮助")
    console.print(table)


def render_thinking_status():
    """返回一个 status context manager, 用于在等待模型时显示 spinner。"""
    return console.status("[bold cyan]模型思考中...[/bold cyan]", spinner="dots")


def render_tool_status(name: str):
    return console.status(f"[bold magenta]执行工具 {name} ...[/bold magenta]", spinner="dots12")
