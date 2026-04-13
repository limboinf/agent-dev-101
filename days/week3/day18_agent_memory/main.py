"""
Day 18 - Agent Memory
======================
知识点:
- 短期记忆 vs 长期记忆
- ConversationBufferMemory / Summary / Window
- 向量数据库作为长期记忆
- 记忆检索与上下文注入

实践任务: 为 Agent 添加不同类型的记忆能力
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from app.llm import client, chat
from app.config import DEFAULT_MODEL


def main():
    """Day 18 main entry point."""
    print("Day 18 - Agent Memory")
    print("=" * 40)
    # TODO: Implement today's exercises
    pass


if __name__ == "__main__":
    main()
