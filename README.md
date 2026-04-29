<p align="center">
  <pre>
   ___     ___      _    ___ 
  / __|___/ _ \    /_\  |_ _|
 | (__/ _ \ (_) |  / _ \  | | 
  \___\___/\___/  /_/ \_\|___|
  </pre>
</p>

<h3 align="center">LLM API 聚合网关 · 统一入口 · 智能路由 · 自动容灾</h3>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-green" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.110+-blue" alt="FastAPI">
  <img src="https://img.shields.io/badge/Vue-3.5+-brightgreen" alt="Vue">
  <img src="https://img.shields.io/badge/SQLite-3-green" alt="SQLite">
  <img src="https://img.shields.io/badge/license-MIT-red" alt="License">
</p>

---

## 为什么需要 co-api？

当你同时使用多个 LLM 平台（DeepSeek、Kimi、OpenAI、Anthropic...），每个都有独立的 API Key、不同的 Base URL、不同的调用方式。co-api 将它们统一为一个 OpenAI 兼容的入口，自动处理：

- **负载均衡** — 多个渠道轮询/加权/粘性调度
- **故障转移** — 主渠道失败自动切换到备选
- **协议转换** — OpenAI ↔ Anthropic ↔ Gemini 无缝互转
- **健康监控** — 熔断器自动隔离故障渠道
- **请求审计** — 全量日志、Token 统计、实时看板

## 架构

```
                     ┌──────────────┐
    Client ──────────│   co-api     │
    (OpenAI SDK      │  :3000/v1    │
     Claude Code     │              │
     opencode ...)   │  ┌──────────┐│    ┌──────────┐
                     │  │ 路由引擎  ││───│ DeepSeek │
                     │  │ 负载均衡  ││───│ Kimi     │
                     │  │ 协议转换  ││───│ OpenAI   │
                     │  └──────────┘│───│ Anthropic│
                     │  ┌──────────┐│───│ Gemini   │
                     │  │ 熔断检测  ││───│ ...      │
                     │  │ 日志审计  ││    └──────────┘
                     │  └──────────┘│
                     │  ┌──────────┐│
                     │  │ Admin UI ││
                     │  │ (Vue3)  ││
                     │  └──────────┘│
                     └──────────────┘
```

## 功能

### 核心能力

| 模块 | 说明 |
|------|------|
| 多平台接入 | DeepSeek, Kimi, Kimi Coding, 智谱, 通义, SiliconFlow, OpenAI, Anthropic, Gemini |
| 一键创建渠道 | 选择平台预设 → 输 API Key → 自动同步模型 |
| 模型池管理 | 多渠道组合成一个模型名，自定义权重/优先级 |
| 4 种负载均衡 | 加权随机、轮询、故障转移、会话粘性（Token+模型 5 分钟 TTL） |
| 协议自动转换 | 客户端 OpenAI 格式 ↔ 上游 Anthropic / Gemini 格式 |
| reasoning_effort | 推理强度参数透传，自动映射为 Anthropic thinking |
| Vision 路由 | 图片请求自动过滤非视觉渠道 |
| 上下文压缩 | 超长对话自动摘要压缩（auto_compact） |
| 熔断与恢复 | 连续失败自动熔断，冷却后自动探测恢复，重启状态持久化 |

### 管理面板

| 页面 | 说明 |
|------|------|
| 数据看板 | 实时统计卡片、7 天趋势图、模型分布图、最近活动、渠道健康 |
| 渠道管理 | 卡片式布局、一键开关、测试连接、自动同步模型 |
| 模型池 | 多渠道路由组、权重/优先级/别名配置 |
| API 令牌 | Token 管理，按 Token 统计用量 |
| 请求记录 | 全量日志、请求/响应详情、重放功能 |
| 统计报表 | 多维度聚合：日/小时/模型/渠道/Token |
| 平台文档 | 负载均衡执行流程、协议转换矩阵、数据流示意 |
| AI 生图 | 调用 GPT Image 模型生成/编辑图片 |

### 客户端接入

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://127.0.0.1:3000/v1",
    api_key="sk-Tb_8QSlJmLS3WdiCTKnZ4kyrcQQ6eYcuIZKGU46LMCo"
)

# 所有渠道的模型统一以 OpenAI 格式调用
response = client.chat.completions.create(
    model="deepseek-chat",          # 自动路由到 DeepSeek
    messages=[{"role": "user", "content": "你好"}]
)
```

Claude Code 配置（`~/.claude/settings.json`）：
```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "http://127.0.0.1:3000",
    "ANTHROPIC_AUTH_TOKEN": "sk-xxx",
    "ANTHROPIC_MODEL": "kimi-for-coding"
  }
}
```

opencode 配置（`~/.codex/config.toml`）：
```toml
[model_providers.coapi]
name = "co-api"
base_url = "http://127.0.0.1:3000/v1"
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 构建前端

```bash
cd app/static && npm install && npm run build && cd ../..
```

### 3. 启动服务

```bash
python run.py
```

访问 `http://127.0.0.1:3000`，默认账号 `admin`，密码 `Admin@1234`。

### 4. 添加渠道

进入管理面板 → 渠道管理 → 新建渠道：

1. 选择平台（DeepSeek / Kimi / Kimi Coding...）
2. 输入 API Key
3. 点击保存 → 自动同步模型

## 负载均衡策略

| 策略 | 行为 | 配置 |
|------|------|------|
| **weighted** (默认) | 按权重比例随机选择 | 模型池 mode=weighted，成员设置 weight |
| **round_robin** | 顺序轮询 | 模型池 mode=round_robin |
| **failover** | 优先级高的先尝试，失败切换下一级 | 成员设置 priority 值 |
| **sticky** | 同一 (Token+模型) 固定路由 | 模型池 mode=sticky，5 分钟 TTL |

## 请求处理流程

```
API 请求 → Token 验证 → 模型解析 → 模型池/渠道发现
  → 负载均衡排序 → Vision 过滤 → 熔断检查 → 协议转换
  → 上游请求 → 重试/故障转移 → 响应转换 → 日志记录 → 返回
```

## 项目结构

```
co-api/
├── run.py                  # 入口
├── requirements.txt
├── app/
│   ├── __init__.py         # FastAPI 应用、中间件、lifespan
│   ├── config.py           # 配置 (pydantic-settings, .env 支持)
│   ├── database.py         # SQLite 异步引擎、自动迁移
│   ├── models.py           # ORM: Channel, Token, ModelPool, Stats, Health
│   ├── api/
│   │   └── routes.py       # 全部 API 路由 (2400+ 行)
│   ├── core/
│   │   ├── cache.py        # 渠道/令牌/模型池 30s 内存缓存
│   │   ├── health.py       # 熔断器、健康检查、状态持久化
│   │   ├── http_pool.py    # httpx 连接池 (HTTP/2, 200 并发)
│   │   ├── log_writer.py   # 异步批量日志写入 + 统计聚合
│   │   └── security.py     # JWT + bcrypt
│   ├── relay/
│   │   └── converter.py    # OpenAI↔Anthropic↔Gemini↔Bedrock 转换
│   └── static/             # Vue3 前端 (Vite + TypeScript + ECharts)
│       └── src/
│           ├── views/      # 8 个页面组件
│           ├── components/ # 11 个通用组件
│           └── api/        # Axios 封装
└── data/                   # SQLite 数据 (自动创建)
```

## 配置项 (.env)

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `primary_max_tries` | `5` | 主源渠道最大重试次数 |
| `backup_max_tries` | `2` | 备源渠道最大重试次数 |
| `read_timeout_light` | `120` | 短文本读取超时 (秒) |
| `read_timeout_heavy` | `300` | 长文本读取超时 (秒) |
| `channel_cache_ttl` | `30` | 渠道缓存过期时间 (秒) |
| `context_overflow_policy` | `route_only` | 超长上下文策略 |

## 平台预设

| 预设 | Base URL | 模型 ID |
|------|----------|---------|
| DeepSeek | `https://api.deepseek.com` | `deepseek-chat`, `deepseek-reasoner` |
| Kimi | `https://api.moonshot.cn` | `moonshot-v1-8k` 等 |
| Kimi Coding | `https://api.kimi.com/coding/v1` | `kimi-for-coding` |
| 智谱 | `https://open.bigmodel.cn/api/paas/v4` | `glm-4`, `glm-4-flash` |
| 通义千问 | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-plus` 等 |
| SiliconFlow | `https://api.siliconflow.cn` | `DeepSeek-V3`, `DeepSeek-R1` |

## License

MIT © CakeCi
