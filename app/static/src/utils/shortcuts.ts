export interface ShortcutConfig {
  key: string
  ctrl?: boolean
  shift?: boolean
  alt?: boolean
  meta?: boolean
  handler: (event: KeyboardEvent) => void
  description?: string
  preventDefault?: boolean
  scope?: string
}

class ShortcutManager {
  private shortcuts: Map<string, ShortcutConfig> = new Map()
  private enabled: boolean = true
  private scope: string = 'global'
  
  constructor() {
    this.handleKeyDown = this.handleKeyDown.bind(this)
  }
  
  register(shortcut: ShortcutConfig): () => void {
    const id = this.generateId(shortcut)
    this.shortcuts.set(id, shortcut)
    
    return () => {
      this.shortcuts.delete(id)
    }
  }
  
  unregister(key: string, ctrl?: boolean, shift?: boolean, alt?: boolean): void {
    const id = this.generateId({ key, ctrl, shift, alt })
    this.shortcuts.delete(id)
  }
  
  enable(): void {
    this.enabled = true
  }
  
  disable(): void {
    this.enabled = false
  }
  
  setScope(scope: string): void {
    this.scope = scope
  }
  
  getShortcuts(): ShortcutConfig[] {
    return Array.from(this.shortcuts.values())
  }
  
  private generateId(shortcut: Partial<ShortcutConfig>): string {
    const parts: string[] = []
    if (shortcut.ctrl) parts.push('ctrl')
    if (shortcut.shift) parts.push('shift')
    if (shortcut.alt) parts.push('alt')
    if (shortcut.meta) parts.push('meta')
    parts.push(shortcut.key!.toLowerCase())
    return parts.join('+')
  }
  
  private handleKeyDown(event: KeyboardEvent): void {
    if (!this.enabled) return
    
    const id = this.generateId({
      key: event.key,
      ctrl: event.ctrlKey,
      shift: event.shiftKey,
      alt: event.altKey,
      meta: event.metaKey
    })
    
    const shortcut = this.shortcuts.get(id)
    if (shortcut) {
      if (shortcut.scope && shortcut.scope !== this.scope) return
      
      if (shortcut.preventDefault !== false) {
        event.preventDefault()
      }
      
      shortcut.handler(event)
    }
  }
  
  bind(): void {
    document.addEventListener('keydown', this.handleKeyDown)
  }
  
  unbind(): void {
    document.removeEventListener('keydown', this.handleKeyDown)
  }
}

// Global instance
export const shortcutManager = new ShortcutManager()
