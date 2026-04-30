# co-api 生产环境配置部署指南

请将以下渠道配置和模型池配置部署到目标设备的 co-api 系统中。

## 一、渠道配置（共4个，排除"公司提供"）

### 1. jmr (Anthropic协议)
- **名称**: jmr
- **Base URL**: `https://jmrai.net`
- **API Key**: `sk-amD0MuT1yoryKTGbTR7PzoMY6ZS...` (完整密钥请从原系统复制)
- **API类型**: anthropic
- **状态**: 启用
- **推理强度**: low, medium, high
- **模型列表**:
  - mimo-v2-pro
  - doubao-seed-2.0-code
  - kimi-k2.6
  - grok-4-thinking
  - grok-3
  - doubao-seed-2.0-pro
  - minimax-m2.5
  - kimi-k2.5
  - glm-4.7
  - grok-4.1-expert
  - grok-3-thinking
  - grok-4.20-beta
  - gemini-3.1-pro
  - deepseek-v3.2
  - grok-4.1-fast
  - glm-5.1
  - grok-4.1-thinking
  - mimo-v2-omni
  - grok-4
  - doubao-seed-code
  - mimo-v2-flash
  - gemini-3-pro
  - grok-4-heavy
  - minimax-m2.7
  - gemini-2.5-pro
  - grok-4.1-mini
  - grok-3-mini
  - doubao-seed-2.0-lite

### 2. xunfei (Anthropic协议)
- **名称**: xunfei
- **Base URL**: `https://maas-coding-api.cn-huabei-1.xf-yun.com/anthropic`
- **API Key**: `6ae70a13fe2dd37d6e7bc916948156...` (完整密钥请从原系统复制)
- **API类型**: anthropic
- **状态**: 启用
- **推理强度**: low, medium, high
- **模型列表**:
  - astron-code-latest

### 3. jmr-openai (OpenAI协议)
- **名称**: jmr-openai
- **Base URL**: `https://jmrai.net`
- **API Key**: `sk-amD0MuT1yoryKTGbTR7PzoMY6ZS...` (完整密钥请从原系统复制，与jmr相同)
- **API类型**: openai
- **状态**: 启用
- **推理强度**: low, medium, high
- **模型列表**:
  - mimo-v2-omni
  - gpt-4o
  - gemini-3.1-pro
  - gpt-image-2
  - gpt-image-1

### 4. Kimi Coding (OpenAI协议)
- **名称**: Kimi Coding
- **Base URL**: `https://api.kimi.com/coding/v1`
- **API Key**: `sk-kimi-WINVTa8egmwJRivk8GFXcX...` (完整密钥请从原系统复制)
- **API类型**: openai
- **状态**: 启用
- **推理强度**: low, medium, high
- **模型列表**:
  - kimi-for-coding

## 二、模型池配置

### GLM 5.1 高可用池 (glm5.1)
- **模式**: weighted (加权轮询)
- **状态**: 启用
- **描述**: GLM 5.1 高可用池子
- **成员配置**:
  1. **xunfei** (渠道ID: 3)
     - 别名: astron-code-latest
     - 优先级: 1
     - 权重: 80
     
  2. **jmr** (渠道ID: 1)
     - 别名: glm-5.1
     - 优先级: 2
     - 权重: 20

## 三、部署步骤

1. **登录 co-api 管理后台**
   - 访问 `http://<目标设备IP>:3000`
   - 使用管理员账号登录

2. **添加渠道**
   - 进入"渠道管理"页面
   - 按照上述配置依次添加4个渠道
   - 注意选择正确的平台预设（Anthropic或OpenAI）
   - 输入完整的 API Key
   - 保存后点击"同步模型"获取模型列表
   - 检查模型映射是否正确

3. **配置模型池**
   - 进入"模型池"页面
   - 创建新池：名称为 `glm5.1`，模式为 `weighted`
   - 添加成员：
     - xunfei (astron-code-latest)，优先级1，权重80
     - jmr (glm-5.1)，优先级2，权重20

4. **验证配置**
   - 检查所有渠道状态为"正常"
   - 测试模型池调用：`glm-5.1` 应该按权重分发到 xunfei 和 jmr
   - 验证各渠道模型列表是否正确加载

## 四、注意事项

- **密钥安全**: API Key 为敏感信息，请通过安全方式传输，不要在公共渠道明文发送
- **公司提供渠道**: ID为2的"公司提供"渠道（`http://10.1.2.15:3000/openai`，模型gpt-5.4）**不包含**在本次部署中
- **推理强度**: 所有渠道默认支持 low/medium/high，如需调整可在渠道编辑页面修改
- **权重分配**: GLM池 xunfei 承担80%流量，jmr 承担20%流量
- **Base URL**: jmr 和 jmr-openai 使用相同域名但不同协议端点（Anthropic vs OpenAI）
