"""
Day 16 - LCEL 与 Chain
=======================
知识点:
- LangChain Expression Language (LCEL) 语法
- Runnable 接口与管道操作符 |
- Chain 的组合与嵌套
- RunnablePassthrough 与 RunnableLambda

实践任务: 使用 LCEL 构建多步骤处理链
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from app.llm import client, chat
from app.config import DEFAULT_MODEL


def main():
    """Day 16 main entry point."""
    print("Day 16 - LCEL 与 Chain")
    print("=" * 40)
    # TODO: Implement today's exercises
    pass


if __name__ == "__main__":
    main()
