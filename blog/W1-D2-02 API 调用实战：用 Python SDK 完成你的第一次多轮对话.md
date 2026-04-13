# API 调用实战：用 Python SDK 完成你的第一次多轮对话

---

> 摘要：上一篇我们搞清楚了模型参数的门道，这一篇正式动手——用 Python SDK 发起第一个 API 请求，手动维护消息列表，完成一次真正的多轮对话。这是后续所有 Agent 开发的起点。

## 一、为什么要从 API 调用开始？

很多同学一上来就想用框架（LangChain、LlamaIndex），但如果你不理解底层的 API 调用流程，后面遇到问题会完全不知道从哪里排查。

原因很简单：

1. **所有框架底层都在调 API**——LangChain 的 `ChatOpenAI`、LlamaIndex 的 `OpenAI`，最终都是在帮你发 HTTP 请求
2. **Agent 的核心循环就是反复调 API**——理解一次调用，才能理解一百次调用
3. **调试时你需要看懂原始请求和响应**——框架封装了太多细节，出了问题得回到原始层面

所以，先踏踏实实跑通一次 API 调用。

---

## 二、工程化最佳实践

pip 安装 openai 这里使用qwen模型，只需要改 `base_url` 和 `api_key`，代码几乎不用动。

推荐用环境变量管理或者 `.env` ，**不要把 Key 写死在代码里**：

```bash
# 推荐结构（清晰分层）
project/
├── app/
│   ├── config.py        # Pydantic Settings
│   └── main.py
├── .env
├── .env.example
└── pyproject.toml
```

```python
# .env 规范
OPENAI_API_KEY=sk-xxxxxx
OPENAI_BASE_URL==https://dashscope.aliyuncs.com/compatible-mode/v1
```
注意：
- `.env` **永远不进 git**  另外最好提供 `.env.example` 给团队

用 **pydantic-settings（v2）**，不是老的 BaseSettings
```python
# app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    openai_api_key: str
    openai_base_url: str = "https://xxx/v1"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # 防止多余变量报错
    )

settings = Settings()
```

---

## 三、第一个 API 请求

### 最简形式

```python
from app.config import settings  
from openai import OpenAI  
  
client = OpenAI(
	api_key=settings.openai_api_key,  
	base_url=settings.openai_base_url,  
)  

response = client.chat.completions.create(
    model="qwen3.5-flash",
    messages= [{"role": "user", "content": "你是谁？" }],
)

print(response.choices[0].message.content)

```

这就是一次完整的 API 调用。你发了一条消息，模型返回了一条回答。

### 解剖响应对象

别急着写下一个请求，先看看返回的 `response` 里有什么：

```python
print(type(response))
# <class 'openai.types.chat.chat_completion.ChatCompletion'>

print(response.model_dump_json(indent=2))
```

```json
{
  "id": "chatcmpl-xxx",
  "choices": [
    {
      "finish_reason": "stop",
      "index": 0,
      "logprobs": null,
      "message": {
        "content": "你好！我是Qwen3.5，xxxx 😊",
        "role": "assistant",
        "audio": null,
        "function_call": null,
        "tool_calls": null,
        "reasoning_content": "嗯，用户问“你是谁？”，我需要先明确自己的身份.."
      }
    }
  ],
  "created": 1775917259,
  "model": "qwen3.5-flash",
  "object": "chat.completion",
  "usage": {
    "completion_tokens": 428,
    "prompt_tokens": 12,
    "total_tokens": 440,
    "completion_tokens_details": {
      "reasoning_tokens": 274,
      "text_tokens": 428
    },
    ...
  }
}
```

几个关键字段：

| 字段                         | 含义          | 你该关注的点                                |
| -------------------------- | ----------- | ------------------------------------- |
| `choices[0].message`       | 模型的回答       | `role` 是 `assistant`，`content` 是文本内容  |
| `choices[0].finish_reason` | 停止原因        | `stop` 表示正常结束，`length` 表示被截断（上一篇讲过的坑） |
| `usage.prompt_tokens`      | 输入消耗的 Token | 和 API 计费直接挂钩                          |
| `usage.completion_tokens`  | 输出消耗的 Token | 同上                                    |
| `usage.total_tokens`       | 总 Token 数   | 监控成本的核心指标                             |

---

## 四、手动维护消息列表：多轮对话的核心

### 模型默认无状态

**模型不记得上一次对话。每次 API 调用都是独立的。要实现多轮对话，你必须自己把历史消息传回去。

### 最简多轮对话

```python
from openai import OpenAI

client = OpenAI()

# 初始化消息列表
messages = [
    {"role": "system", "content": "你是一位耐心的编程老师。"}
]

# 第一轮
messages.append({"role": "user", "content": "什么是变量？"})
response = client.chat.completions.create(
    model="qwen3.5-flash",
    messages=messages
)
assistant_msg = response.choices[0].message.content
messages.append({"role": "assistant", "content": assistant_msg})
print(f"助手: {assistant_msg}")

# 第二轮 —— 模型能"记得"上一轮，是因为我们把历史传回去了
messages.append({"role": "user", "content": "能给一个 Python 的例子吗？"})
response = client.chat.completions.create(
    model="qwen3.5-flash",
    messages=messages
)
assistant_msg = response.choices[0].message.content
messages.append({"role": "assistant", "content": assistant_msg})
print(f"助手: {assistant_msg}")
```

看明白了吗？每一轮对话做的事情是：

1. 把用户新消息 `append` 到 `messages`
2. 把完整的 `messages` 发给 API
3. 把模型回复也 `append` 到 `messages`
4. 下一轮再带上所有历史

```text
第一轮发送: [system, user_1]
第二轮发送: [system, user_1, assistant_1, user_2]
第三轮发送: [system, user_1, assistant_1, user_2, assistant_2, user_3]
...
```

消息列表越来越长，Token 越来越多，成本越来越高——这就是为什么后面我们要学 Context Engineering。

---

## 五、封装一个交互式多轮对话

理解了原理，我们来写一个完整的交互式对话程序：

```python

def chat():
    client = OpenAI()
    
    messages = [{"role": "system", "content": "算命大师"}]
    
    print("开始对话（输入 'quit' 退出，输入 'clear' 清空历史）")
    print("-" * 50)
    
    while True:
        user_input = input("\n你: ").strip()
        
        if not user_input:
            continue
        if user_input.lower() == "/quit":
            print("再见！")
            break
        if user_input.lower() == "/clear":
            messages = [messages[0]]  # 只保留 system 消息
            print("[历史已清空]")
            continue
        
        # 1. 追加用户消息
        messages.append({"role": "user", "content": user_input})
        
        try:
            # 2. 调用 API
            response = client.chat.completions.create(
                model="qwen3.5-flash",
                messages=messages,
                temperature=0.7
            )
            
            # 3. 提取回复
            assistant_msg = response.choices[0].message.content
            
            # 4. 追加到历史
            messages.append({"role": "assistant", "content": assistant_msg})
            
            # 5. 显示回复和 Token 用量
            print(f"\n助手: {assistant_msg}")
            print(f"[Token 用量: 输入={response.usage.prompt_tokens}, "
                  f"输出={response.usage.completion_tokens}, "
                  f"总计={response.usage.total_tokens}]")
            
        except Exception as e:
            print(f"\n[错误] {e}")
            messages.pop()  # 移除刚才追加的用户消息，避免污染历史

if __name__ == "__main__":
    chat()
```


---

## 六、流式输出：让回复像"打字"一样出现

上面的例子中，用户要等模型完整生成后才能看到回复。实际产品中通常用**流式输出（Streaming）**，让回复逐字出现：

```python
# stream=True 开启流式
stream = client.chat.completions.create(
    model="qwen3.5-flash",
    messages=messages,
    stream=True
)

print("助手: ", end="", flush=True)
full_response = ""
for chunk in stream:
    delta = chunk.choices[0].delta
    if delta.content:
        print(delta.content, end="", flush=True)
        full_response += delta.content

print()  # 换行
# full_response 就是完整的回复，可以追加到 messages 里
```

流式输出的核心点：

- `stream=True`：告诉 API 不要等生成完再返回，而是边生成边推送
- 返回的是一个**迭代器**，每个 `chunk` 包含一小段内容（通常几个 Token）
- `chunk.choices[0].delta.content` 是增量内容
- 需要自己拼接 `full_response` 用于后续存入消息历史


---

## 七、两套 API 形态：Chat Completions vs Responses

OpenAI（以及兼容 OpenAI 接口的 Qwen 等厂商）目前有**两套不同的 API 端点**，在 Python SDK 中对应两个完全不同的调用入口。搞混了会直接报错，这里帮你彻底理清。

### 1. Chat Completions（经典接口）

这是最早、最通用的接口，也是前面所有示例用的方式：

```python
response = client.chat.completions.create(
    model="qwen3.5-flash",
    messages=[{"role": "user", "content": "你好"}]
)
print(response.choices[0].message.content)
```

**支持的核心参数：**

| 参数                                     | 说明                       |
| -------------------------------------- | ------------------------ |
| `model`                                | 模型名称                     |
| `messages`                             | 消息列表（`role` + `content`） |
| `temperature`                          | 控制随机性                    |
| `max_tokens` / `max_completion_tokens` | 最大输出长度                   |
| `top_p`、`stop`、`stream`                | 其他生成控制参数                 |
| `tools` / `tool_choice`                | 函数调用（Function Calling）   |
| `response_format`                      | 结构化输出（JSON Schema）       |

**不支持的参数：** `reasoning`、`input`、`instructions`、`previous_response_id` 等。如果你传了 `reasoning`，SDK 会直接报错：

```
TypeError: got an unexpected keyword argument 'reasoning'
```

**响应结构：** 通过 `response.choices[0].message.content` 获取回复。

### 2. Responses（新一代接口）

这是 OpenAI 推出的新接口，专为 Agent 和复杂工作流设计：

```python
response = client.responses.create(
    model="gpt-5",
    instructions="你是一位编程老师。",
    input="什么是变量？",
    reasoning={"effort": "low"},
)
print(response.output_text)
```

**与 Chat Completions 的关键差异：**

| 特性 | Chat Completions | Responses |
|------|-----------------|-----------|
| **调用方式** | `client.chat.completions.create()` | `client.responses.create()` |
| **输入参数** | `messages`（消息列表） | `input`（字符串或消息列表） |
| **系统提示** | 放在 `messages` 里，`role: "system"` | 独立的 `instructions` 参数 |
| **获取回复** | `response.choices[0].message.content` | `response.output_text` |
| **推理控制** | ❌ 不支持 `reasoning` | ✅ `reasoning={"effort": "low/medium/high"}` |
| **多轮对话** | 手动维护 `messages` 列表 | 可用 `previous_response_id` 自动续接 |
| **内置工具** | ❌ 需自己编排 | ✅ `web_search`、`code_interpreter` 等 |
| **状态管理** | 无状态，完全手动 | 可选服务端存储（`store: true`） |

### 3. 多轮对话方式对比

**Chat Completions 风格**——手动维护消息列表（前面的例子都是这种）：

**Responses 风格**——用 `previous_response_id` 自动续接上下文：

```python
res1 = client.responses.create(
    model="gpt-5",
    instructions="你是一位助手。",
    input="法国的首都是哪？",
    store=True
)

res2 = client.responses.create(
    model="gpt-5",
    input="人口多少？",
    previous_response_id=res1.id,  # 自动带上之前的上下文
    store=True
)
```

Responses 的多轮对话不需要你手动维护消息列表，服务端帮你存了。

### 4. extra_body：Chat Completions 的「扩展后门」

前面说 Chat Completions 不支持 `reasoning` 参数，那用 Qwen 这类模型时，怎么在 Chat Completions 里控制思考模式？

答案是 **`extra_body`**。

OpenAI 的 Python SDK 在 `create()` 方法里预留了一个 `extra_body` 参数，它会把你传入的字典**原封不动地合并到 HTTP 请求体**中发出去。这意味着：即使 SDK 本身不认识某个参数，你也能通过 `extra_body` 把它「夹带」到请求里，让服务端去处理。

#### Qwen 的用法：`enable_thinking` + `thinking_budget`

通义千问的 Qwen3 系列支持「混合思考模式」——模型可以先思考再回答，也可以直接回答。控制方式就是通过 `extra_body` 传入非标准参数：

```python
# 开启思考模式
completion = client.chat.completions.create(
    model="qwen-plus",
    messages=[{"role": "user", "content": "9.9 和 9.11 谁大？"}],
    extra_body={
        "enable_thinking": True,       # 开启思考
        "thinking_budget": 2048        # 可选：限制思考过程最多用 2048 个 Token
    },
    stream=True,
)

# 流式读取：思考内容在 reasoning_content，回复在 content
for chunk in completion:
    if not chunk.choices:
        continue
    delta = chunk.choices[0].delta
    # 思考过程
    if hasattr(delta, "reasoning_content") and delta.reasoning_content:
        print(f"[思考] {delta.reasoning_content}", end="", flush=True)
    # 正式回复
    if delta.content:
        print(delta.content, end="", flush=True)
```

#### 各厂商的扩展参数对比

**这里是最容易踩坑的地方**——各厂商在 Chat Completions 上扩展了自己的思考控制参数，参数名和格式**互不相同**，都需要通过 `extra_body` 传：

| 厂商 | 扩展参数 | 格式 | 示例 |
|------|---------|------|------|
| 通义千问 | `enable_thinking` | 布尔值 | `extra_body={"enable_thinking": True}` |
| 通义千问 | `thinking_budget` | 整数（限制思考 Token 数） | `extra_body={"thinking_budget": 2048}` |
| 通义千问 | `enable_search` | 布尔值（联网搜索） | `extra_body={"enable_search": True}` |
| DeepSeek | `thinking` | 对象 `{"type": "enabled/disabled"}` | `extra_body={"thinking": {"type": "enabled"}}` |
| 豆包（火山方舟） | `thinking` | 对象 `{"type": "enabled/disabled/auto"}` | `extra_body={"thinking": {"type": "disabled"}}` |

注意看区别：

```python
# 通义千问 —— 布尔值风格
extra_body={"enable_thinking": True}
# DeepSeek —— 对象风格
extra_body={"thinking": {"type": "enabled"}}
# 豆包 —— 同样是对象风格，但多一个 auto 选项
extra_body={"thinking": {"type": "auto"}}
```

DeepSeek 和豆包的 `thinking` 参数格式一样（都是 `{"type": "..."}` ），但和通义千问的 `enable_thinking` 不同。如果项目需要兼容多个厂商，就得根据 provider 做判断：

```python
def get_thinking_extra_body(provider: str, enabled: bool) -> dict:
    """根据厂商返回正确的思考控制参数"""
    if provider == "qwen":
        return {"enable_thinking": enabled}
    elif provider in ("deepseek", "doubao"):
        return {"thinking": {"type": "enabled" if enabled else "disabled"}}
    return {}

# 调用时
extra_body = get_thinking_extra_body("deepseek", enabled=True)
response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[...],
    extra_body=extra_body,
)
```

#### 响应里的思考内容在哪？

开启思考后，模型的思考过程通过 `reasoning_content` 字段返回（不是 `content`）：

```python
# 非流式
msg = completion.choices[0].message
print(msg.reasoning_content)  # 思考过程
print(msg.content)            # 正式回复

# 流式
for chunk in stream:
    delta = chunk.choices[0].delta
    delta.reasoning_content   # 增量思考内容
    delta.content             # 增量回复内容
```

这和 OpenAI Responses 接口的 `reasoning` 参数是**完全不同的机制**——一个是服务端扩展参数通过 `extra_body` 传，一个是 SDK 原生支持的标准参数。但最终效果类似：都是控制模型「想多深再回答」。

### 6. 怎么选？

| 场景 | 推荐接口 | 理由 |
|------|---------|------|
| 学习阶段、简单对话 | Chat Completions | 概念简单，生态兼容性最好 |
| 需要跨厂商切换（Qwen、DeepSeek 等） | Chat Completions | 几乎所有厂商都兼容这套接口 |
| 使用推理模型（o3、GPT-5 等） | Responses | 推理模型在 Responses 下表现更好，且支持 `reasoning` 控制 |
| 构建 Agent、需要内置工具 | Responses | 原生支持 `web_search`、`code_interpreter` 等 |
| 需要服务端管理对话状态 | Responses | `previous_response_id` 省去手动管理历史的麻烦 |

> **本系列教程以 Chat Completions 为主**。原因很简单：它是行业通用标准，Qwen、DeepSeek、Gemini 等国内外模型都兼容；而且理解了手动管理消息列表，你才真正理解了 Agent 的底层运作。等你需要用到推理模型或内置工具时，再切到 Responses 只是换个调用方式而已。



---

## 八、一些实战中会遇到的问题

### 1. 消息列表太长怎么办？

随着对话轮次增加，`messages` 会越来越长。最简单的应对方式：

```python
MAX_HISTORY = 20  # 最多保留最近 20 条消息

if len(messages) > MAX_HISTORY + 1:  # +1 是 system 消息
    messages = [messages[0]] + messages[-(MAX_HISTORY):]
```

这是最粗暴的截断策略。更优雅的方式（滑动窗口 + 摘要压缩）会在后面 Context Engineering 那节详细讲。

### 2. API 调用失败怎么办？

网络请求总会有失败的时候。基本的重试逻辑：

---

## 九、LLM 调用耗时统计：你该关注哪些性能指标？

调 API 不仅要关注"回答得对不对"，还要关注"回答得快不快"。在 Agent 场景中，一个循环可能调用模型 5-10 次，每次多慢一点，用户体验就差一截。

### 三个核心指标

| 指标 | 英文 | 含义 | 为什么重要 |
|------|------|------|-----------|
| 首 Token 耗时 | TTFT (Time To First Token) | 从发送请求到收到第一个 Token 的时间 | 直接决定用户"感觉快不快" |
| 总耗时 | Total Latency | 从发送请求到收到最后一个 Token 的时间 | 决定整个调用的端到端时长 |
| 推理速度 | Tokens Per Second (TPS) | 每秒生成多少个 Token | 衡量模型的吞吐能力 |

#### 首 Token 耗时（TTFT）

TTFT 是用户体验最敏感的指标。它反映的是模型从接收请求到"开始说第一个字"的延迟：

```text
用户发送请求 ──────── 等待 ────────> 第一个 Token 到达
              |<--- TTFT --->|
```

影响 TTFT 的因素：
- **输入长度**：输入 Token 越多，模型处理（Prefill 阶段）越慢，TTFT 越高
- **模型大小**：参数量越大，首次推理越慢
- **推理模型的 Thinking**：o3、GPT-5 等推理模型会先做内部推理，TTFT 会显著更长
- **服务端负载**：高峰期排队也会影响

#### 总耗时（Total Latency）

从请求发出到完整响应返回的时间。计算公式：

```text
总耗时 ≈ TTFT + (输出 Token 数 / TPS)
```

#### 推理速度（TPS）

每秒生成的 Token 数量。注意，TPS 通常指的是**生成阶段**（Decode）的速度，不包括 Prefill 阶段：

```text
TPS = 输出 Token 数 / (总耗时 - TTFT)
```


### 流式场景：统计 TTFT + TPS

**谁先到就记谁为 TTFT**

```
推理模型流：  [reasoning_content...] → [content...]  
                ↑ ttft 在这里记录        ↑ first_content_time  
  
普通模型流：  [content...]  
                ↑ ttft 在这里记录（同时也是 first_content_time）  

```

下面代码：
```python
import time  
# ── 流式请求 ──────────────────────────────────────────────────────  
start = time.time()  
  
stream = client.chat.completions.create(  
    model='qwen3.5-flash',  
    messages = [{"role": "user", "content": "200字介绍一下Python"}]  
    stream=True,  
    stream_options={"include_usage": True}  
)  
  
# ── 状态变量 ──────────────────────────────────────────────────────  
ttft = None                  # 首 token 时间（不管是思考还是正文）  
first_content_time = None    # 第一个 content token 的时间戳  
is_reasoning_model = False   # 自动检测是否为推理模型  
  
full_thinking = ""  
full_response = ""  
completion_tokens = 0  
  
# ── 遍历流 ────────────────────────────────────────────────────────  
for chunk in stream:  
    now = time.time()  
  
    # 最后一个 chunk 可能 choices 为空，只带 usage  
    if chunk.choices:  
        delta = chunk.choices[0].delta  
  
        # ① 检测推理 token（reasoning_content）  
        reasoning_content = getattr(delta, "reasoning_content", None)  
        if reasoning_content:  
            is_reasoning_model = True  
            if ttft is None:  
                ttft = now - start  
            full_thinking += reasoning_content  
  
        # ② 检测正文 token（content）  
        if delta.content:  
            if ttft is None:  
                ttft = now - start  
            if first_content_time is None:  
                first_content_time = now  
            full_response += delta.content  
  
    # ③ 记录 usage  
    if chunk.usage:  
        completion_tokens = chunk.usage.completion_tokens  
  
# ── 计算指标 ──────────────────────────────────────────────────────  
total_time = time.time() - start  
  
# 思考耗时（仅推理模型）  
thinking_time = None  
if is_reasoning_model and first_content_time:  
    thinking_time = first_content_time - start  
  
# 解码速度：从第一个 content token 到结束  
if first_content_time:  
    decode_time = time.time() - first_content_time  
elif ttft is not None:  
    decode_time = total_time - ttft  
else:  
    decode_time = total_time  
  
tps = completion_tokens / decode_time if decode_time > 0 else 0  
  
# ── 打印结果 ──────────────────────────────────────────────────────  
print(f"模型       : {model}")  
print(f"模型类型   : {'推理模型 🧠' if is_reasoning_model else '普通模型'}")  
print(f"首 Token   : {ttft:.3f}s" + (" （首个思考 token）" if is_reasoning_model else ""))  
if thinking_time is not None:  
    print(f"思考耗时   : {thinking_time:.2f}s")  
print(f"总耗时     : {total_time:.2f}s")  
print(f"输出 Token : {completion_tokens}")  
print(f"推理速度   : {tps:.1f} tokens/s")  
  
# ── 打印内容 ──────────────────────────────────────────────────────  
if full_thinking:  
    print(f"\n{'='*50}")  
    print(f"【思考过程】")  
    print(full_thinking[:300] + ("..." if len(full_thinking) > 300 else ""))  
  
print(f"\n{'='*50}")  
print(f"【回答】")  
print(full_response)  

```

输出：
![](https://limbo.oss-cn-beijing.aliyuncs.com/wiki/20260412000035697.png)


### 实际场景参考值

不同模型和场景下的性能差异很大，以下是一些粗略参考：

| 模型类型          | TTFT     | TPS    | 备注                   |
| ------------- | -------- | ------ | -------------------- |
| 小模型           | 0.2~0.5s | 80~150 | 速度快，适合 Agent 循环      |
| 大模型           | 0.5~2s   | 40~80  | 质量高，速度适中             |

> 这些数值仅供参考，实际取决于输入长度、服务端负载、网络延迟等因素。

### 在 Agent 开发中为什么要关注这些？

Agent 的核心是**多轮循环调用**模型。假设一个任务需要 5 轮 ReAct 循环：

- 如果每轮 TTFT 2s + 生成 1s = 3s → 总耗时 **15s**
- 如果每轮 TTFT 0.5s + 生成 0.5s = 1s → 总耗时 **5s**

这就是为什么很多 Agent 框架会在不需要深度推理的步骤选用更快的小模型——不是所有步骤都需要最强的模型，**用对模型比用好模型更重要**。

---

## 十、小结

这一篇我们完成了 API 调用的全部核心操作：

1. **单次调用**：构造 `messages`，调 `chat.completions.create`，拿 `choices[0].message.content`
2. **多轮对话**：每轮把用户消息和模型回复都 `append` 到 `messages`，下次带上完整历史
3. **流式输出**：`stream=True`，逐 chunk 读取 `delta.content`
4. **跨厂商调用**：大部分厂商兼容 OpenAI 接口，改 `base_url` 即可

关键心智模型：**API 调用 = 构造消息列表 + 发送 + 接收 + 追加历史**。后面做 Agent 时，不管循环多少轮、调多少工具，底层都是这个模式。

> 💡 **预告**：现在你会调 API、会手动维护消息了，但随着对话越来越长，消息列表膨胀、Token 成本飙升、关键信息被稀释……这些问题怎么办？下一篇我们进入**多轮对话与消息管理**，学习 Token 计数、截断策略和对话历史管理的实用技巧。
