"""
Day 26 - LangGraph 工具集成
=============================
知识点:
- LangGraph 中的 Tool Node
- ToolNode 与 tools_condition
- 人机协作 (Human-in-the-loop)
- 检查点与状态持久化

实践任务: 构建一个带工具调用和人工确认的 LangGraph Agent
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from app.llm import client, chat
from app.config import DEFAULT_MODEL


def main():
    """Day 26 main entry point."""
    print("Day 26 - LangGraph 工具集成")
    print("=" * 40)
    # TODO: Implement today's exercises
    pass


if __name__ == "__main__":
    main()
