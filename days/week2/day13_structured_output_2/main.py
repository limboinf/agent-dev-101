"""
Day 13 - Structured Output (下)
================================
知识点:
- 复杂嵌套结构的输出
- 枚举类型与联合类型
- 输出验证与错误处理
- Structured Output 与 Function Calling 对比

实践任务: 构建一个结构化的信息抽取 Pipeline
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from app.llm import client, chat
from app.config import DEFAULT_MODEL


def main():
    """Day 13 main entry point."""
    print("Day 13 - Structured Output (下)")
    print("=" * 40)
    # TODO: Implement today's exercises
    pass


if __name__ == "__main__":
    main()
