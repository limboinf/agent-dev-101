"""
Day 36 - Harness Engineering (上)
==================================
知识点:
- Agent Harness 的概念与设计
- 输入输出管道设计
- 工具注册与管理框架
- 配置驱动的 Agent 构建

实践任务: 设计并实现一个可复用的 Agent Harness 框架
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from app.llm import client, chat
from app.config import DEFAULT_MODEL


def main():
    """Day 36 main entry point."""
    print("Day 36 - Harness Engineering (上)")
    print("=" * 40)
    # TODO: Implement today's exercises
    pass


if __name__ == "__main__":
    main()
