"""
Day 27 - LangGraph 高级特性
=============================
知识点:
- 子图 (Subgraph) 与模块化
- 状态管理高级模式
- 流式输出与事件处理
- 错误恢复与重试策略

实践任务: 构建一个带子图和高级状态管理的复杂 Agent
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from app.llm import client, chat
from app.config import DEFAULT_MODEL


def main():
    """Day 27 main entry point."""
    print("Day 27 - LangGraph 高级特性")
    print("=" * 40)
    # TODO: Implement today's exercises
    pass


if __name__ == "__main__":
    main()
