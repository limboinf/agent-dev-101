"""
Day 28 - Agentic RAG 项目
===========================
知识点:
- Agentic RAG 架构设计
- 自适应检索策略
- 查询改写与路由
- 综合 LangGraph + RAG 构建完整项目

实践任务: 构建一个 Agentic RAG 系统，支持智能检索和多步推理
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from app.llm import client, chat
from app.config import DEFAULT_MODEL


def main():
    """Day 28 main entry point."""
    print("Day 28 - Agentic RAG 项目")
    print("=" * 40)
    # TODO: Implement today's exercises
    pass


if __name__ == "__main__":
    main()
