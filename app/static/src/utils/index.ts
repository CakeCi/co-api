export function formatDuration(ms: number): string {
  if (ms >= 1000) return (ms / 1000).toFixed(1) + 's'
  return ms + 'ms'
}

export function formatNumber(num: number): string {
  return num.toLocaleString()
}

export function formatDateTime(dateStr: string): string {
  return new Date(dateStr.replace(' ', 'T') + '+08:00').toLocaleString('zh-CN')
}

export function maskSecret(key: string): string {
  if (!key || key.length < 8) return key
  return key.slice(0, 6) + '****' + key.slice(-4)
}
