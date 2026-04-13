"""
Day 25 - LangGraph 入门
========================
知识点:
- LangGraph 核心概念: 状态、节点、边
- StateGraph 的创建与编译
- 条件边与路由
- 与 LangChain Agent 的区别

实践任务: 使用 LangGraph 构建一个简单的对话流程图
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from app.llm import client, chat
from app.config import DEFAULT_MODEL


def main():
    """Day 25 main entry point."""
    print("Day 25 - LangGraph 入门")
    print("=" * 40)
    # TODO: Implement today's exercises
    pass


if __name__ == "__main__":
    main()
