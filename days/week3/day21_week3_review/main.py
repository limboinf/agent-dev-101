"""
Day 21 - 第三周回顾与总结
==========================
知识点:
- LangChain 核心组件回顾
- LCEL 与 Chain 构建要点
- Agent 与 Memory 实践总结
- RAG 系统构建经验

实践任务: 综合练习 — 构建一个带记忆和 RAG 的 LangChain Agent
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from app.llm import client, chat
from app.config import DEFAULT_MODEL


def main():
    """Day 21 main entry point."""
    print("Day 21 - 第三周回顾与总结")
    print("=" * 40)
    # TODO: Implement today's exercises
    pass


if __name__ == "__main__":
    main()
