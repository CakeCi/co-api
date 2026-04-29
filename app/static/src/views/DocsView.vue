<template>
  <TerminalLayout>
    <div class="fade-in max-w-5xl">
      <div class="flex justify-between items-center mb-6">
        <h2 class="text-xl font-bold glow-text">平台文档</h2>
        <div class="flex gap-2">
          <button
            v-for="tab in tabs"
            :key="tab.key"
            class="tab-btn"
            :class="{ active: activeTab === tab.key }"
            @click="activeTab = tab.key"
          >
            {{ tab.label }}
          </button>
        </div>
      </div>

      <!-- ========================
           负载均衡执行文档
           ======================== -->
      <div v-if="activeTab === 'lb'" class="space-y-6">

        <!-- Overview -->
        <section class="content-card">
          <h3 class="text-lg font-bold text-green-400 mb-4">负载均衡概述</h3>
          <p class="text-sm opacity-80 leading-relaxed">
            co-api 实现了多级负载均衡与故障转移机制。当客户端发起 API 请求时，
            系统通过模型名匹配模型池或渠道，根据配置的负载均衡策略选择合适的渠道，
            并在请求失败时自动重试和故障转移。
          </p>
        </section>

        <!-- Architecture Flow -->
        <section class="content-card">
          <h3 class="text-lg font-bold text-green-400 mb-4">请求流转架构</h3>
          <pre class="text-xs font-mono whitespace-pre overflow-x-auto glow-bg">
<span class="text-green-400">客户端请求</span>
    |
    v
<span class="text-green-400">1. API 认证层</span>
    |--- 验证 Bearer Token (sk-xxxx)
    |--- 查询 Token 状态 (status=1)
    |
    v
<span class="text-green-400">2. 模型解析层</span>
    |--- 提取请求中的 model 参数
    |--- 上下文溢出检测 & 自动压缩 (auto_compact)
    |--- 图片能力检测 (vision)
    |
    v
<span class="text-green-400">3. 渠道发现层</span>
    |--- 优先查找模型池 (model_pools + pool_members)
    |--- 模型池不存在时，查找直接匹配的渠道 (channels.models)
    |--- 按 priority 分组，组内按 weight 排序
    |
    v
<span class="text-green-400">4. 负载均衡层</span>
    |--- 根据 pool.mode 应用策略:
    |    · weighted:      加权随机排序
    |    · round_robin:   轮询偏移
    |    · sticky:        会话粘性 (Token+模型)
    |    · failover:      保持优先级排序
    |--- 过滤不可用渠道 (circuit_open / soft_cooldown)
    |--- 过滤不支持 vision 的渠道 (需要图片时)
    |
    v
<span class="text-green-400">5. 请求执行层</span>
    |--- 协议转换 (OpenAI ↔ Anthropic ↔ Gemini ↔ Bedrock)
    |--- 按优先级分组迭代: 主源 primary + 备源 backup
    |--- 每组内按顺序尝试渠道
    |--- 每个渠道内重试 max_tries 次
    |    primary_max_tries: {{ primaryMaxTries }} 次
    |    backup_max_tries:  {{ backupMaxTries }} 次
    |
    v
<span class="text-green-400">6. 健康监控层</span>
    |--- 记录每次请求的成功/失败
    |--- 连续失败达到阈值触发熔断 (circuit breaker)
    |--- 大请求超时触发软冷却 (soft cooldown)
    |--- 熔断/冷却期间自动跳过对应渠道
    |--- 重试预算内重置熔断器 (避免全局熔断干扰主源重试)
    |
    v
<span class="text-green-400">7. 响应返回层</span>
    |--- 非流式: 直接返回 JSON
    |--- 流式: 构建 SSE 流、延迟人工分块
    |--- 协议反向转换 (Anthropic→OpenAI / OpenAI→Anthropic)
    |--- 提取 usage tokens、首 Token 延迟
    |
    v
<span class="text-green-400">8. 日志记录层</span>
    |--- 写入 request_logs 表
    |--- 聚合更新 stats_* 统计表
    |--- 超过阈值清理旧日志 body 字段
          </pre>
        </section>

        <!-- Load Balancing Strategies -->
        <section class="content-card">
          <h3 class="text-lg font-bold text-green-400 mb-4">四种负载均衡策略</h3>

          <div class="space-y-4">
            <!-- Weighted -->
            <div class="strategy-card">
              <div class="flex items-center gap-2 mb-2">
                <span class="strategy-icon bg-green-900/30 text-green-400">W</span>
                <h4 class="font-bold">加权随机 (weighted) - 默认</h4>
              </div>
              <div class="text-sm opacity-80 space-y-1">
                <p>每个渠道配置 <code class="inline-code">weight</code> 权重值（默认 100），
                每次请求按权重比例随机选择一个渠道。</p>
                <p><span class="text-green-400">配置：</span>
                模型池 <code class="inline-code">mode = "weighted"</code>，
                成员设置不同的 <code class="inline-code">weight</code> 值即可。</p>
              </div>
            </div>

            <!-- Round Robin -->
            <div class="strategy-card">
              <div class="flex items-center gap-2 mb-2">
                <span class="strategy-icon bg-green-900/30 text-green-400">R</span>
                <h4 class="font-bold">轮询 (round_robin)</h4>
              </div>
              <div class="text-sm opacity-80 space-y-1">
                <p>每个请求按顺序轮流选择渠道，所有渠道机会均等。
                状态保存在内存中，服务重启后计数器归零。</p>
                <p><span class="text-green-400">配置：</span>
                模型池 <code class="inline-code">mode = "round_robin"</code>。</p>
              </div>
            </div>

            <!-- Failover -->
            <div class="strategy-card">
              <div class="flex items-center gap-2 mb-2">
                <span class="strategy-icon bg-green-900/30 text-green-400">F</span>
                <h4 class="font-bold">故障转移 (failover)</h4>
              </div>
              <div class="text-sm opacity-80 space-y-1">
                <p>按优先级分组，优先级高的渠道优先使用。只有高优先级渠道全部失败后，
                才尝试下一级优先级的备选渠道。</p>
                <p><span class="text-green-400">配置：</span>
                模型池 <code class="inline-code">mode = "failover"</code>，
                成员设置不同 <code class="inline-code">priority</code> 值。</p>
              </div>
            </div>

            <!-- Sticky -->
            <div class="strategy-card">
              <div class="flex items-center gap-2 mb-2">
                <span class="strategy-icon bg-green-900/30 text-green-400">S</span>
                <h4 class="font-bold">会话粘性 (sticky)</h4>
              </div>
              <div class="text-sm opacity-80 space-y-1">
                <p>同一组 (Token + 模型) 的所有请求固定路由到首次成功的渠道，
                粘性 TTL 为 <code class="inline-code">{{ stickyTtl }} 秒</code>。</p>
                <p><span class="text-green-400">配置：</span>
                模型池 <code class="inline-code">mode = "sticky"</code>。</p>
              </div>
            </div>
          </div>
        </section>

        <!-- Priority & Retry -->
        <section class="content-card">
          <h3 class="text-lg font-bold text-green-400 mb-4">优先级与重试机制</h3>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            <div>
              <h4 class="font-bold mb-2 text-green-400">优先级分组</h4>
              <ul class="list-disc list-inside opacity-80 space-y-1">
                <li>priority 值越小越优先（1 最高优先级）</li>
                <li>同优先级组内渠道按权重或轮询排序</li>
                <li>主源 (priority=1): 最多重试 {{ primaryMaxTries }} 次</li>
                <li>备源 (priority>=2): 最多重试 {{ backupMaxTries }} 次</li>
              </ul>
            </div>
            <div>
              <h4 class="font-bold mb-2 text-green-400">重试间隔</h4>
              <ul class="list-disc list-inside opacity-80 space-y-1">
                <li>主源延迟: {{ primaryDelays }}</li>
                <li>备源延迟: {{ backupDelays }}</li>
                <li>讯飞非流式模式: 自动切换为非流式请求</li>
                <li>超长上下文: 跳过讯飞渠道，重试其他</li>
              </ul>
            </div>
          </div>
        </section>

        <!-- Health & Circuit Breaker -->
        <section class="content-card">
          <h3 class="text-lg font-bold text-green-400 mb-4">健康监控与熔断机制</h3>
          <div class="overflow-x-auto">
            <table class="w-full text-sm">
              <thead><tr>
                <th class="text-left p-2">机制</th>
                <th class="text-left p-2">触发条件</th>
                <th class="text-left p-2">效果</th>
              </tr></thead>
              <tbody>
                <tr>
                  <td class="font-bold text-green-400">熔断器 (Circuit Breaker)</td>
                  <td>连续失败达到阈值 (<code class="inline-code">AUTO_DISABLE_THRESHOLD</code>)</td>
                  <td>该渠道被标记为不可用，请求跳过</td>
                </tr>
                <tr>
                  <td class="font-bold text-green-400">软冷却 (Soft Cooldown)</td>
                  <td>大请求超时 (ReadTimeout + estimated_tokens >= 阈值)</td>
                  <td>该渠道短暂冷却，大请求跳过</td>
                </tr>
                <tr>
                  <td class="font-bold text-green-400">自动恢复</td>
                  <td>重试预算内主动重置熔断器</td>
                  <td>主源 5 次重试预算内不会被全局熔断打断</td>
                </tr>
                <tr>
                  <td class="font-bold text-green-400">健康重置</td>
                  <td>手动调用 <code class="inline-code">POST /api/channels/{id}/reset-health</code></td>
                  <td>清除熔断状态，自动重新启用渠道</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <!-- Vision Filter -->
        <section class="content-card">
          <h3 class="text-lg font-bold text-green-400 mb-4">图片能力自动路由</h3>
          <p class="text-sm opacity-80 mb-3">
            系统自动检测请求是否包含图片内容，并在执行前过滤不支持 vision 的渠道。
          </p>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            <div>
              <h4 class="font-bold mb-2">检测规则</h4>
              <ul class="list-disc list-inside opacity-80 space-y-1">
                <li>OpenAI 格式: messages 包含 <code class="inline-code">image_url</code> 块或 data:image 前缀</li>
                <li>Anthropic 格式: messages 包含 <code class="inline-code">image</code> 块</li>
              </ul>
            </div>
            <div>
              <h4 class="font-bold mb-2">渠道过滤</h4>
              <ul class="list-disc list-inside opacity-80 space-y-1">
                <li>中继站 (jmrai.net): 自动通过</li>
                <li>模型名含 vision/omni/gpt-4o/claude-3/gemini: 通过</li>
                <li>模型名含 deepseek/qwen-coder/llama: 拒绝</li>
                <li>无兼容渠道: 返回 400 错误</li>
              </ul>
            </div>
          </div>
        </section>

        <!-- Protocol Conversion -->
        <section class="content-card">
          <h3 class="text-lg font-bold text-green-400 mb-4">协议转换矩阵</h3>
          <div class="overflow-x-auto">
            <table class="w-full text-sm">
              <thead><tr>
                <th class="text-left p-2">客户端格式</th>
                <th class="text-left p-2">渠道类型</th>
                <th class="text-left p-2">请求转换</th>
                <th class="text-left p-2">响应转换</th>
                <th class="text-left p-2">SSE 转换</th>
              </tr></thead>
              <tbody>
                <tr>
                  <td>OpenAI</td>
                  <td>Anthropic</td>
                  <td>openai_to_anthropic_request</td>
                  <td>anthropic_to_openai_response</td>
                  <td>AnthropicSSEToOpenAIConverter</td>
                </tr>
                <tr>
                  <td>Anthropic</td>
                  <td>OpenAI</td>
                  <td>anthropic_to_openai_request</td>
                  <td>openai_to_anthropic_response</td>
                  <td>openai_sse_to_anthropic_sse</td>
                </tr>
                <tr>
                  <td>Gemini</td>
                  <td>OpenAI</td>
                  <td>gemini_to_openai_request</td>
                  <td>openai_to_gemini_response</td>
                  <td>-</td>
                </tr>
                <tr>
                  <td>Bedrock</td>
                  <td>OpenAI</td>
                  <td>bedrock_to_openai_request</td>
                  <td>openai_to_bedrock_response</td>
                  <td>-</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <!-- Configuration Reference -->
        <section class="content-card">
          <h3 class="text-lg font-bold text-green-400 mb-4">配置参考</h3>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            <div>
              <h4 class="font-bold mb-2">环境变量 (config.json)</h4>
              <ul class="list-disc list-inside opacity-80 space-y-1 text-xs font-mono">
                <li>primary_max_tries = {{ primaryMaxTries }}</li>
                <li>backup_max_tries = {{ backupMaxTries }}</li>
                <li>primary_retry_delays = "{{ primaryDelays }}"</li>
                <li>backup_retry_delays = "{{ backupDelays }}"</li>
                <li>connect_timeout = 10.0</li>
                <li>read_timeout_light = 120.0</li>
                <li>read_timeout_heavy = 600.0</li>
                <li>write_timeout = 60.0</li>
                <li>pool_timeout = 60.0</li>
              </ul>
            </div>
            <div>
              <h4 class="font-bold mb-2">数据库模型</h4>
              <ul class="list-disc list-inside opacity-80 space-y-1 text-xs font-mono">
                <li>model_pools: name, mode, status</li>
                <li>pool_members: pool_id, channel_id, alias, weight, priority</li>
                <li>channels: name, base_url, api_key, models, api_type, status, custom_headers</li>
              </ul>
            </div>
          </div>
        </section>

        <!-- Data Flow Diagram -->
        <section class="content-card">
          <h3 class="text-lg font-bold text-green-400 mb-4">数据流示意</h3>
          <pre class="text-xs font-mono whitespace-pre overflow-x-auto glow-bg">
                    ┌─────────────────────┐
                    │   Client (SDK/CLI)   │
                    │   model: "gpt-4o"    │
                    └──────────┬──────────┘
                               │ POST /v1/chat/completions
                               v
                    ┌─────────────────────┐
                    │  co-api Gateway     │
                    │  Token Auth         │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              v                                 v
   ┌──────────────────┐              ┌──────────────────┐
   │ Model Pool Match │              │ Channel Match    │
   │ pool.name=gpt-4o │              │ ch.models=gpt-4o │
   │ pool.mode=weight │              │ random.choice()  │
   └────────┬─────────┘              └────────┬─────────┘
            │                                 │
            │ candidates: [(Channel, alias,   │
            │   weight, priority), ...]       │
            │                                 │
            │  _apply_lb_strategy()           │
            │  weighted_order(group)           │
            │  filter circuit_open            │
            │  filter soft_cooldown           │
            │  filter vision capability       │
            │                                 │
            v                                 v
   ┌──────────────────────────────────────────────────┐
   │          Iterate: priorities → channels          │
   │                                                   │
   │   Priority 1 (主源): channel_A → retry x5        │
   │       ├─ success ? record + return                │
   │       ├─ fail ? record_failure → next channel      │
   │       └─ all fail ?                               │
   │                                                   │
   │   Priority 2 (备源): channel_B → retry x1        │
   │       ├─ success ? record + return                │
   │       └─ fail ? record_failure                    │
   │                                                   │
   │   all fail → 502 上游错误                          │
   └───────────────────┬──────────────────────────────┘
                       v
              ┌──────────────────┐
              │ Upstream         │
              │ OpenAI / Anthropic│
              │ Gemini / Bedrock │
              └──────────────────┘
          </pre>
        </section>
      </div>

      <!-- ========================
           技术架构 (原有内容)
           ======================== -->
      <div v-if="activeTab === 'arch'" class="space-y-6">
        <section class="content-card">
          <h3 class="text-lg font-bold text-green-400 mb-4">技术架构</h3>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            <div class="space-y-2">
              <div class="font-bold opacity-80">构建工具</div>
              <ul class="list-disc list-inside opacity-70 space-y-1">
                <li>Vite - 极速 HMR、代码分割</li>
                <li>TypeScript - 类型安全</li>
                <li>ESM 模块化</li>
              </ul>
            </div>
            <div class="space-y-2">
              <div class="font-bold opacity-80">前端框架</div>
              <ul class="list-disc list-inside opacity-70 space-y-1">
                <li>Vue3 Composition API + script setup</li>
                <li>Pinia - 状态管理</li>
                <li>vue-router (hash 模式)</li>
              </ul>
            </div>
            <div class="space-y-2">
              <div class="font-bold opacity-80">UI 组件</div>
              <ul class="list-disc list-inside opacity-70 space-y-1">
                <li>Tailwind CSS - 原子化样式</li>
                <li>自定义终端风格组件</li>
                <li>ECharts - 数据可视化</li>
              </ul>
            </div>
            <div class="space-y-2">
              <div class="font-bold opacity-80">HTTP 客户端</div>
              <ul class="list-disc list-inside opacity-70 space-y-1">
                <li>Axios + 拦截器</li>
                <li>统一错误处理</li>
                <li>Token 自动注入</li>
              </ul>
            </div>
          </div>
        </section>

        <section class="content-card">
          <h3 class="text-lg font-bold text-green-400 mb-4">项目结构</h3>
          <pre class="text-xs font-mono overflow-x-auto">{{ projectStructure }}</pre>
        </section>

        <section class="content-card">
          <h3 class="text-lg font-bold text-green-400 mb-4">组件设计</h3>
          <div class="space-y-3">
            <div v-for="comp in components" :key="comp.name" class="p-3 channel-item">
              <div class="flex justify-between items-start">
                <div class="font-bold text-green-400">{{ comp.name }}</div>
                <div class="text-xs opacity-60">{{ comp.path }}</div>
              </div>
              <p class="text-sm opacity-80 mt-1">{{ comp.desc }}</p>
              <div v-if="comp.props && comp.props.length" class="mt-2 text-xs opacity-70">
                Props: {{ comp.props.join(', ') }}
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  </TerminalLayout>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import TerminalLayout from '@/components/TerminalLayout.vue'

const activeTab = ref('lb')

const tabs = [
  { key: 'lb', label: '负载均衡' },
  { key: 'arch', label: '技术架构' }
]

// --- config values (matching backend defaults) ---
const primaryMaxTries = 5
const backupMaxTries = 1
const primaryDelays = '2.0, 3.0, 4.0, 5.0'
const backupDelays = '2.0'
const stickyTtl = 300

const projectStructure = `app/static/
├── index.html              # Vite 入口
├── package.json            # 依赖配置
├── vite.config.ts          # Vite 配置
├── tsconfig.json           # TypeScript 配置
└── src/
    ├── main.ts             # 应用入口
    ├── App.vue             # 根组件
    ├── router/             # 路由配置
    │   └── index.ts
    ├── stores/             # Pinia 状态
    │   └── auth.ts
    ├── components/         # 通用组件
    │   ├── TerminalLayout.vue
    │   ├── TerminalButton.vue
    │   ├── TerminalModal.vue
    │   ├── Toast.vue
    │   ├── DataTable.vue
    │   ├── EChart.vue
    │   ├── AnimatedNumber.vue
    │   └── HealthBadge.vue
    ├── views/              # 页面视图
    │   ├── LoginView.vue
    │   ├── DashboardView.vue
    │   ├── ChannelsView.vue
    │   ├── PoolsView.vue
    │   ├── TokensView.vue
    │   ├── LogsView.vue
    │   ├── StatsView.vue
    │   ├── ImageGenView.vue
    │   └── DocsView.vue
    ├── api/                # API 封装
    │   └── index.ts
    ├── types/              # TS 类型
    │   └── index.ts
    └── utils/              # 工具函数
        └── index.ts`

const components = [
  {
    name: 'TerminalLayout',
    path: 'components/TerminalLayout.vue',
    desc: '主布局组件，侧边栏导航 + 底部导航栏(移动端)，活跃指示器动画。',
    props: []
  },
  {
    name: 'DataTable',
    path: 'components/DataTable.vue',
    desc: '通用数据表格，支持排序、分页、批量操作、自定义列渲染。',
    props: ['data', 'columns', 'rowKey', 'batchable', 'batchActions']
  },
  {
    name: 'TerminalModal',
    path: 'components/TerminalModal.vue',
    desc: '终端风格弹窗组件，支持多种尺寸，点击遮罩关闭。',
    props: ['modelValue', 'title', 'size']
  },
  {
    name: 'TerminalButton',
    path: 'components/TerminalButton.vue',
    desc: '终端风格按钮，支持多种变体和尺寸，支持 loading 状态。',
    props: ['variant', 'size', 'disabled', 'loading']
  },
  {
    name: 'EChart',
    path: 'components/EChart.vue',
    desc: 'ECharts 封装组件，支持响应式 resize 和主题适配。',
    props: ['option']
  },
  {
    name: 'AnimatedNumber',
    path: 'components/AnimatedNumber.vue',
    desc: '数字动画组件，easeOutExpo 缓动效果。',
    props: ['value', 'duration', 'prefix', 'suffix']
  },
  {
    name: 'HealthBadge',
    path: 'components/HealthBadge.vue',
    desc: '渠道健康状态徽章，根据成功率显示不同颜色。',
    props: ['health']
  }
]
</script>

<style scoped>
.content-card {
  background: rgba(0, 15, 5, 0.5);
  border: 1px solid rgba(0, 255, 65, 0.1);
  border-radius: 12px;
  padding: 16px;
}

.tab-btn {
  padding: 6px 16px;
  border-radius: 8px;
  background: rgba(0, 20, 5, 0.6);
  border: 1px solid rgba(0, 255, 65, 0.12);
  color: rgba(0, 255, 65, 0.6);
  font-family: inherit;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.tab-btn:hover {
  border-color: rgba(0, 255, 65, 0.25);
  color: rgba(0, 255, 65, 0.8);
}

.tab-btn.active {
  background: rgba(0, 255, 65, 0.1);
  border-color: rgba(0, 255, 65, 0.35);
  color: #00ff41;
}

.strategy-card {
  background: rgba(0, 20, 5, 0.4);
  border: 1px solid rgba(0, 255, 65, 0.08);
  border-radius: 10px;
  padding: 14px;
}

.strategy-icon {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 12px;
  flex-shrink: 0;
}

.inline-code {
  background: rgba(0, 255, 65, 0.1);
  padding: 1px 6px;
  border-radius: 4px;
  font-family: monospace;
  font-size: 12px;
}

.glow-bg {
  background: rgba(0, 10, 3, 0.5);
  padding: 12px 16px;
  border-radius: 8px;
}

.channel-item {
  border: 1px solid rgba(0, 255, 65, 0.1);
  border-radius: 8px;
}

table th,
table td {
  border: 1px solid rgba(0, 255, 65, 0.15);
  padding: 8px;
}

table th {
  background: rgba(0, 255, 65, 0.08);
}

.glow-text {
  color: #00ff41;
  text-shadow: 0 0 6px rgba(0, 255, 65, 0.3);
}
</style>
