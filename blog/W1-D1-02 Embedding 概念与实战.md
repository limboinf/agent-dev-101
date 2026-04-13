# Embedding 概念与实战（面向大语言 LLM 入门教程）

---

## 一、Embedding 是什么？

在上一节中，我们了解到文本被 Tokenize 后，模型需要将 Token 转换为**数值形式**才能进行处理。Embedding（词嵌入）就是这个转换过程的核心机制。

![](https://limbo.oss-cn-beijing.aliyuncs.com/wiki/20260410121844708.png)

### 核心定义

**Embedding 是将离散的 Token 映射为连续向量空间中的稠密向量（Dense Vector）的过程。**

```
文本 → Tokenizer → Token IDs → Embedding Layer → 向量（如 1536 维浮点数）
```

每个 Token 对应一个固定维度的向量（常见维度：384、768、1024、1536、3072 等），这些向量的每个维度都是学习得到的浮点数。

### 为啥叫稠密？它和稀疏向量区别？

稠密向量呢，它的元素分布大部分都是由非零的实数填充的一个固定长度数值序列。稀疏向量呢，它绝大多数是0，极少数是非0的这种元素分布。所以，稀疏向量的维度长度比较高，通常和词汇表大小相等。稠密向量刚才说了，它是长度固定的数值序列，所以它的维度长度较低且固定，通常是768、1024、1536等。这是从概念上去表示两者的不同。

![](https://limbo.oss-cn-beijing.aliyuncs.com/wiki/20260410123802521.png)
#### 通俗理解 

如果把寻找一个城市看作数据检索：

- **稀疏向量**就像是**查字典索引**。你必须搜“上海”这两个字，如果搜“东方明珠所在的城市”，索引就断了。
    
- **稠密向量**就像是**经纬度坐标**。每个城市在地球上都有一个精确的坐标 $(x, y)$。即便你不知道城市名字，只要你有“沿海”、“经济中心”等特征描述，模型就能把你带到坐标最接近的那个点。


### 为什么叫"嵌入"？

想象把一个个离散的词汇"嵌入"到一个连续的、有意义的高维空间中——语义相似的词汇在这个空间中距离更近，就像把相似的物品放在货架的相邻位置。

---

## 二、Embedding 的核心特性

### 1. 语义相似性 → 向量距离近

这是 Embedding 最神奇的特性：

| 词对 | 关系 | 向量相似度 |
|------|------|-----------|
| "大语言模型" ↔ "LLM" | 同义 | 高（如 0.85） |
| "猫" ↔ "狗" | 同类 | 较高（如 0.75） |
| "猫" ↔ "汽车" | 无关 | 低（如 0.20） |

> 向量相似度通常用**余弦相似度**（Cosine Similarity）衡量，范围 [-1, 1]，值越大越相似。

### 2. 语义关系的线性特征

Embedding 向量还表现出惊人的线性关系：

```
vector("国王") - vector("男") + vector("女") ≈ vector("女王")
vector("北京") - vector("中国") + vector("日本") ≈ vector("东京")
```

这说明 Embedding 捕捉的不仅是"相似"，还有**语义关系的方向性**。

---

## 三、Embedding 是如何生成的？

### 训练过程（简化版）

Embedding 层本质上是一个**查找表（Lookup Table）**：

```python
# 伪代码示意
vocab_size = 50000      # 词汇表大小
dim = 1536              # 向量维度

# Embedding 表: [vocab_size, dim]
embedding_table = torch.randn(vocab_size, dim)

# 查询某个 token 的向量
token_id = 1234
vector = embedding_table[token_id]  # 返回 1536 维向量
```

这个查找表在模型预训练时学习得到——模型通过预测下一个 Token 的任务，被迫学会"哪些词经常出现在相似的上下文中"，从而将语义相似的词映射到相近的向量。

### 上下文感知 vs 静态 Embedding

| 类型 | 代表 | 特点 |
|------|------|------|
| 静态 Embedding | Word2Vec、GloVe | 一词一向量，不随上下文变化 |
| 上下文感知 | BERT、GPT 系列 | "bank" 在"河岸"和"银行"场景下向量不同 |

现代 LLM 使用**上下文感知**的 Embedding，能处理一词多义。

---

## 四、实战：使用 OpenAI API 获取 Embedding

### 准备工作

```bash
pip install openai
```

```python
import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
```

### 获取文本 Embedding

```python
def get_embedding(text, model="text-embedding-3-small"):
    """获取文本的 Embedding 向量"""
    response = client.embeddings.create(
        input=text,
        model=model
    )
    return response.data[0].embedding

# 测试
text = "大语言模型"
vector = get_embedding(text)
print(f"文本: {text}")
print(f"向量维度: {len(vector)}")
print(f"前5维: {vector[:5]}")
# 输出: 文本: 大语言模型
#       向量维度: 1536
#       前5维: [0.0123, -0.0456, 0.0789, ...]
```


### 计算语义相似度

```python
import numpy as np

def cosine_similarity(vec1, vec2):
    """计算两个向量的余弦相似度"""
    vec1 = np.array(vec1)
    vec2 = np.array(vec2)
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

# 对比多组文本的相似度
texts = [
    "大语言模型",
    "LLM",
    "Large Language Model",
    "猫",
    "深度学习"
]

# 获取所有文本的 embedding
embeddings = [get_embedding(t) for t in texts]

# 计算相似度矩阵
print("相似度矩阵:")
print(f"{'':15}", end="")
for t in texts:
    print(f"{t:15}", end="")
print()

for i, text_i in enumerate(texts):
    print(f"{text_i:15}", end="")
    for j, text_j in enumerate(texts):
        sim = cosine_similarity(embeddings[i], embeddings[j])
        print(f"{sim:15.3f}", end="")
    print()

# 输出示例:
#               大语言模型               LLM Large Language...              猫         深度学习
# 大语言模型           1.000           0.892           0.823           0.234           0.712
# LLM                0.892           1.000           0.901           0.198           0.654
# Large Language...  0.823           0.901           1.000           0.187           0.623
# 猫                 0.234           0.198           0.187           1.000           0.245
# 深度学习            0.712           0.654           0.623           0.245           1.000
```

可以看到：
- "大语言模型"、"LLM"、"Large Language Model" 三者相似度很高（>0.8）
- "猫"与其他词相似度都很低（<0.25）
- "深度学习"与大语言模型相关，相似度中等（~0.7）

---

## 五、Embedding 的实际应用场景

### 1. 语义搜索（Semantic Search）

传统关键词搜索只能匹配字面，Embedding 实现**语义搜索**：

```python
class SemanticSearcher:
    """基于 Embedding 的语义搜索"""
    
    def __init__(self):
        self.documents = []      # 原始文档
        self.embeddings = []     # 文档 embedding
    
    def add_document(self, text):
        """添加文档到搜索库"""
        self.documents.append(text)
        self.embeddings.append(get_embedding(text))
    
    def search(self, query, top_k=3):
        """语义搜索"""
        query_vec = get_embedding(query)
        
        # 计算与所有文档的相似度
        similarities = [
            cosine_similarity(query_vec, doc_vec)
            for doc_vec in self.embeddings
        ]
        
        # 返回最相似的 top_k 个
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        return [(self.documents[i], similarities[i]) for i in top_indices]

# 使用示例
searcher = SemanticSearcher()
docs = [
    "Python 是一种高级编程语言，语法简洁",
    "JavaScript 主要用于网页前端开发",
    "机器学习是人工智能的一个分支",
    "深度学习使用神经网络进行学习",
]

for doc in docs:
    searcher.add_document(doc)

# 语义搜索：查询"AI 编程"，应该匹配到 Python 和机器学习相关文档
results = searcher.search("AI 编程语言", top_k=2)
print("搜索结果:")
for doc, score in results:
    print(f"  [{score:.3f}] {doc}")

# 输出示例:
# 搜索结果:
#   [0.823] Python 是一种高级编程语言，语法简洁
#   [0.756] 机器学习是人工智能的一个分支
```

### 2. 文本分类（零样本）

利用 Embedding 无需训练即可分类：

```python
def zero_shot_classify(text, categories):
    """零样本文本分类"""
    text_vec = get_embedding(text)
    category_vectors = [get_embedding(c) for c in categories]
    
    similarities = [cosine_similarity(text_vec, cv) for cv in category_vectors]
    best_idx = np.argmax(similarities)
    
    return categories[best_idx], similarities[best_idx]

# 示例：自动分类客户反馈
categories = ["产品建议", "投诉", "咨询", "表扬"]
feedbacks = [
    "你们的 App 太好用了，帮我节省了好多时间",
    "能不能加个夜间模式？现在太亮了",
    "订单还没收到货，已经一周了",
]

for fb in feedbacks:
    label, score = zero_shot_classify(fb, categories)
    print(f"[{label}] {fb[:20]}... (置信度: {score:.3f})")

# 输出:
# [表扬] 你们的 App 太好用了，帮... (置信度: 0.834)
# [产品建议] 能不能加个夜间模式？现... (置信度: 0.712)
# [投诉] 订单还没收到货，已经一... (置信度: 0.756)
```

### 3. RAG（检索增强生成）的核心

Embedding 是 RAG 架构的基石：

```
用户问题 → Embedding → 向量数据库检索 → 相似文档 → 构造 Prompt → LLM 生成回答
```

```python
def simple_rag_answer(question, knowledge_base):
    """简化版 RAG 流程"""
    # 1. 将知识库文档转换为 embedding（实际中通常预先计算好）
    doc_embeddings = [get_embedding(doc) for doc in knowledge_base]
    
    # 2. 问题 embedding
    question_vec = get_embedding(question)
    
    # 3. 检索最相关文档
    similarities = [cosine_similarity(question_vec, de) for de in doc_embeddings]
    best_doc_idx = np.argmax(similarities)
    relevant_doc = knowledge_base[best_doc_idx]
    
    # 4. 构造增强 Prompt（简化版，实际使用 Chat API）
    prompt = f"""基于以下参考资料回答问题：

参考资料：{relevant_doc}

用户问题：{question}

回答："""
    
    return prompt, relevant_doc

# 示例知识库
knowledge_base = [
    "OpenAI 成立于 2015 年，总部位于旧金山，致力于开发安全的通用人工智能",
    "GPT-4 是 OpenAI 发布的大语言模型，支持多模态输入",
    "BERT 是 Google 开发的双向编码器表示模型，主要用于理解任务",
]

question = "OpenAI 的总部在哪里？"
prompt, doc = simple_rag_answer(question, knowledge_base)
print(f"检索到的文档: {doc}")
print(f"构造的 Prompt:\n{prompt}")
```

---

## 六、主流 Embedding 模型对比

| 模型 | 提供商 | 维度 | 特点 | 适用场景 |
|------|--------|------|------|----------|
| text-embedding-3-small | OpenAI | 1536 | 快速、便宜 | 通用场景、大规模应用 |
| text-embedding-3-large | OpenAI | 3072 | 高精度 | 对质量要求高的场景 |
| text-embedding-ada-002 | OpenAI | 1536 | 老版本，兼容性好 | 遗留系统 |
| bge-m3 | BAAI | 1024 | 开源、多语言 | 中文场景、离线部署 |
| all-MiniLM-L6-v2 | Sentence-Transformers | 384 | 轻量、快速 | 资源受限环境 |
| m3e-base | 社区 | 768 | 中文优化 | 中文语义搜索 |

### 选型建议

1. **快速验证/原型**：OpenAI text-embedding-3-small
2. **生产环境中文场景**：考虑 bge-m3 或 m3e-base（成本低，可离线）
3. **极致精度**：text-embedding-3-large
4. **边缘设备**：all-MiniLM-L6-v2 等轻量模型

---

## 七、常见问题

### Q1: Embedding 向量为什么维度这么高？

高维空间能容纳更丰富的语义信息。就像用 3 个数字只能描述颜色 RGB，但用 1536 个数字可以描述词义的方方面面。

### Q2: 长文本如何处理？

大多数 Embedding 模型有长度限制（如 8192 tokens）。超长文本可：
- 分段后取平均
- 提取关键段落
- 使用支持长文本的专用模型（如 Jina Embeddings v2 支持 8192 tokens）

### Q3: 不同模型的 Embedding 能混用吗？

**不能**。不同模型的向量空间完全不同，无法比较相似度。

---

## 八、小结

- **Embedding 是将 Token 映射为向量的过程**，让模型能"理解"语义
- **语义相似的词，向量距离近**——这是所有应用的基础
- **实战应用**：语义搜索、文本分类、RAG、推荐系统
- **预告**：第二周学习 RAG 时，我们将深入 Embedding 模型的选型、微调与向量数据库的使用

> 💡 **练习建议**：
> 1. 运行上述代码，观察不同文本的相似度
> 2. 用自己领域的文档构建一个小型语义搜索引擎
> 3. 尝试对比 OpenAI 和开源 Embedding 模型的效果差异

---