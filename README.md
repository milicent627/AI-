# BookWright — AI 小说写作与续写器

AI 驱动的智能小说写作工具，支持多模型续写、提示词编排、世界书分析、自动总结、伏笔管理等。

## 功能概览

| 功能 | 说明 |
|---|---|
| **AI 续写** | 普通续写、定向续写、分支续写，内嵌 AI 生成卡片（采纳/放弃） |
| **富文本编辑器** | tiptap 编辑器，中文衬线字体、首行缩进、智能标点（直引号→中文引号） |
| **多模型支持** | OpenAI（GPT-4o）、Anthropic（Claude）、DeepSeek，按用途独立配置 |
| **提示词编排** | 按功能（续写/润色/分析等）独立配置片段排序，可拖拽调序、开关、触发词匹配 |
| **世界书** | 角色/势力/地点/物品/力量体系/口头禅，自动 AI 提取 + 手动编辑 |
| **人物关系** | 角色间关系（师徒/恋人/仇敌等）自动提取 |
| **自动总结** | 小总结 + 大总结金字塔，降低上下文压力。级联替换：已总结内容自动折叠 |
| **长期伏笔** | 管理暗线/主线规划，自动检测新伏笔和旧伏笔推进/揭示 |
| **自动分章** | 达到目标字数后自动在完整句子边界切章 |
| **自动润色** | 独立配置润色模型，去 AI 味 |
| **手风琴侧边栏** | 章节/世界书/伏笔/总结分区，可拖拽调整宽度 |
| **存档隔离** | 每部小说独立 SQLite 存储，正文、总结、世界书、伏笔互不干扰 |
| **SillyTavern 兼容** | 世界书和提示词预设支持 ST 格式导入/导出 |

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python 3.11+ / FastAPI / SQLAlchemy async / SQLite |
| 前端 | React 18 / TypeScript / Vite / Tailwind CSS / tiptap |
| AI | OpenAI SDK / Anthropic SDK |

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+
- 至少一个 AI 模型的 API Key

### 安装

```bash
# 克隆仓库
git clone https://github.com/milicent627/AI-Bookwrighter.git
cd AI-Bookwrighter

# 安装后端依赖
cd backend
pip install -r requirements.txt

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

### 首次使用

1. 打开浏览器 → 点击右上角 **设置** ⚙️
2. 添加至少一个续写模型（填写 API Key、选择提供商和模型）
3. 返回首页 → 新建故事 → 进入编辑页
4. 在编辑器中写作或使用续写按钮让 AI 帮你写

## 项目结构

```
bookwrighttool/
├── backend/
│   └── app/
│       ├── main.py              # FastAPI 入口
│       ├── database.py           # 数据库引擎（NullPool）
│       ├── models/               # 数据模型
│       │   ├── story.py          # Story / Chapter / PromptOrderItem
│       │   ├── world_book.py     # WorldBookEntry / CharacterRelation
│       │   ├── summary.py        # Summary
│       │   ├── foreshadowing.py  # Foreshadowing
│       │   ├── prompt_preset.py  # PromptPreset / PromptFragment
│       │   └── model_config.py   # ModelConfig
│       ├── providers/            # AI 模型适配层（OpenAI / Anthropic / DeepSeek）
│       ├── services/             # 核心业务
│       │   ├── continuation.py   # AI 续写
│       │   ├── prompt_assembler.py  # 提示词组装（片段→消息列表）
│       │   ├── summarization.py  # 自动总结
│       │   ├── world_analysis.py # 世界书 AI 分析
│       │   ├── foreshadowing.py  # 伏笔检测
│       │   ├── polishing.py      # 文本润色
│       │   └── chapter_split.py  # 自动分章
│       ├── routers/              # API 路由
│       └── utils/                # 工具函数 + Prompt 模板
├── frontend/
│   └── src/
│       ├── pages/
│       │   ├── HomePage.tsx          # 故事列表
│       │   ├── EditorPage.tsx        # 写作编辑器（编排器）
│       │   ├── WorldBookEditPage.tsx  # 世界书条目编辑
│       │   ├── SettingsPage.tsx      # 模型 & 提示词预设
│       │   └── PromptOrderPage.tsx   # 提示词排序
│       ├── components/               # 可复用组件
│       │   ├── TiptapEditor.tsx      # tiptap 富文本编辑器
│       │   ├── AccordionSidebar.tsx  # 手风琴侧边栏
│       │   ├── ChapterList.tsx       # 章节列表
│       │   ├── WorldBookList.tsx     # 世界书浏览
│       │   ├── ForeshadowingList.tsx # 伏笔列表
│       │   ├── SummaryList.tsx       # 总结列表
│       │   ├── ContinuationControls.tsx # 续写控制栏
│       │   ├── TopToolbar.tsx        # 顶部工具栏
│       │   ├── AIAssistDialog.tsx    # AI 助手弹窗
│       │   └── tiptap/               # tiptap 扩展
│       │       ├── SmartPunctuation.ts  # 智能标点
│       │       ├── AICardNode.ts      # AI 生成卡片节点
│       │       └── AICardNodeView.tsx # AI 卡片 UI
│       ├── hooks/
│       │   ├── useSSEStream.ts   # SSE 流式封装
│       │   └── useSplitPane.ts   # 拖拽分割面板
│       ├── stores/
│       │   ├── storyStore.ts     # 故事/章节状态
│       │   └── editorStore.ts    # 编辑器 UI 状态
│       └── api/client.ts         # API 封装 + SSE 流式
├── data/                         # 运行时数据（gitignore）
│   ├── archives/                 # 各小说独立存档
│   └── index.sqlite              # 全局配置
└── scripts/start.bat             # 一键启动
```

## 模型角色说明

| 角色 | 推荐模型 | 说明 |
|---|---|---|
| 续写 | GPT-4o / Claude / DeepSeek | 主力创意写作，temperature 0.8-1.0 |
| 润色 | Claude / GPT-4o | 去 AI 味、优化表达，temperature 0.3-0.5 |
| 分析 | GPT-4o-mini / Claude Haiku | 总结/世界书/伏笔分析，成本优先 |

## License

MIT
