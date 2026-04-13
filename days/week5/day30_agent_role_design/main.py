"""
Day 30 - Agent 角色设计
========================
知识点:
- Agent 人设 (Persona) 设计
- System Prompt 与角色约束
- 能力边界定义
- 工具分配策略

实践任务: 设计并实现多个具有不同角色的 Agent
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from app.llm import client, chat
from app.config import DEFAULT_MODEL


def main():
    """Day 30 main entry point."""
    print("Day 30 - Agent 角色设计")
    print("=" * 40)
    # TODO: Implement today's exercises
    pass


if __name__ == "__main__":
    main()
