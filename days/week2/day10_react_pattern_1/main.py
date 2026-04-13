"""
Day 10 - ReAct 模式实现 (上)
==============================
知识点:
- ReAct 论文核心思想
- Thought → Action → Observation 循环
- 手动实现 ReAct Loop
- 调试与日志记录

实践任务: 从零实现一个 ReAct Agent
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from app.llm import client, chat
from app.config import DEFAULT_MODEL


def main():
    """Day 10 main entry point."""
    print("Day 10 - ReAct 模式实现 (上)")
    print("=" * 40)
    # TODO: Implement today's exercises
    pass


if __name__ == "__main__":
    main()
