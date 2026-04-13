"""
Day 15 - LangChain 基础
========================
知识点:
- LangChain 框架概览与核心组件
- ChatModel、PromptTemplate、OutputParser
- LangChain 与原生 API 的对比
- 安装与环境配置

实践任务: 使用 LangChain 重写之前的 API 调用示例
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from app.llm import client, chat
from app.config import DEFAULT_MODEL


def main():
    """Day 15 main entry point."""
    print("Day 15 - LangChain 基础")
    print("=" * 40)
    # TODO: Implement today's exercises
    pass


if __name__ == "__main__":
    main()
