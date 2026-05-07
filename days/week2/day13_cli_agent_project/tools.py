"""
工具集合 (Tools)
================

本模块定义 CLI Agent 可调用的三个工具：

1. wikipedia_search  - 维基百科搜索 (基于 MediaWiki REST API + httpx)
2. calculator        - 数学表达式求值 (使用 simpleeval 库, 安全沙箱)
3. weather_lookup    - 中国大陆城市天气查询 (使用 wttr.in 公共 API, 无需 Key)

每个工具暴露两样东西:
- 一个 Python 函数, 真正干活的实现
- 一份 OpenAI tool schema (JSON Schema), 让模型知道有哪些工具、参数怎么写

下游 agent.py 会:
- 把 SCHEMAS 传给 OpenAI Chat Completions 的 tools 参数
- 收到 tool_call 后查 TOOL_REGISTRY 找到对应函数并执行
"""

from __future__ import annotations

import math
from typing import Any, Callable

import httpx
from simpleeval import SimpleEval

# Wikipedia 强制要求 User-Agent 才能访问 API, 否则会被拒绝
_WIKI_UA = "agentic-agent-101/0.1 (https://github.com/limboinf/agent-dev-101)"


# ============================================================
# 1. Wikipedia 搜索 (调用 MediaWiki Action API)
# ============================================================

def wikipedia_search(query: str, lang: str = "zh", sentences: int = 3) -> str:
    """搜索维基百科并返回首条结果的摘要。

    流程: opensearch (找候选标题) -> extracts (取纯文本摘要)。

    Args:
        query: 搜索关键词, 例如 '量子计算' 或 'Alan Turing'
        lang: 语言代码, 默认中文 ("zh"), 也支持 "en"
        sentences: 摘要保留的句数, 默认 3 句
    """
    api = f"https://{lang}.wikipedia.org/w/api.php"
    headers = {"User-Agent": _WIKI_UA}

    try:
        with httpx.Client(timeout=15.0, headers=headers, follow_redirects=True) as client:
            # Step 1: opensearch 找候选条目
            search_resp = client.get(
                api,
                params={
                    "action": "opensearch",
                    "search": query,
                    "limit": 3,
                    "namespace": 0,
                    "format": "json",
                },
            )
            search_resp.raise_for_status()
            _, titles, _, urls = search_resp.json()
            if not titles:
                return f"未找到与 '{query}' 相关的维基百科词条。"

            title, url = titles[0], urls[0]

            # Step 2: 取该条目的纯文本摘要
            extract_resp = client.get(
                api,
                params={
                    "action": "query",
                    "prop": "extracts",
                    "explaintext": 1,
                    "exintro": 1,           # 仅取首段 (lead section)
                    "exsentences": sentences,
                    "redirects": 1,
                    "titles": title,
                    "format": "json",
                },
            )
            extract_resp.raise_for_status()
            pages = extract_resp.json()["query"]["pages"]
            page = next(iter(pages.values()))
            extract = (page.get("extract") or "").strip()

        if not extract:
            return f"找到词条 '{title}' 但没有可用的摘要。\n来源: {url}"

        return f"【{title}】\n{extract}\n\n来源: {url}"

    except httpx.HTTPError as exc:
        return f"维基百科请求失败: {exc}"
    except (KeyError, ValueError, StopIteration) as exc:
        return f"维基百科响应解析失败: {exc}"


# ============================================================
# 2. 计算器 (基于 simpleeval, 防代码注入)
# ============================================================

# 暴露一些常用数学函数, 让模型可以做更复杂的计算
_MATH_FUNCS: dict[str, Callable[..., Any]] = {
    "sqrt": math.sqrt,
    "pow": math.pow,
    "log": math.log,
    "log2": math.log2,
    "log10": math.log10,
    "exp": math.exp,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "floor": math.floor,
    "ceil": math.ceil,
}

_MATH_NAMES: dict[str, Any] = {
    "pi": math.pi,
    "e": math.e,
}


def calculator(expression: str) -> str:
    """安全地求值一个数学表达式。

    支持 + - * / // % **、常见数学函数 (sqrt/log/sin/...)
    以及常量 pi、e。
    """
    evaluator = SimpleEval(functions=_MATH_FUNCS, names=_MATH_NAMES)
    try:
        result = evaluator.eval(expression)
        return f"{expression} = {result}"
    except Exception as exc:  # noqa: BLE001
        return f"表达式求值失败 ({type(exc).__name__}): {exc}"


# ============================================================
# 3. 天气查询 (wttr.in, 无需 API Key)
# ============================================================

def weather_lookup(city: str) -> str:
    """查询中国大陆城市当前天气。

    使用 wttr.in 公共服务, 拼接 city 即可, 中文地名也可识别。
    返回温度、体感、天气状况、风向风速等关键信息。
    """
    # ?format=j1 让 wttr.in 返回结构化 JSON
    url = f"https://wttr.in/{city}"
    params = {"format": "j1", "lang": "zh"}
    headers = {"User-Agent": "curl/8.0"}  # 不加 UA 会拿到 HTML

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()

        current = data["current_condition"][0]
        area = data["nearest_area"][0]

        # 中文描述优先, 没有就回退英文
        desc_zh = current.get("lang_zh", [{}])[0].get("value")
        desc = desc_zh or current["weatherDesc"][0]["value"]

        area_name = area["areaName"][0]["value"]
        country = area["country"][0]["value"]

        return (
            f"【{area_name}, {country} · 实时天气】\n"
            f"- 天气: {desc}\n"
            f"- 气温: {current['temp_C']}°C (体感 {current['FeelsLikeC']}°C)\n"
            f"- 湿度: {current['humidity']}%\n"
            f"- 风向: {current['winddir16Point']} {current['windspeedKmph']} km/h\n"
            f"- 能见度: {current['visibility']} km\n"
            f"- 观测时间: {current['localObsDateTime']}"
        )
    except httpx.HTTPError as exc:
        return f"天气服务请求失败: {exc}"
    except (KeyError, IndexError, ValueError) as exc:
        return f"天气数据解析失败: {exc}"


# ============================================================
# 工具注册表 + OpenAI Tool Schemas
# ============================================================

TOOL_REGISTRY: dict[str, Callable[..., str]] = {
    "wikipedia_search": wikipedia_search,
    "calculator": calculator,
    "weather_lookup": weather_lookup,
}


SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "wikipedia_search",
            "description": (
                "在维基百科上搜索词条并返回简短摘要。"
                "适用于查询人物、地点、概念、事件等百科知识。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词, 例如 '量子计算' 或 'Alan Turing'",
                    },
                    "lang": {
                        "type": "string",
                        "description": "维基百科语言代码, 中文用 'zh', 英文用 'en'",
                        "enum": ["zh", "en"],
                        "default": "zh",
                    },
                    "sentences": {
                        "type": "integer",
                        "description": "摘要返回的句子数, 默认 3",
                        "default": 3,
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": (
                "对一个数学表达式求值。支持 + - * / // % **、"
                "sqrt/log/sin/cos/tan/exp 等函数, 以及 pi、e 常量。"
                "示例表达式: '2 + 3 * 4'、'sqrt(2)'、'log(100, 10)'。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "要计算的数学表达式",
                    },
                },
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "weather_lookup",
            "description": (
                "查询中国大陆城市的当前天气, 返回温度、体感、天气状况、风向风速等。"
                "城市名可用中文 (如 '北京'、'上海') 或拼音 (如 'Beijing')。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名称, 例如 '北京'、'杭州'、'Shanghai'",
                    },
                },
                "required": ["city"],
            },
        },
    },
]
