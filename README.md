<p align="center">
  <pre>
   ___     ___      _    ___ 
  / __|___/ _ \    /_\  |_ _|
 | (__/ _ \ (_) |  / _ \  | | 
  \___\___/\___/  /_/ \_\|___|
  </pre>
</p>

<h3 align="center">企业级 LLM API 智能网关</h3>

<p align="center">
  一个端点接入所有大模型 · 自动负载均衡 · 多级故障转移 · 实时健康监控
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?logo=python" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi" alt="FastAPI">
  <img src="https://img.shields.io/badge/Vue-3.5+-4FC08D?logo=vue.js" alt="Vue">
  <img src="https://img.shields.io/badge/ECharts-5-AA344D" alt="ECharts">
  <img src="https://img.shields.io/badge/SQLite-3-003B57?logo=sqlite" alt="SQLite">
  <img src="https://img.shields.io/badge/HTTP/2-Enabled-blue" alt="HTTP/2">
  <img src="https://img.shields.io/badge/license-MIT-red" alt="License">
</p>

---

## 为什么选择 co-api

> 一个中间层，终结多平台 API 管理的混乱。

当你同时使用 DeepSeek、Kimi、OpenAI、Anthropic、Gemini 等多个 LLM 平台时，每个都有独立的 API Key、不同的 Base URL、不同的调用协议、不同的计费方式。co-api 将它们统一为一个标准的 **OpenAI 兼容端点**，在此之上提供：

| 能力 | 描述 |
|------|------|
| **智能路由** | 根据模型池自动发现可用渠道，按权重/轮询/粘性策略分配请求 |
| **多级容灾** | 主渠道失败自动切换备选，熔断器隔离故障节点，冷却后自动恢复 |
| **协议无感转换** | 客户端统一用 OpenAI 格式，后端自动转为 Anthropic / Gemini / Bedrock |
| **推理强度透传** | `reasoning_effort` 参数零损耗透传，自动映射为 Anthropic `thinking` |
| **视觉智能路由** | 图片请求自动过滤非 Vision 渠道，防止 API 报错 |
| **上下文压缩** | 超长对话自动摘要压缩，突破上游上下文限制 |
| **全链路审计** | 每笔请求记录完整请求/响应体、Token 用量、延迟分布、重试链路 |
| **实时监控** | 熔断状态、成功率、Token 消耗、模型排行一目了然 |

## 架构

```
                              ┌──────────────────────────┐
  OpenAI SDK                  │        co-api            │
  Claude Code  ─────────────▶ │      :3000/v1             │
  opencode                    │                          │
  Cursor                      │  ┌────────────────────┐  │      ┌─────────────┐
  Roo Code                    │  │    路由引擎         │  │      │  DeepSeek   │
  ...                         │  │                    │  │─────▶│  Kimi       │
                              │  │  加权随机 / 轮询    │  │      │  Kimi Code  │
                              │  │  故障转移 / 粘性    │  │      │  智谱 GLM   │
                              │  └────────────────────┘  │      │  通义千问   │
                              │  ┌────────────────────┐  │      │  OpenAI     │
                              │  │    协议转换引擎     │  │      │  Anthropic  │
                              │  │                    │  │      │  Gemini     │
                              │  │  OpenAI ↔ Anthropic │  │      │  SiliconFlow│
                              │  │  Gemini ↔ Bedrock   │  │      │  ...        │
                              │  └────────────────────┘  │      └─────────────┘
                              │  ┌────────────────────┐  │
                              │  │    熔断 & 健康      │  │
                              │  │  连续失败自動熔断   │  │
                              │  │  exponential backoff│  │
                              │  │  状态重启持久化     │  │
                              │  └────────────────────┘  │
                              │  ┌────────────────────┐  │
                              │  │    Admin Panel      │  │
                              │  │  8 个管理页面       │  │
                              │  │  ECharts 数据看板   │  │
                              │  │  实时统计           │  │
                              │  └────────────────────┘  │
                              └──────────────────────────┘
```

## 快速开始

```bash
# 1. 安装后端依赖
pip install -r requirements.txt

# 2. 构建前端
cd app/static && npm install && npm run build && cd ../..

# 3. 启动
python run.py
```

浏览器打开 `http://127.0.0.1:3000`，登录 `admin` / `Admin@1234`。

### 添加渠道（3 秒完成）

进入 **渠道管理 → 新建渠道**：

1. 点击平台预设卡片（DeepSeek / Kimi / Kimi Coding / 智谱 / 通义 / SiliconFlow）
2. 粘贴 API Key
3. 保存 → 自动从上游 `/v1/models` 同步全部支持模型

### 客户端接入

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://127.0.0.1:3000/v1",
    api_key="sk-your-token"
)

# 无论上游是什么平台，统一 OpenAI 格式调用
client.chat.completions.create(
    model="deepseek-chat",
    messages=[{"role": "user", "content": "你好"}]
)

# 推理模型自动启用 thinking
client.chat.completions.create(
    model="deepseek-reasoner",
    messages=[{"role": "user", "content": "写一个快排"}],
    reasoning_effort="high"
)
```

**Claude Code：**
```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "http://127.0.0.1:3000",
    "ANTHROPIC_AUTH_TOKEN": "sk-xxx",
    "ANTHROPIC_MODEL": "kimi-for-coding"
  }
}
```

**opencode / Codex：**
```toml
[model_providers.coapi]
base_url = "http://127.0.0.1:3000/v1"
```

## 负载均衡策略

| 策略 | 工作机制 | 适用场景 |
|------|----------|----------|
| **加权随机** (默认) | 按成员权重比例随机分配，权重越高分配越多 | 多渠道有不同速率限制，按配额分配 |
| **轮询** | 按顺序轮流分配，所有渠道机会均等 | 多个完全等价的渠道 |
| **故障转移** | 优先使用高优先级渠道，失败后自动切换下一级 | 有主备关系的渠道 |
| **会话粘性** | 同一组 (Token + 模型) 的请求固定路由到同一渠道，TTL 5 分钟 | 需要上下文连贯的长对话 |

## 请求处理全链路

```
  Client Request
       │
       ▼
  ┌─────────────┐
  │  Token 验证  │ ← Bearer Token / JWT
  └──────┬──────┘
         ▼
  ┌─────────────┐
  │  模型解析   │ ← 提取 model / 估算 Token 数
  │  上下文压缩  │ ← auto_compact 超长对话摘要
  └──────┬──────┘
         ▼
  ┌─────────────┐
  │  渠道发现   │ ← 模型池优先 → 直接匹配兜底
  │  Vision过滤  │ ← 图片请求自动排除非视觉渠道
  └──────┬──────┘
         ▼
  ┌─────────────┐
  │  负载均衡   │ ← weighted / round_robin / sticky / failover
  │  熔断检查   │ ← 跳过 circuit_open / soft_cooldown 渠道
  └──────┬──────┘
         ▼
  ┌─────────────┐
  │  协议转换   │ ← OpenAI ↔ Anthropic ↔ Gemini ↔ Bedrock
  │  Header 注入 │ ← 渠道自定义 Header 自动附加
  └──────┬──────┘
         ▼
  ┌─────────────┐
  │  上游请求   │ ← HTTP/2 连接池复用
  │  重试机制   │ ← 主源 5 次 → 备源 2 次，指数退避
  └──────┬──────┘
         ▼
  ┌─────────────┐
  │  健康反馈   │ ← record_success / record_failure → 熔断判定
  │  日志审计   │ ← 批量异步写入 + 多维度统计聚合
  └──────┬──────┘
         ▼
  Client Response
```

## 健康监控与熔断

```
连续失败 3 次  → circuit breaker 打开 (冷却 60s, 指数退避最高 600s)
连续失败 10 次 → 标记应当自动禁用
大请求超时     → soft_cooldown (30s), 不影响小请求
重启恢复       → 熔断状态从 SQLite 恢复, 坏渠道不会因重启复活
健康检查器     → 每 60s 自动探测, 超过冷却期自动降级恢复
```

## 平台预设

| 预设 | Base URL | 模型 | 特点 |
|------|----------|------|------|
| **DeepSeek** | `api.deepseek.com` | deepseek-chat, deepseek-reasoner | 编程推理 |
| **Kimi** | `api.moonshot.cn` | moonshot-v1 系列, kimi-k2 | 长文本 |
| **Kimi Coding** | `api.kimi.com/coding/v1` | kimi-for-coding | 会员编程专属 |
| **智谱 GLM** | `open.bigmodel.cn` | glm-4, glm-4-flash | 国产旗舰 |
| **通义千问** | `dashscope.aliyuncs.com` | qwen-plus, qwen-max | 阿里云 |
| **SiliconFlow** | `api.siliconflow.cn` | DeepSeek-V3, DeepSeek-R1 | 第三方聚合 |

支持 OpenAI / Anthropic / Gemini / Bedrock 协议的任意自定义渠道。

## 管理面板功能矩阵

| 页面 | 核心功能 |
|------|----------|
| **数据看板** | ECharts 趋势图 & 分布图、实时统计卡片、最近活动流、模型排行、渠道健康监控 |
| **渠道管理** | 卡片/列表双视图、一键开关、连接测试、批量操作、自动同步模型、导出/导入配置 |
| **模型池** | 成员管理、权重/优先级/别名配置、4 种负载均衡模式切换 |
| **API 令牌** | 创建/删除/批量管理、按令牌统计用量 |
| **请求记录** | 卡片式日志项、请求/响应体详情、重放、按模型/令牌筛选、分页 |
| **统计报表** | 日/小时/模型/渠道/Token 5 维度聚合数据 |
| **AI 生图** | GPT Image 生成/编辑、支持 base64 数据 URL |
| **平台文档** | 负载均衡架构图、协议转换矩阵、配置参考 |

## 项目技术栈

| 层 | 技术 |
|----|------|
| Web 框架 | FastAPI (异步) + Uvicorn |
| ORM | SQLAlchemy 2.0 (异步) + SQLite |
| HTTP 客户端 | httpx (HTTP/2, 连接池复用) |
| 认证 | JWT + bcrypt |
| 前端框架 | Vue 3 (Composition API, script setup) |
| 构建工具 | Vite + TypeScript |
| 状态管理 | Pinia |
| 数据可视化 | ECharts 5 |
| 样式 | Tailwind CSS 原子化 |

## 配置项

通过 `.env` 文件或环境变量覆盖：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `port` | `3000` | 服务端口 |
| `db_url` | `sqlite+aiosqlite:///./data/coapi.db` | 数据库路径 |
| `primary_max_tries` | `5` | 主源最大重试 |
| `backup_max_tries` | `2` | 备源最大重试 |
| `primary_retry_delays` | `2,3,4,5` | 主源重试间隔(秒) |
| `read_timeout_light` | `120` | 普通请求读超时(秒) |
| `read_timeout_heavy` | `300` | 大请求读超时(秒) |
| `channel_cache_ttl` | `30` | 渠道缓存(秒) |
| `auto_compact_enabled` | `false` | 启用上下文压缩 |
| `jwt_secret` | - | JWT 密钥(生产必改) |

## License

MIT © [CakeCi](https://github.com/CakeCi)
