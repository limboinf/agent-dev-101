"""
Day 03 - Context Engineering (上)
==================================
知识点:
- Context Window 的概念与限制
- System Prompt 设计原则
- Few-shot Prompting 技巧
- Prompt 模板化与管理

实践任务: 设计高质量的 System Prompt，实践 Few-shot 示例编排
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from app.llm import client, chat
from app.config import DEFAULT_MODEL


def main():
    """Day 03 main entry point."""
    print("Day 03 - Context Engineering (上)")
    print("=" * 40)
    # TODO: Implement today's exercises
    pass


if __name__ == "__main__":
    main()
