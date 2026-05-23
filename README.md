# BookWright — AI 小说写作与续写器

AI 驱动的智能小说写作工具，支持多模型续写、世界书分析、自动总结、伏笔管理等。

## 功能概览

| 功能 | 说明 |
|---|---|
| **AI 续写** | 支持普通续写、定向续写、分支续写，可控制文风、剧情方向、字数 |
| **多模型支持** | OpenAI（GPT-4o）、Anthropic（Claude）、DeepSeek，三种模型可分别配置不同用途 |
| **自动总结** | 小总结（每10章）+ 大总结金字塔，降低上下文压力，防止 AI "失忆" |
| **世界书分析** | 自动提取角色、势力、地点、物品、口头禅，动态更新世界观，含完整角色详情卡片 |
| **人物关系网** | 角色间关系（师徒/恋人/仇敌等）自动提取 + 可视化 |
| **长期伏笔** | 独立管理暗线、主线规划，自动检测新伏笔和旧伏笔推进 |
| **自动分章节** | 达到目标字数后自动在完整句子边界切章 |
| **原文章节库** | 自动归档已完结章节，支持查看、导出（txt/html） |
| **自动润色** | 可独立配置润色模型，对新增内容去 AI 味 |
| **存档隔离** | 每部小说独立 SQLite 存储，正文、总结、世界书、伏笔互不干扰 |

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python 3.11+ / FastAPI / SQLAlchemy async / SQLite |
| 前端 | React 18 / TypeScript / Vite / Tailwind CSS |
| AI | OpenAI SDK / Anthropic SDK / httpx |

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+
- 至少一个 AI 模型的 API Key

### 安装

```bash
# 克隆仓库
git clone https://github.com/milicent627/AI-.git
cd AI-

# 安装后端依赖
cd backend
pip install -r requirements.txt  # 或 pip install fastapi uvicorn sqlalchemy aiosqlite openai anthropic httpx python-multipart sse-starlette jieba tiktoken pydantic pydantic-settings

# 安装前端依赖
cd ../frontend
npm install
```

### 启动

```bash
# 终端1：启动后端（端口 8001）
cd backend
uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload

# 终端2：启动前端（端口 5173）
cd frontend
npx vite

# 浏览器打开 http://localhost:5173
```

或者直接双击 `scripts/start.bat` 一键启动。

### 首次使用

1. 打开浏览器 → 点击右上角 **设置** ⚙️
2. 添加至少一个续写模型（填写 API Key、选择提供商和模型）
3. 返回首页 → 新建故事 → 进入编辑页
4. 在编辑器中写作或使用续写按钮让 AI 帮你写

## 项目结构

```
AI-/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口
│   │   ├── models/              # 数据模型（故事/章节/总结/世界书/伏笔）
│   │   ├── providers/           # AI 模型适配层（OpenAI/Anthropic/DeepSeek）
│   │   ├── services/            # 核心业务（续写/总结/分析/分章/润色）
│   │   ├── routers/             # API 路由
│   │   └── utils/               # 工具函数 + Prompt 模板
│   └── pyproject.toml
├── frontend/
│   └── src/
│       ├── pages/
│       │   ├── HomePage.tsx     # 故事列表
│       │   ├── EditorPage.tsx   # 写作编辑器（核心页面）
│       │   └── SettingsPage.tsx # 模型配置
│       └── api/client.ts       # API 封装 + SSE 流式
├── data/                        # 运行时数据（gitignore）
│   ├── archives/                # 各小说独立存档
│   └── index.sqlite             # 全局配置
└── scripts/start.bat            # 一键启动
```

## 模型角色说明

| 角色 | 推荐模型 | 说明 |
|---|---|---|
| 续写模型 | GPT-4o / Claude / DeepSeek | 主力创意写作，temperature 建议 0.8-1.0 |
| 润色模型 | Claude / GPT-4o | 去 AI 味、优化表达，temperature 建议 0.3-0.5 |
| 分析模型 | GPT-4o-mini / Claude Haiku | 总结/世界书/伏笔分析，成本优先 |

## License

MIT
