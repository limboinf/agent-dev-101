"""
Day 20 - RAG 基础 (下)
=======================
知识点:
- 检索策略优化 (相似度搜索、MMR)
- Chunk 大小与重叠度调优
- Re-ranking 与过滤
- RAG 评估指标

实践任务: 优化 RAG 系统的检索质量与回答准确性
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from app.llm import client, chat
from app.config import DEFAULT_MODEL


def main():
    """Day 20 main entry point."""
    print("Day 20 - RAG 基础 (下)")
    print("=" * 40)
    # TODO: Implement today's exercises
    pass


if __name__ == "__main__":
    main()
