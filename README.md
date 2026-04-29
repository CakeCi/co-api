# co-api

极简 AI API 网关 - 暗绿色终端风格

## 功能

- 单用户认证 (admin / Admin@1234)
- 上游 Channel 管理 (OpenAI 兼容格式)
- API Token 管理
- OpenAI 格式请求转发

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务
python run.py
```

访问 http://localhost:3000

## 默认登录

- 用户名: `admin`
- 密码: `Admin@1234`

## API 使用

```bash
curl http://localhost:3000/v1/chat/completions \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```
