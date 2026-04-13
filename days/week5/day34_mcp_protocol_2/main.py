"""
Day 34 - MCP 协议 (下)
========================
知识点:
- MCP Resources 与 Prompts
- MCP Client 集成
- MCP 与现有 Agent 框架的对接
- MCP 生态与最佳实践

实践任务: 将 MCP Server 集成到 Agent 中，实现端到端调用
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from app.llm import client, chat
from app.config import DEFAULT_MODEL


def main():
    """Day 34 main entry point."""
    print("Day 34 - MCP 协议 (下)")
    print("=" * 40)
    # TODO: Implement today's exercises
    pass


if __name__ == "__main__":
    main()
