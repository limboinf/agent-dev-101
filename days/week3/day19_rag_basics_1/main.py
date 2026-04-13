"""
Day 19 - RAG 基础 (上)
=======================
知识点:
- RAG (Retrieval-Augmented Generation) 原理
- 文档加载与分割 (Document Loaders, Text Splitters)
- Embedding 模型选择
- 向量数据库 (ChromaDB / FAISS)

实践任务: 构建一个简单的文档问答 RAG 系统
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from app.llm import client, chat
from app.config import DEFAULT_MODEL


def main():
    """Day 19 main entry point."""
    print("Day 19 - RAG 基础 (上)")
    print("=" * 40)
    # TODO: Implement today's exercises
    pass


if __name__ == "__main__":
    main()
