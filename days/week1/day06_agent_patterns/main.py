"""
Day 06 - Agent 设计模式
========================
知识点:
- ReAct 模式 (Reasoning + Acting)
- Plan-and-Execute 模式
- Reflection / Self-Critique 模式
- Tool Use 模式

实践任务: 用伪代码实现不同 Agent 模式的基本流程
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from app.llm import client, chat
from app.config import DEFAULT_MODEL


def main():
    """Day 06 main entry point."""
    print("Day 06 - Agent 设计模式")
    print("=" * 40)
    # TODO: Implement today's exercises
    pass


if __name__ == "__main__":
    main()
