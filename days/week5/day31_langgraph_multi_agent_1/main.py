"""
Day 31 - LangGraph 多 Agent (上)
==================================
知识点:
- LangGraph 多 Agent 架构
- Supervisor 模式实现
- Agent 间状态共享
- 任务委派与结果收集

实践任务: 使用 LangGraph 实现 Supervisor 多 Agent 系统
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from app.llm import client, chat
from app.config import DEFAULT_MODEL


def main():
    """Day 31 main entry point."""
    print("Day 31 - LangGraph 多 Agent (上)")
    print("=" * 40)
    # TODO: Implement today's exercises
    pass


if __name__ == "__main__":
    main()
