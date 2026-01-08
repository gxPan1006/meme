# Meme Analyzer

表情包分析工具，使用豆包 API 分析表情包的情绪、使用场景和设计灵感。

## 安装

```bash
# 克隆项目
git clone <repo-url>
cd meme

# 安装（开发模式）
pip install -e .
```

## 环境变量

| 变量 | 必需 | 描述 | 默认值 |
|------|------|------|--------|
| `ARK_API_KEY` | ✅ | 豆包 API 密钥 | - |
| `ARK_API_URL` | ❌ | API 端点 | `https://ark.cn-beijing.volces.com/api/v3/chat/completions` |
| `ARK_MODEL` | ❌ | 模型名称 | `doubao-seed-1-8-251228` |
| `ANALYSIS_HOST` | ❌ | 服务器地址 | `127.0.0.1` |
| `ANALYSIS_PORT` | ❌ | 服务器端口 | `8000` |

## 使用方法

### 批量分析表情包

```bash
# 基础用法
meme-analyze input.json output.json

# 使用 data URL 模式（将图片转为 base64）
meme-analyze input.json output.json --image-mode data

# 限制处理数量并支持断点续传
meme-analyze input.json output.json --limit 100 --resume

# 查看帮助
meme-analyze --help
```

### 过滤静态表情包

```bash
# 过滤掉 GIF 动图
meme-filter all_memes.json static_memes.json
```

### 启动 API 服务器

```bash
# 启动服务器
meme-server

# 指定地址和端口
meme-server --host 0.0.0.0 --port 8080

# 调用 API
curl -X POST http://127.0.0.1:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/meme.jpg"}'
```

## 数据格式

### 输入格式

```json
{
  "data": [
    {"name": "meme1.jpg", "url": "https://...", "category": "funny"},
    {"name": "meme2.png", "url": "https://..."}
  ]
}
```

或者直接使用数组：

```json
[
  {"name": "meme1.jpg", "url": "https://..."}
]
```

### 输出格式

```json
[
  {
    "name": "meme1.jpg",
    "category": "funny",
    "url": "https://...",
    "analysis": {
      "所代表情绪": "开心",
      "使用场景": "朋友聊天时表达愉悦",
      "设计灵感": "卡通人物夸张表情"
    }
  }
]
```

## 项目结构

```
meme/
├── pyproject.toml          # 项目配置
├── README.md               # 本文件
├── AGENTS.md               # 工程规范
└── src/meme/
    ├── __init__.py         # 包入口
    ├── cli.py              # CLI 入口点
    ├── config.py           # 配置管理
    ├── client.py           # API 客户端
    ├── exceptions.py       # 异常定义
    ├── analyze_memes.py    # 批量分析逻辑
    ├── filter_static_meme.py # 过滤逻辑
    └── api.py              # HTTP 服务器
```