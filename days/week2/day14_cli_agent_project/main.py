"""
Day 14 - CLI Agent 项目
========================
知识点:
- 综合运用 Function Calling + ReAct + Structured Output
- 命令行交互设计
- Agent 工具注册与管理
- 完整 Agent 项目架构

实践任务: 构建一个完整的 CLI Agent，支持多种工具调用和对话
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from app.llm import client, chat
from app.config import DEFAULT_MODEL


def main():
    """Day 14 main entry point."""
    print("Day 14 - CLI Agent 项目")
    print("=" * 40)
    # TODO: Implement today's exercises
    pass


if __name__ == "__main__":
    main()
