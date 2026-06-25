# Marx AI Assistant

**网页边缘悬浮的 3D 马克思 AI 助手** — 前端 3D Demo + 后端 FastAPI 服务

---

## 目录结构

```
Marx/
├── backend/
│   ├── main.py                  # 启动入口
│   ├── requirements.txt
│   ├── .env.example             # 环境变量模板
│   └── app/
│       ├── __init__.py          # FastAPI app factory + CORS
│       ├── prompts.py           # Marx System Prompt
│       ├── services.py          # LLM (OpenAI) + TTS (edge-tts) 封装
│       └── routers/
│           ├── __init__.py
│           └── chat.py          # /api/chat_text  /api/chat_voice
│
└── frontend/
    ├── index.html               # 完整单页 Demo
    └── assets/
        └── marx.glb             # ← 把你的 3D 模型放这里
```

---

## 快速启动

### 后端

```bash
cd backend

# 1. 创建虚拟环境
python -m venv .venv && source .venv/bin/activate

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置 API Key
cp .env.example .env
#   → 编辑 .env，填入 OPENAI_API_KEY 和 OPENAI_BASE_URL

# 4. 启动服务（热重载）
python main.py
# 服务运行在 http://localhost:8000
# 交互文档: http://localhost:8000/docs
```

### 前端

```bash
# 把 marx.glb 放到 frontend/assets/marx.glb
# 用任意静态服务器启动（不能直接双击 HTML，否则跨域读取 glb 会失败）

cd frontend
npx serve .
# 访问 http://localhost:3000
```

---

## 接口说明

| 接口 | 方法 | 请求 | 返回 |
|------|------|------|------|
| `/api/chat_text` | POST | `{"message": "..."}` | `{"reply": "..."}` |
| `/api/chat_voice` | POST | FormData `audio=<file>` | MP3 二进制流，`X-Marx-Reply` Header 含回复文字，`X-Transcript` Header 含识别文字 |

---

## 关键依赖版本

| 包 | 用途 |
|----|------|
| `fastapi` | Web 框架 |
| `openai` | LLM 调用（OpenAI 兼容接口）|
| `openai-whisper` | 本地语音识别 |
| `edge-tts` | 微软 TTS，无需 API Key |
| `three@0.165` | 3D 渲染（CDN，无需安装）|

> **Whisper 首次运行**会自动下载 `base` 模型（~150 MB）。  
> 如需更高精度可在 `chat.py` 中改为 `whisper.load_model("medium")`。
