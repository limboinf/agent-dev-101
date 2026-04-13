"""
Day 17 - LangChain Tools & Agent
==================================
知识点:
- LangChain Tool 定义与 @tool 装饰器
- 内置工具与自定义工具
- LangChain Agent 类型与创建
- AgentExecutor 的使用

实践任务: 创建一个带自定义工具的 LangChain Agent
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from app.llm import client, chat
from app.config import DEFAULT_MODEL


def main():
    """Day 17 main entry point."""
    print("Day 17 - LangChain Tools & Agent")
    print("=" * 40)
    # TODO: Implement today's exercises
    pass


if __name__ == "__main__":
    main()
