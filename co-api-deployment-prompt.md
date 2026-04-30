# co-api 生产环境配置 - 完整部署提示词

请将以下配置部署到目标设备的 co-api 系统中。

## 渠道配置（共4个，排除"公司提供"渠道）

### 渠道1: jmr (Anthropic协议)
```json
{
  "name": "jmr",
  "base_url": "https://jmrai.net",
  "api_key": "sk-amD0MuT1yoryKTGbTR7PzoMY6ZSeeRbClIGJpKWCppTuM4bl",
  "api_type": "anthropic",
  "status": 1,
  "reasoning_levels": "low,medium,high",
  "models": "mimo-v2-pro,doubao-seed-2.0-code,kimi-k2.6,grok-4-thinking,grok-3,doubao-seed-2.0-pro,minimax-m2.5,kimi-k2.5,glm-4.7,grok-4.1-expert,grok-3-thinking,grok-4.20-beta,gemini-3.1-pro,deepseek-v3.2,grok-4.1-fast,glm-5.1,grok-4.1-thinking,mimo-v2-omni,grok-4,doubao-seed-code,mimo-v2-flash,gemini-3-pro,grok-4-heavy,minimax-m2.7,gemini-2.5-pro,grok-4.1-mini,grok-3-mini,doubao-seed-2.0-lite"
}
```

### 渠道2: xunfei (Anthropic协议)
```json
{
  "name": "xunfei",
  "base_url": "https://maas-coding-api.cn-huabei-1.xf-yun.com/anthropic",
  "api_key": "6ae70a13fe2dd37d6e7bc91694815690:ZGUxMTM2MzRkNTMwODUwNzllOTQ3ZjU4",
  "api_type": "anthropic",
  "status": 1,
  "reasoning_levels": "low,medium,high",
  "models": "astron-code-latest"
}
```

### 渠道3: jmr-openai (OpenAI协议)
```json
{
  "name": "jmr-openai",
  "base_url": "https://jmrai.net",
  "api_key": "sk-amD0MuT1yoryKTGbTR7PzoMY6ZSeeRbClIGJpKWCppTuM4bl",
  "api_type": "openai",
  "status": 1,
  "reasoning_levels": "low,medium,high",
  "models": "mimo-v2-omni,gpt-4o,gemini-3.1-pro,gpt-image-2,gpt-image-1"
}
```

### 渠道4: Kimi Coding (OpenAI协议)
```json
{
  "name": "Kimi Coding",
  "base_url": "https://api.kimi.com/coding/v1",
  "api_key": "sk-kimi-WINVTa8egmwJRivk8GFXcXbmcs4xGBpeWsmaif0SxfJEqJacdAbWrPj1bOGhDCrV",
  "api_type": "openai",
  "status": 1,
  "reasoning_levels": "low,medium,high",
  "models": "kimi-for-coding"
}
```

## 模型池配置

### GLM 5.1 高可用池
```json
{
  "name": "glm5.1",
  "mode": "weighted",
  "description": "GLM 5.1 高可用池子",
  "status": 1,
  "members": [
    {
      "channel_name": "xunfei",
      "alias": "astron-code-latest",
      "priority": 1,
      "weight": 80
    },
    {
      "channel_name": "jmr",
      "alias": "glm-5.1",
      "priority": 2,
      "weight": 20
    }
  ]
}
```

## 部署步骤

1. **登录 co-api 管理后台** (`http://<目标IP>:3000`)

2. **添加渠道** (按顺序添加，因为模型池成员需要引用渠道)：
   - 进入"渠道管理" → "添加渠道"
   - 依次添加上述4个渠道
   - 每个渠道选择对应的平台预设 (Anthropic或OpenAI)
   - 输入完整的 base_url 和 api_key
   - 保存后点击"同步模型"获取模型列表
   - 检查模型映射是否正确

3. **配置模型池**：
   - 进入"模型池" → "添加池子"
   - 名称: `glm5.1`
   - 模式: `weighted`
   - 描述: `GLM 5.1 高可用池子`
   - 添加成员：
     - xunfei: alias=`astron-code-latest`, priority=1, weight=80
     - jmr: alias=`glm-5.1`, priority=2, weight=20

4. **验证**：
   - 所有渠道状态应为"正常"
   - 测试 `glm-5.1` 调用，确认按权重分发到 xunfei(80%) 和 jmr(20%)

## 注意事项

- **排除渠道**: "公司提供" (base_url: `http://10.1.2.15:3000/openai`, 模型: gpt-5.4) **不包含**在本次部署中
- **API Key 安全**: 上述密钥为生产密钥，请通过安全方式传输
- **Base URL**: jmr 和 jmr-openai 使用相同域名但不同协议端点
- **权重**: GLM池中 xunfei 承担80%流量，jmr 承担20%流量
