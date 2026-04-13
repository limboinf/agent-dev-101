"""
Day 05 - Agent 核心概念
========================
知识点:
- 什么是 AI Agent
- Agent 的核心组成: 感知、推理、行动
- Agent 与普通 LLM 应用的区别
- Agent 的能力边界与适用场景

实践任务: 分析几个真实 Agent 产品的架构，理解 Agent 设计思路
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from app.llm import client, chat
from app.config import DEFAULT_MODEL


def main():
    """Day 05 main entry point."""
    print("Day 05 - Agent 核心概念")
    print("=" * 40)
    # TODO: Implement today's exercises
    pass


if __name__ == "__main__":
    main()
