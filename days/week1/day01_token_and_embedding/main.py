"""
Day 01 - Token 与 Embedding 基础
================================
知识点:
- 什么是 Token，Tokenizer 的工作原理
- Token 计数与成本估算
- Embedding 的概念与用途
- 使用 tiktoken 进行 Token 分析

实践任务: 使用 tiktoken 分析不同文本的 Token 数量，体验 Embedding API
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from app.llm import client, chat
from app.config import DEFAULT_MODEL


def main():
    """Day 01 main entry point."""
    print("Day 01 - Token 与 Embedding 基础")
    print("=" * 40)
    # TODO: Implement today's exercises
    pass


if __name__ == "__main__":
    main()
