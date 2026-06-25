import asyncio
import os
import sys
import base64
from dotenv import load_dotenv

# 加载 .env 环境变量（需要你先配置好 DEEPSEEK_API_KEY）
load_dotenv("backend/.env")

# 引入我们写好的服务
sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))
from app.services import chat_response

async def main():
    if not os.getenv("DEEPSEEK_API_KEY") or os.getenv("DEEPSEEK_API_KEY") == "sk-placeholder":
        print("❌ 错误：请先在 backend/.env 中配置 DEEPSEEK_API_KEY")
        return

    print("🤖 正在连接 DeepSeek 并生成马克思的回复，请稍候...")
    
    # 模拟用户提问
    test_question = "你好，马克思，请用一句话评价现在的资本主义。"
    print(f"\n🗣️ 你的问题: {test_question}\n")
    
    try:
        # 调用核心逻辑
        result = await chat_response(test_question)
        
        print("✅ 成功获取回复！\n")
        print(f"📜 马克思的文字回复:\n{result['reply']}\n")
        
        # 将 base64 音频保存为真实的 mp3 文件
        audio_data = base64.b64decode(result["audio_base64"])
        output_file = "test_output.mp3"
        with open(output_file, "wb") as f:
            f.write(audio_data)
            
        print(f"🎵 语音已经成功生成，并保存在当前目录下的: {output_file}")
        print("👉 你可以去文件夹里双击播放听听看效果！")
        
    except Exception as e:
        print(f"❌ 运行报错了: {e}")

if __name__ == "__main__":
    asyncio.run(main())
