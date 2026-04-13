"""
Day 02 - API 调用基础
=====================
知识点:
- OpenAI API 的基本调用方式
- Chat Completions vs Responses API
- 请求参数详解 (model, temperature, max_tokens)
- 流式输出 (Streaming)

实践任务: 封装一个通用的 API 调用函数，实现流式与非流式两种模式
"""

import sys
from pathlib import Path

root = Path.cwd()
while not (root / "pyproject.toml").exists() and root != root.parent:
    root = root.parent
sys.path.insert(0, str(root))


from app.config import settings  
from openai import OpenAI  
  

client = OpenAI(
	api_key=settings.openai_api_key,  
	base_url=settings.openai_base_url,
) 


def chat():
    
    messages = [{"role": "system", "content": "算命大师"}]
    
    print("开始对话（输入 '/quit' 退出，输入 '/clear' 清空历史）")
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
                temperature=0.7,
                max_completion_tokens=200,
                # reasoning={"effort": "low"},
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
