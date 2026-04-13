"""
Day 08 - Function Calling (上)
===============================
知识点:
- Function Calling 的概念与原理
- 定义函数 Schema (JSON Schema)
- OpenAI Function Calling API 使用
- 参数解析与函数执行

实践任务: 实现一个带 Function Calling 的天气查询 Agent
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from app.llm import client, chat
from app.config import DEFAULT_MODEL


def main():
    """Day 08 main entry point."""
    print("Day 08 - Function Calling (上)")
    print("=" * 40)
    # TODO: Implement today's exercises
    pass


if __name__ == "__main__":
    main()
