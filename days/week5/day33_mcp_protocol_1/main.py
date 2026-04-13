"""
Day 33 - MCP 协议 (上)
========================
知识点:
- Model Context Protocol (MCP) 概述
- MCP 架构: Client / Server / Transport
- MCP 工具 (Tools) 定义
- MCP Server 的创建与注册

实践任务: 创建一个简单的 MCP Server，暴露自定义工具
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from app.llm import client, chat
from app.config import DEFAULT_MODEL


def main():
    """Day 33 main entry point."""
    print("Day 33 - MCP 协议 (上)")
    print("=" * 40)
    # TODO: Implement today's exercises
    pass


if __name__ == "__main__":
    main()
