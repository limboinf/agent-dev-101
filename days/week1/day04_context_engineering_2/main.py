"""
Day 04 - Context Engineering (下)
==================================
知识点:
- 上下文压缩与摘要策略
- 长文本处理技巧
- 多轮对话的上下文管理
- Context Engineering 最佳实践

实践任务: 实现一个带上下文管理的多轮对话系统
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from app.llm import client, chat
from app.config import DEFAULT_MODEL


def main():
    """Day 04 main entry point."""
    print("Day 04 - Context Engineering (下)")
    print("=" * 40)
    # TODO: Implement today's exercises
    pass


if __name__ == "__main__":
    main()
