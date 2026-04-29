export interface Channel {
  id: number
  name: string
  base_url: string
  api_key: string
  has_api_key: boolean
  models: string[]
  api_type: string
  status: number
  reasoning_levels?: string
  created_at?: string
}

export interface Token {
  id: number
  name: string
  key: string
  status: number
  created_at?: string
}

export interface ModelPool {
  id: number
  name: string
  description: string
  status: number
  member_count: number
  created_at?: string
}

export interface PoolMember {
  id: number
  pool_id: number
  channel_id: number
  channel_name: string
  alias: string
  weight: number
  priority: number
  status: number
}

export interface RequestLog {
  id: number
  token_id: number
  token_name: string
  channel_id: number
  channel_name: string
  model: string
  upstream_model: string
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
  estimated_prompt_tokens: number
  estimated_completion_tokens: number
  duration_ms: number
  first_token_ms: number
  is_stream: number
  status: number
  error_type: string | null
  error_msg: string | null
  retry_count: number
  fallback_used: number
  request_body: string | null
  response_body: string | null
  created_at: string
  has_detail: boolean
}

export interface DashboardStats {
  total_requests: number
  today_requests: number
  success_requests: number
  failed_requests: number
  failure_rate: number
  total_tokens: number
  prompt_tokens: number
  completion_tokens: number
  success_tokens: number
  success_prompt_tokens: number
  success_completion_tokens: number
  estimated_tokens: number
  estimated_prompt_tokens: number
  estimated_completion_tokens: number
  failed_estimated_tokens: number
  failed_estimated_prompt_tokens: number
  failed_estimated_completion_tokens: number
  active_channels: number
  total_api_keys: number
  trend: { date: string; count: number }[]
  model_distribution: { model: string; count: number }[]
}

export interface HealthStatus {
  channel_id: number
  consecutive_failures: number
  total_requests: number
  success_count: number
  failure_count: number
  last_request_time: string | null
  last_error: string | null
  circuit_open: boolean
  success_rate: number
}

export interface BatchAction {
  key: string
  label: string
  variant?: 'default' | 'danger'
}
