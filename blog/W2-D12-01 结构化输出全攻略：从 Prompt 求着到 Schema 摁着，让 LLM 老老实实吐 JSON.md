# 结构化输出全攻略：从 Prompt 求着到 Schema 摁着，让 LLM 老老实实吐 JSON

---

> 摘要：昨天 D11 那个手写 ReAct Agent 跑通之后，我做了件不太聪明的事——把它的最终 Action 从 `finish[文本]` 改成 `finish[JSON]`，想让它直接输出可以入库的结构化结果。结果模型给我演了一出大型现场翻车：有时候输出 ` ```json {...} ``` ` 包了三层、有时候在 JSON 前面写一段"亲爱的用户，下面是您的旅行计划……"、有时候字段名大小写漂移、有时候直接被截断了一半。我前前后后试了 Prompt 求着、JSON Mode、Structured Output、Pydantic 兜底、自动重试一整套方案，今天这篇笔记就把这套"驯服 LLM 输出 JSON"的完整工程套路一次讲透——从最初级的 Prompt 引导，到 OpenAI 的 `response_format`、JSON Schema 的 `strict: true`，再到 Pydantic 验证 + 自动重试、最后聊聊为什么 Instructor / outlines 这些第三方库会火。读完之后你应该能对得上一道经典面试题：**"怎么让 LLM 稳定输出 JSON?"**


---

![](https://limbo.oss-cn-beijing.aliyuncs.com/wiki/json-llm.png)

## 一、LLM 是"续写机"，不是"格式机"

LLM 本质是按概率 sample 下一个 token，**它没有"输出必须满足某种结构"的概念**。你写在 Prompt 里的"请输出 JSON 格式"是给它的"建议"，不是"约束"——满足这个建议的概率，取决于训练数据里类似的 pattern 出现得多不多。

所以"求着模型输出 JSON"会有四种典型失败模式：

| 失败模式 | 现象 | 根因 |
| ------ | ---- | ---- |
| **包装文本** | JSON 前后多了 "好的，下面是 JSON：" / markdown code block | 模型把"输出 JSON"当成了对话任务，本能地加礼貌套话 |
| **字段漂移** | `name` 变 `Name` 变 `full_name` | 模型在自己重新组织语义，没有把字段名当成"字面量" |
| **截断** | 输出到一半 token 用完了，JSON 不闭合 | `max_tokens` 设小了或 JSON 太长 |
| **结构幻觉** | 多出 / 少了字段，类型错了 | 训练数据里类似 schema 的样本不一致 |

要根治这四种问题，**得让"约束"从 Prompt 这一层下沉到推理这一层**。这就是 OpenAI 这两年引入 JSON Mode 和 Structured Output 的真正动机——把"输出格式"从"模型续写时的偏好"变成"采样时的硬性约束"。

---

## 二、三种"驯服"层级——从软到硬

我把驯服 LLM 输出 JSON 的所有方案，归纳成三个层级，越往下越硬：

```diagram
╭─────────────────────────────────────────────────╮
│ Level 1: Prompt 引导                            │
│   "请用 JSON 格式输出，包含 city / temp 字段"   │
│   → 软约束，模型说不定听不进去                  │
╰────────────────────┬────────────────────────────╯
                     │ 升级
                     ▼
╭─────────────────────────────────────────────────╮
│ Level 2: JSON Mode                              │
│   response_format={"type": "json_object"}       │
│   → 保证输出是合法 JSON，但字段没有约束         │
╰────────────────────┬────────────────────────────╯
                     │ 升级
                     ▼
╭─────────────────────────────────────────────────╮
│ Level 3: Structured Output                      │
│   response_format={"type": "json_schema",       │
│                    "json_schema": {...,         │
│                    "strict": true}}             │
│   → 字段名/类型/枚举全约束，几乎 100% 命中       │
╰─────────────────────────────────────────────────╯
```

外面再套一层 **Pydantic 验证 + 自动重试**，就是"工程级"的稳定输出方案。下面挨个上手。

---

## 三、Level 1 — Prompt 引导（最弱也最常见）

最朴素的写法，给 Prompt 里写一段"请你输出 JSON"：

```python
prompt = """请把下面这段产品描述抽取成 JSON，包含字段：
- name (string)
- price (number)
- in_stock (boolean)

只输出 JSON，不要解释。

描述：iPhone 16 Pro，售价 7999 元，现货发售。
"""
```

这种写法在强模型上，**80% 的情况是能用的**。但剩下 20% 就是上面演示的那些翻车。

**经验加分项**——能让命中率从 80% 提到 95%：

1. **加 "只输出 JSON，不要解释"**——治"礼貌套话"。
2. **给一个完整 few-shot 示例**——治字段漂移。
3. **明确写出每个字段的类型**——`name (string)`、`price (number)`。
4. **结尾加 `JSON:`**——把模型推到"开始写 JSON"的状态：

```python
prompt += "\n\nJSON:"
```

但说实话，**这些技巧都是在治标**。只要模型能输出文本，它就有可能输出错误的 JSON。所以我们升级。

---

## 四、Level 2 — JSON Mode（保证"是 JSON"，不保证"对的 JSON"）

OpenAI 2023 年底加的功能。核心就一行参数：

```python
resp = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "你是一个信息抽取助手，只输出 JSON。"},
        {"role": "user", "content": prompt},
    ],
    response_format={"type": "json_object"},   # 关键
)
```

加上之后，**OpenAI 会保证返回的 `content` 一定是合法 JSON**——`json.loads` 100% 不会报 `JSONDecodeError`、markdown code block、截断这些问题都不会再有。

但 JSON Mode 有两个**容易被忽略的限制**：

### 限制 1：你必须在 Prompt 里说 "JSON"

如果 Prompt 里完全没出现 "JSON" 这个词，OpenAI 会直接报错：

```text
'messages' must contain the word 'json' in some form, to use 'response_format' of type 'json_object'.
```

这是个"防呆"机制——避免你忘了告诉模型"我要 JSON"，然后它输出一个空对象 `{}` 应付你。

### 限制 2：JSON Mode 只管"是 JSON"，不管"字段对不对"

来看个翻车例子。我让它抽 `name / price / in_stock`：

```python
# JSON Mode 输出：
{"product_name": "iPhone 16 Pro", "cost": 7999, "available": true}
```

JSON 是合法的（`json.loads` 没问题），但字段名全错了——`name` 变 `product_name`，`price` 变 `cost`，`in_stock` 变 `available`。下游 `data["price"]` 直接 `KeyError`。

**JSON Mode 保证的是语法层（这是合法 JSON），不是语义层（字段对不对）。** 字段约束你得自己在 Prompt 里写、自己在代码里校验。

> 一句话总结：JSON Mode 是"防低级错误"的最低保障——能用，但远远不够。

---

## 五、Level 3 — Structured Output（字段也摁住）

OpenAI 2024 年 8 月推出的"硬约束"方案。原理上比 JSON Mode 更深一层：**它不是"事后检查输出是不是 JSON"，而是在 sample 阶段就限制下一个 token 必须符合 schema**（业界叫 constrained decoding）。

用法：

```python
schema = {
    "name": "product_extract",
    "strict": True,                     # 关键
    "schema": {
        "type": "object",
        "properties": {
            "name":     {"type": "string"},
            "price":    {"type": "number"},
            "in_stock": {"type": "boolean"},
        },
        "required": ["name", "price", "in_stock"],
        "additionalProperties": False,   # 禁止多余字段
    },
}

resp = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[...],
    response_format={"type": "json_schema", "json_schema": schema},
)
```

跑同一个抽取任务，结果稳如老狗：

```python
{"name": "iPhone 16 Pro", "price": 7999, "in_stock": true}
```

**字段名一字不差、类型正确、不多不少。** 多跑 100 次也是这个结构。

不过 Structured Output 也有几条**血泪写出来的注意事项**：

### 注意事项 1：`required` 必须包含所有字段

OpenAI 的 strict 模式有个反直觉的硬要求——`required` 数组必须列出 `properties` 里**所有的**字段，不允许"可选字段"。

```python
# ❌ 这样 OpenAI 会直接拒绝
"properties": {"name": {...}, "nickname": {...}},
"required": ["name"],   # nickname 没列进去 → 报错
```

想让某个字段"可空"，得用 `["string", "null"]` 联合类型：

```python
# ✅ 正确写法
"properties": {
    "name":     {"type": "string"},
    "nickname": {"type": ["string", "null"]},   # 允许 null
},
"required": ["name", "nickname"],   # 都得在 required 里
```

### 注意事项 2：`additionalProperties: false` 不能省

不写这条的话，模型偶尔会"多吐"几个字段。强制写上 = 多余字段直接被禁。

### 注意事项 3：嵌套 schema 也要 strict

如果 schema 里嵌套了对象，**每一层都要遵守上面两条规则**——`additionalProperties: false` + 所有字段都在 `required` 里。漏一层都会报错。

### 注意事项 4：不是所有模型都支持

只有 `gpt-4o`、`gpt-4o-mini` 这一代之后的模型支持 strict 模式；`gpt-3.5-turbo` 这种老模型只能用 JSON Mode。Anthropic 的 Claude 提供类似能力但 API 长得不一样（通过 Tool Use 包一层 schema 实现），DeepSeek / Qwen / Gemini 各家也都有自己的实现。**写跨厂商代码时，建议把"获取 schema 输出"封装成一个 adapter**，下层根据厂商分别实现。

![](https://limbo.oss-cn-beijing.aliyuncs.com/wiki/json-schema.png)

---

## 六、配上 Pydantic — 让"声明 schema"和"代码使用"对齐

到这里 schema 输出已经稳了，但还有个工程问题：**手写 JSON Schema 又啰嗦又容易写错**（嵌套对象、`required` 列表手动维护、类型字符串拼写错），而且 schema 写完了，下游代码还是只能用 `dict["price"]` 这种**没类型提示**的方式访问。

Pydantic 一手解决两个问题。

### 用 Pydantic 定义 + 自动生成 schema

```python
from pydantic import BaseModel, Field
from typing import Optional

class Product(BaseModel):
    name: str = Field(description="商品全名")
    price: float = Field(description="售价（人民币）")
    in_stock: bool
    nickname: Optional[str] = None
```

调 OpenAI 时，新版 SDK（>=1.40）直接支持把 Pydantic 模型传进去，不用手写 schema：

```python
from openai import OpenAI
client = OpenAI()

resp = client.beta.chat.completions.parse(   # 注意是 .parse 不是 .create
    model="gpt-4o-mini",
    messages=[...],
    response_format=Product,                  # ★ 直接传 Pydantic 类
)

product: Product = resp.choices[0].message.parsed
print(product.price)        # ✅ 有类型提示，IDE 直接补全
print(product.in_stock)
```

`client.beta.chat.completions.parse()` 帮你做了三件事：

1. **把 Pydantic 模型转成 JSON Schema**（自动加 `strict: true` 和 `additionalProperties: false`）
2. **把模型返回的 JSON 反序列化成 Pydantic 实例**
3. **如果反序列化失败，抛 `LengthFinishReasonError` / `ContentFilterFinishReasonError` 等明确异常**

代码量从"手写 schema + 调 API + json.loads + 再校验"四步压缩到一步。**这是 Pydantic + Structured Output 的最佳搭档姿势**。

### 进阶：用 Validator 把"业务规则"写进 schema

Pydantic 还能塞业务规则进去：

```python
from pydantic import BaseModel, Field, field_validator

class TravelPlan(BaseModel):
    destination: str
    days: int = Field(ge=1, le=30)              # 1-30 天
    budget: float = Field(gt=0)                  # 必须正数
    activities: list[str] = Field(min_length=1)  # 至少一项

    @field_validator("destination")
    def must_be_chinese_city(cls, v):
        if not any('\u4e00' <= c <= '\u9fff' for c in v):
            raise ValueError("destination 必须是中文城市名")
        return v
```

模型如果输出 `days=50`，Pydantic 直接拒。这层校验**在 JSON Schema 表达不出来**——schema 只能声明 `type: integer`，没法说"1-30 之间"。Pydantic 做事后校验，是 schema 的有效补充。

---

## 七、最后一块拼图：失败重试与降级策略

就算上了 Structured Output + Pydantic，**真实生产环境里仍然会有 1-2% 的失败**。原因可能是：

- `max_tokens` 不够，输出被截断
- 模型触发了 content filter 拒答
- field_validator 业务规则没过
- 厂商接口偶发超时

所以**重试 + 降级**是必须的。我喜欢的写法：

```python
from pydantic import ValidationError
import json

def safe_extract(prompt: str, model_cls, max_retries: int = 2) -> Product:
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            resp = client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "严格按 schema 输出 JSON。"},
                    {"role": "user",   "content": prompt},
                ] + ([
                    {"role": "user", "content":
                        f"上次输出失败：{last_error}，请修正后重试。"}
                ] if last_error else []),
                response_format=model_cls,
            )
            return resp.choices[0].message.parsed
        except (ValidationError, json.JSONDecodeError) as e:
            last_error = str(e)
    # 所有重试都失败 → 降级到 JSON Mode 兜底
    return _fallback_json_mode(prompt, model_cls)
```

两个细节值得说：

1. **把上一次的错误塞回 Prompt**——模型看到 `"上次输出失败：destination must be Chinese"` 之后会自己改正。这是"自我修正"的最简实现。
2. **降级到 JSON Mode**——`strict: true` 在某些 corner case 下会持续失败，这时回退到松一档的 JSON Mode + Pydantic 兜底，比直接抛错好。

---

## 八、最佳实践

### 8.1 主流方案的"全景对比表"

我把市面上能见到的所有方案做了一张大表，按部署场景分组——下次选型直接对着这张表查：

| 厂商 / 方案 | 怎么用 | 命中率 | 限制 |
| ---- | ---- | ---- | ---- |
| **OpenAI Structured Outputs (strict)** | `response_format={"type":"json_schema","json_schema":{...,"strict":true}}` | ~100% | 只 GPT-4o 之后；`required` 必须列全字段；`additionalProperties:false` 必填；嵌套 ≤5 层；不支持 `$ref` 深递归 / `patternProperties` / `if-then-else` |
| **OpenAI JSON Mode** | `response_format={"type":"json_object"}` | 保证是合法 JSON，字段不保证 | prompt 里必须出现 "json" 字样 |
| **OpenAI Function/Tool Calling** | 把 schema 包成 tool 定义 | ~100%（与 strict 同源） | 语义上是"调函数"，不是"输出数据"，需要心智切换 |
| **Anthropic Claude** | 通过 Tool Use 间接实现：定义一个 tool，强制 `tool_choice` | ~99% | 没有"原生 strict"，是用 tool 机制曲线救国；2025 末才上"原生 structured output" |
| **Google Gemini** | `response_mime_type="application/json"` + `response_schema=...` | ~100% | schema 子集和 OpenAI 不完全兼容 |
| **DeepSeek / Qwen / Mistral** | JSON Mode（多数模型支持） + prompt 引导 | 80-95% | 多数厂商的 JSON Mode 实际是"prompt 加塞 + 重试"，不是真正的 constrained decoding |

> **避雷**：很多国产 / 开源模型 API 文档里写的"JSON Mode"，**实际是 prompt-only 的伪 strict**——背后给你 prompt 加一句"请输出 JSON" 然后 retry 几次。和 OpenAI 的 token 级 constrained decoding **完全不是一个东西**。跨厂商代码不能假设"开了 JSON Mode 就一定稳"。


### 8.2 厂商间的"小坑"——Reasoning 模型的特殊问题

GPT-o1 / DeepSeek-R1 / QwQ 这类**推理模型**用 Structured Output 有个隐藏陷阱：

- 它们会先输出一大段 `<thinking>...` 推理内容，**这段内容也算在 `max_tokens` 里**；如果你 schema 复杂，推理过程吃完了 token，最终 JSON 直接被截断。
- 部分推理模型**完全不支持 JSON Mode / Structured Output**（如早期 o1-preview），只能 prompt 引导 + 后置解析。
- DeepSeek-R1 的"思考链"和最终 JSON 输出会混在一起，需要先剥离 `</think>` 标签再 `json.loads`。

**实战建议**：用推理模型时，**先让它推理 + 输出自然语言答案，再用一个普通模型做"格式化"二次调用**。两步走，每步只做一件事，比硬塞一个能推理又能严格输出 JSON 的怪物稳得多。

### 8.3 Schema 设计的 6 条铁律（让命中率再上一档）

光选对方案还不够。**Schema 本身怎么设计，直接决定 constrained decoding 的命中率和速度**。这 6 条来自 Outlines / XGrammar 团队和我自己踩坑的总结：

1. **字段越少越好**——字段越多，把"必要字段"和"扩展字段"拆成两次调用比一次硬塞 30 个字段更好。
2. **嵌套深度 ≤ 3 层**——避免深嵌套，OpenAI 官方限制是 5 层，但实战 3 层之内最稳。能 flatten 就 flatten。
3. **多用 `enum`，少用自由文本**——`{"type":"string","enum":["high","medium","low"]}` 比 `{"type":"string"}` 快得多，命中率也更高（候选 token 直接被锁死成几个）。
4. **谨慎用 Optional**——可空字段越多，模型越容易"偷懒"全输出 `null`。优先把所有真正"必需"的字段标 required。
5. **善用 `description`**——JSON Schema 的 `description` 字段会被模型当 prompt 提示。给每个字段写一句话清楚说明用途，命中率显著提高（和 Pydantic `Field(description=...)` 等价）。
6. **字段顺序要"友好于 next-token 预测"**——把模型已知的、信息量大的字段放前面（比如 `id`、`name`），后面字段的预测就更准。**这是个反直觉但很有效的小技巧**。


### 8.4 面试 / 技术评审标准答法

被面试官 / 架构 review 问到 "怎么稳定输出 JSON" 时，按这个结构答（背下来够用）：

> **第一层（原理）**：纯 prompt 失败率 5-15%，因为 LLM 是续写机，格式只是它的偏好不是约束。要稳定，必须把约束从"prompt 这一层"下沉到"采样这一层"——也就是 Constrained Decoding（FSM/CFG + logit masking）。
>
> **第二层（方案选型）**：
> - **OpenAI 系**：Structured Output (`strict: true`) + Pydantic `.parse()`，命中率接近 100%。
> - **多厂商**：用 Instructor 做统一抽象，它会自动按厂商选最优 mode（OpenAI Tools / Anthropic Tools / Gemini JSON）。
> - **推理模型**：拆两步——先推理输出文本，再用普通模型做格式化。
>
> **第三层（工程兜底）**：外层永远套 Pydantic 验证 + 自动重试（把上次失败的 reason 喂回去让模型自我修正）+ 降级到 JSON Mode + 最后 json-repair 兜底。SLA 高的业务再加 schema 预编译缓存。
>
> **核心原则**：**约束往下沉，校验往上层套**。能在 sample 阶段卡死的，就别留到事后清洗。

把这套答完——基本就稳了。

---

## 九、踩过的坑（实战集锦）

下面这些是我在调试过程中被绊倒的地方，都不是文档里写得很显眼的，专门列出来给你避雷：

### 坑 1：strict 模式下 `enum` 必须用字符串字面量

```python
# ❌ 报错
{"type": "string", "enum": ["high", "medium", "low", None]}

# ✅ 正确
{"type": ["string", "null"], "enum": ["high", "medium", "low", None]}
```

`enum` 里如果有 `None`，类型也得是 union。

### 坑 2：嵌套数组里的对象也要 `additionalProperties: false`

```python
{
  "type": "array",
  "items": {
    "type": "object",
    "properties": {...},
    "additionalProperties": False,   # ★ 这层也要写
    "required": [...]
  }
}
```

少写一层，整个 schema 被 OpenAI 拒。

### 坑 3：Pydantic 的 `Field(default=...)` 在 strict 模式下没用

```python
class Foo(BaseModel):
    name: str = "default_name"   # ❌ strict 模式下，模型仍然必须输出
```

因为 strict 模式要求 `required` 包含所有字段，Pydantic 默认值在 schema 转换时会被忽略。如果某个字段真的可空，老老实实写 `Optional[str] = None`。

### 坑 4：`max_tokens` 没设够 → 输出被截断

Structured Output 的 strict 解码不会"自动伸缩"——token 用完就用完，输出截断后整个 JSON 不完整，反序列化直接失败。**长字段类型一定要算好 max_tokens**，或者直接给一个保守的大值（如 4096）。

### 坑 5：Anthropic / 国产模型的"假 Structured Output"

很多厂商的 "JSON Mode" 实际是 prompt-only 的——它在背后自动给你的 prompt 加一段"请输出 JSON"，然后 retry 几次。**和 OpenAI 的 constrained decoding 完全不是一个东西**。跨厂商代码不能假设"开了 JSON Mode 就一定稳"，最外层 Pydantic + 重试这层永远不能省。

---

## 十、小结

把今天搞明白的几件事拎出来：

1. **LLM 不天然输出格式正确的 JSON**，因为它是"续写机"——格式只是续写时的偏好，不是硬约束。Prompt 求着模型最多 80-95% 命中。
2. **驯服 LLM 输出 JSON 有三个层级**：Prompt 引导 → JSON Mode（保证语法正确）→ Structured Output（连字段都摁住）。**约束越往下沉，命中率越高**。
3. **JSON Mode 只管"是 JSON"，不管"字段对不对"**——字段漂移 / 多吐字段 / 类型错误，它都管不了。生产环境永远要走 Structured Output。
4. **Structured Output 用法有四个雷**：`required` 必须列全部字段、`additionalProperties: false` 不能省、嵌套层每层都要遵守、不是所有模型都支持。
5. **Pydantic 是终极搭档**：`client.beta.chat.completions.parse(response_format=PydanticClass)` 一行代码搞定 schema 生成 + 反序列化 + 类型提示，还能塞 `field_validator` 加业务规则。
6. **生产环境的"稳定输出 JSON"= Pydantic + Structured Output + 自动重试 + JSON Mode 降级**。失败时把错误 reason 喂回去让模型自我修正，是最简单也最有效的兜底。
7. **面试题答法**：看场景。从"Prompt + few-shot"到"strict schema + Pydantic + 重试 + 降级"，越严越贵；记住"约束往下沉"这条原则就够了。

一条可以带走的工程判断：**任何要从 LLM 拿数据进数据库 / 进下游系统的地方，都不要相信"模型能输出对的 JSON"**——永远在最外层套 Pydantic 校验，永远准备好至少一次重试。这不是"防御性编程"，这是 LLM 时代的常识。

> 💡 **预告**：明天 D13 不引入新知识点，专门用今天学的全套技巧做几个实战项目（信息抽取、报销单解析、旅行计划生成），把 JSON Mode、Structured Output、Pydantic、重试、降级这些都串起来跑一遍，最后整理一份"稳定输出 JSON 的 Checklist"放进自己的工程素材库——以后写任何 Agent 项目，照着这个 Checklist 走就不会翻车。后天 D14 是周五项目日，把 W2 学的 Function Calling + ReAct + 结构化输出全部整合到一个 CLI Agent 里——这就是从"看会"到"做会"的最后一公里。
