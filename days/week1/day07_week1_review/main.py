"""
Day 07 - 第一周回顾与总结
==========================
知识点:
- Token、Embedding、API 调用回顾
- Context Engineering 要点总结
- Agent 概念与模式梳理
- 动手练习: 综合小项目

实践任务: 完成一个综合练习，整合本周所学知识
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from app.llm import client, chat
from app.config import DEFAULT_MODEL


def main():
    """Day 07 main entry point."""
    print("Day 07 - 第一周回顾与总结")
    print("=" * 40)
    # TODO: Implement today's exercises
    pass


if __name__ == "__main__":
    main()
