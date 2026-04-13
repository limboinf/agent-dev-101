"""
Day 23 - Callbacks 与可观测性
==============================
知识点:
- LangChain Callback 系统
- 自定义 Callback Handler
- LangSmith 集成与 Tracing
- 日志记录与性能监控

实践任务: 实现自定义 Callback，接入 LangSmith 进行调试
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from app.llm import client, chat
from app.config import DEFAULT_MODEL


def main():
    """Day 23 main entry point."""
    print("Day 23 - Callbacks 与可观测性")
    print("=" * 40)
    # TODO: Implement today's exercises
    pass


if __name__ == "__main__":
    main()
