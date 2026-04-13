"""
Day 12 - Structured Output (上)
================================
知识点:
- 为什么需要结构化输出
- JSON Mode 与 Structured Outputs
- Pydantic 模型定义与验证
- Response Format 参数使用

实践任务: 使用 Structured Output 实现数据提取任务
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from app.llm import client, chat
from app.config import DEFAULT_MODEL


def main():
    """Day 12 main entry point."""
    print("Day 12 - Structured Output (上)")
    print("=" * 40)
    # TODO: Implement today's exercises
    pass


if __name__ == "__main__":
    main()
