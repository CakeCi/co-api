# OpenCode 接入 co-api 配置提示词

请将 OpenCode 配置为使用 co-api 作为 AI 模型提供商。

## 配置步骤

### 1. 找到 opencode.json 配置文件

文件路径：
- Windows: `%USERPROFILE%\.config\opencode\opencode.json`
- macOS/Linux: `~/.config/opencode/opencode.json`

### 2. 在 `provider` 中添加 co-api 配置

```json
"co-api": {
  "npm": "@ai-sdk/openai-compatible",
  "name": "co-api Proxy",
  "options": {
    "baseURL": "http://127.0.0.1:3000/v1",
    "apiKey": "sk-Tb_8QSlJmLS3WdiCTKnZ4kyrcQQ6eYcuIZKGU46LMCo",
    "setCacheKey": true,
    "timeout": 120000,
    "chunkTimeout": 30000
  },
  "models": {
    "glm5.1": {
      "name": "glm5.1 (Pool: jmr/glm-5.1 + xunfei/astron-code-latest)",
      "limit": { "context": 256000, "output": 32768 },
      "variants": { "low": {}, "medium": {}, "high": {} }
    },
    "astron-code-latest": {
      "name": "xunfei/astron-code-latest",
      "limit": { "context": 92160, "output": 32768 },
      "variants": { "low": {}, "medium": {}, "high": {} }
    },
    "deepseek-v3.2": {
      "name": "jmr/deepseek-v3.2",
      "limit": { "context": 65536, "output": 32768 },
      "variants": { "low": {}, "medium": {}, "high": {} }
    },
    "doubao-seed-2.0-code": {
      "name": "jmr/doubao-seed-2.0-code",
      "limit": { "context": 131072, "output": 32768 },
      "variants": { "low": {}, "medium": {}, "high": {} }
    },
    "doubao-seed-2.0-lite": {
      "name": "jmr/doubao-seed-2.0-lite",
      "limit": { "context": 131072, "output": 32768 },
      "variants": { "low": {}, "medium": {}, "high": {} }
    },
    "doubao-seed-2.0-pro": {
      "name": "jmr/doubao-seed-2.0-pro",
      "limit": { "context": 131072, "output": 32768 },
      "variants": { "low": {}, "medium": {}, "high": {} }
    },
    "doubao-seed-code": {
      "name": "jmr/doubao-seed-code",
      "limit": { "context": 131072, "output": 32768 },
      "variants": { "low": {}, "medium": {}, "high": {} }
    },
    "gemini-2.5-pro": {
      "name": "jmr/gemini-2.5-pro",
      "limit": { "context": 1000000, "output": 65536 },
      "variants": { "low": {}, "medium": {}, "high": {} }
    },
    "gemini-3-pro": {
      "name": "jmr/gemini-3-pro",
      "limit": { "context": 1000000, "output": 65536 },
      "variants": { "low": {}, "medium": {}, "high": {} }
    },
    "gemini-3.1-pro": {
      "name": "jmr, jmr-openai/gemini-3.1-pro",
      "limit": { "context": 1000000, "output": 65536 },
      "variants": { "low": {}, "medium": {}, "high": {} }
    },
    "glm-4.7": {
      "name": "jmr/glm-4.7",
      "limit": { "context": 256000, "output": 32768 },
      "variants": { "low": {}, "medium": {}, "high": {} }
    },
    "glm-5.1": {
      "name": "jmr/glm-5.1",
      "limit": { "context": 256000, "output": 32768 },
      "variants": { "low": {}, "medium": {}, "high": {} }
    },
    "gpt-4o": {
      "name": "jmr-openai/gpt-4o",
      "limit": { "context": 131072, "output": 32768 },
      "variants": { "low": {}, "medium": {}, "high": {} }
    },
    "gpt-5.4": {
      "name": "公司提供/gpt-5.4",
      "limit": { "context": 1000000, "output": 32768 },
      "variants": { "low": {}, "medium": {}, "high": {}, "xhigh": {} }
    },
    "gpt-image-1": {
      "name": "jmr-openai/gpt-image-1",
      "limit": { "context": 131072, "output": 32768 },
      "variants": { "low": {}, "medium": {}, "high": {} }
    },
    "gpt-image-2": {
      "name": "jmr-openai/gpt-image-2",
      "limit": { "context": 131072, "output": 32768 },
      "variants": { "low": {}, "medium": {}, "high": {} }
    },
    "grok-3": {
      "name": "jmr/grok-3",
      "limit": { "context": 131072, "output": 32768 },
      "variants": { "low": {}, "medium": {}, "high": {} }
    },
    "grok-3-mini": {
      "name": "jmr/grok-3-mini",
      "limit": { "context": 131072, "output": 32768 },
      "variants": { "low": {}, "medium": {}, "high": {} }
    },
    "grok-3-thinking": {
      "name": "jmr/grok-3-thinking",
      "limit": { "context": 131072, "output": 32768 },
      "variants": { "low": {}, "medium": {}, "high": {} }
    },
    "grok-4": {
      "name": "jmr/grok-4",
      "limit": { "context": 131072, "output": 32768 },
      "variants": { "low": {}, "medium": {}, "high": {} }
    },
    "grok-4-heavy": {
      "name": "jmr/grok-4-heavy",
      "limit": { "context": 131072, "output": 32768 },
      "variants": { "low": {}, "medium": {}, "high": {} }
    },
    "grok-4-thinking": {
      "name": "jmr/grok-4-thinking",
      "limit": { "context": 131072, "output": 32768 },
      "variants": { "low": {}, "medium": {}, "high": {} }
    },
    "grok-4.1-expert": {
      "name": "jmr/grok-4.1-expert",
      "limit": { "context": 131072, "output": 32768 },
      "variants": { "low": {}, "medium": {}, "high": {} }
    },
    "grok-4.1-fast": {
      "name": "jmr/grok-4.1-fast",
      "limit": { "context": 131072, "output": 32768 },
      "variants": { "low": {}, "medium": {}, "high": {} }
    },
    "grok-4.1-mini": {
      "name": "jmr/grok-4.1-mini",
      "limit": { "context": 131072, "output": 32768 },
      "variants": { "low": {}, "medium": {}, "high": {} }
    },
    "grok-4.1-thinking": {
      "name": "jmr/grok-4.1-thinking",
      "limit": { "context": 131072, "output": 32768 },
      "variants": { "low": {}, "medium": {}, "high": {} }
    },
    "grok-4.20-beta": {
      "name": "jmr/grok-4.20-beta",
      "limit": { "context": 131072, "output": 32768 },
      "variants": { "low": {}, "medium": {}, "high": {} }
    },
    "kimi-for-coding": {
      "name": "Kimi Coding/kimi-for-coding",
      "limit": { "context": 262144, "output": 32768 },
      "variants": { "low": {}, "medium": {}, "high": {} }
    },
    "kimi-k2.5": {
      "name": "jmr/kimi-k2.5",
      "limit": { "context": 256000, "output": 32768 },
      "variants": { "low": {}, "medium": {}, "high": {} }
    },
    "kimi-k2.6": {
      "name": "jmr/kimi-k2.6",
      "limit": { "context": 256000, "output": 32768 },
      "variants": { "low": {}, "medium": {}, "high": {} }
    },
    "mimo-v2-flash": {
      "name": "jmr/mimo-v2-flash",
      "limit": { "context": 131072, "output": 32768 },
      "variants": { "low": {}, "medium": {}, "high": {} }
    },
    "mimo-v2-omni": {
      "name": "jmr, jmr-openai/mimo-v2-omni",
      "limit": { "context": 131072, "output": 32768 },
      "variants": { "low": {}, "medium": {}, "high": {} }
    },
    "mimo-v2-pro": {
      "name": "jmr/mimo-v2-pro",
      "limit": { "context": 131072, "output": 32768 },
      "variants": { "low": {}, "medium": {}, "high": {} }
    },
    "minimax-m2.5": {
      "name": "jmr/minimax-m2.5",
      "limit": { "context": 1000000, "output": 32768 },
      "variants": { "low": {}, "medium": {}, "high": {} }
    },
    "minimax-m2.7": {
      "name": "jmr/minimax-m2.7",
      "limit": { "context": 1000000, "output": 32768 },
      "variants": { "low": {}, "medium": {}, "high": {} }
    }
  }
}
```

### 3. 修改顶层默认模型配置

在 opencode.json 根级别添加/修改：

```json
{
  "model": "co-api/glm5.1",
  "small_model": "co-api/astron-code-latest",
  ...
}
```

### 4. 关键配置说明

| 配置项 | 值 | 说明 |
|--------|-----|------|
| npm | @ai-sdk/openai-compatible | 使用 OpenAI 兼容协议 |
| baseURL | http://127.0.0.1:3000/v1 | co-api 服务地址，**如部署到其他机器请改为对应 IP** |
| apiKey | sk-Tb_8QSlJmLS3WdiCTKnZ4kyrcQQ6eYcuIZKGU46LMCo | co-api 的 API Key，**请从目标设备的 co-api 管理后台获取** |
| timeout | 120000 | 请求超时 120 秒 |
| chunkTimeout | 30000 | SSE 分块超时 30 秒 |

### 5. 模型别名说明

- `glm5.1` - 模型池，自动负载均衡到 jmr(80%) 和 xunfei(20%)
- `gpt-5.4` - 公司内网模型，context 1M，支持 4 档推理强度 (low/medium/high/xhigh)
- 其他模型直接映射到对应渠道

### 6. 验证配置

配置完成后，运行：
```bash
opencode config validate
# 或
opencode --version
```

然后测试对话：
```bash
opencode
# 在对话中应该能看到使用 co-api/glm5.1
```

## 注意事项

1. **API Key**: 请从目标设备的 co-api 管理后台获取正确的 API Key，路径：管理后台 → API Keys → 复制 Key
2. **Base URL**: 如果 co-api 和 opencode 不在同一台机器，请将 `127.0.0.1` 改为 co-api 所在机器的 IP
3. **模型同步**: co-api 的模型列表可通过 `/api/opencode-models` 接口获取最新配置
4. **推理强度**: 大部分模型支持 low/medium/high 三档，gpt-5.4 额外支持 xhigh
5. **池子模型**: glm5.1 是负载均衡池子，会自动在 jmr 和 xunfei 之间分配请求
