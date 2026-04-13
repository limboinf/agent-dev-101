"""
Day 38 - 框架探索 (上)
========================
知识点:
- Agent 框架全景: CrewAI, AutoGen, OpenAI Swarm
- 框架选型考虑因素
- CrewAI / AutoGen 快速上手
- 框架对比与适用场景

实践任务: 使用一个新框架重新实现之前的 Agent 项目
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from app.llm import client, chat
from app.config import DEFAULT_MODEL


def main():
    """Day 38 main entry point."""
    print("Day 38 - 框架探索 (上)")
    print("=" * 40)
    # TODO: Implement today's exercises
    pass


if __name__ == "__main__":
    main()
