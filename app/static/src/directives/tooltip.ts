import type { DirectiveBinding, VNode } from 'vue'

interface TooltipOptions {
  content: string
  placement?: 'top' | 'bottom' | 'left' | 'right'
  delay?: number
  duration?: number
}

function createTooltipElement(content: string, placement: string): HTMLElement {
  const tooltip = document.createElement('div')
  tooltip.className = `tooltip-directive tooltip-${placement}`
  tooltip.textContent = content
  tooltip.style.cssText = `
    position: fixed;
    padding: 6px 12px;
    background: var(--bg-tertiary, #111811);
    border: 1px solid var(--border-secondary, rgba(0, 255, 65, 0.15));
    border-radius: var(--radius-sm, 4px);
    color: var(--text-secondary, #888);
    font-size: 12px;
    white-space: nowrap;
    z-index: 9999;
    pointer-events: none;
    opacity: 0;
    transition: opacity 0.2s ease, transform 0.2s ease;
    transform: translateY(4px);
    font-family: var(--font-mono, 'Courier New', monospace);
  `
  return tooltip
}

function positionTooltip(
  tooltip: HTMLElement,
  target: HTMLElement,
  placement: string
): void {
  const targetRect = target.getBoundingClientRect()
  const tooltipRect = tooltip.getBoundingClientRect()
  
  let top = 0
  let left = 0
  
  switch (placement) {
    case 'top':
      top = targetRect.top - tooltipRect.height - 8
      left = targetRect.left + (targetRect.width - tooltipRect.width) / 2
      break
    case 'bottom':
      top = targetRect.bottom + 8
      left = targetRect.left + (targetRect.width - tooltipRect.width) / 2
      break
    case 'left':
      top = targetRect.top + (targetRect.height - tooltipRect.height) / 2
      left = targetRect.left - tooltipRect.width - 8
      break
    case 'right':
      top = targetRect.top + (targetRect.height - tooltipRect.height) / 2
      left = targetRect.right + 8
      break
  }
  
  // Boundary check
  const padding = 8
  top = Math.max(padding, Math.min(top, window.innerHeight - tooltipRect.height - padding))
  left = Math.max(padding, Math.min(left, window.innerWidth - tooltipRect.width - padding))
  
  tooltip.style.top = `${top}px`
  tooltip.style.left = `${left}px`
}

export const vTooltip = {
  mounted(el: HTMLElement, binding: DirectiveBinding<string | TooltipOptions>) {
    const options: TooltipOptions = typeof binding.value === 'string'
      ? { content: binding.value, placement: 'top', delay: 200 }
      : { placement: 'top', delay: 200, ...binding.value }
    
    let tooltip: HTMLElement | null = null
    let showTimeout: ReturnType<typeof setTimeout> | null = null
    
    const show = () => {
      if (showTimeout) clearTimeout(showTimeout)
      
      showTimeout = setTimeout(() => {
        if (!tooltip) {
          tooltip = createTooltipElement(options.content, options.placement!)
          document.body.appendChild(tooltip)
          
          // Force reflow
          tooltip.offsetHeight
          
          positionTooltip(tooltip, el, options.placement!)
          
          tooltip.style.opacity = '1'
          tooltip.style.transform = 'translateY(0)'
        }
      }, options.delay)
    }
    
    const hide = () => {
      if (showTimeout) {
        clearTimeout(showTimeout)
        showTimeout = null
      }
      
      if (tooltip) {
        tooltip.style.opacity = '0'
        tooltip.style.transform = 'translateY(4px)'
        
        setTimeout(() => {
          if (tooltip) {
            document.body.removeChild(tooltip)
            tooltip = null
          }
        }, 200)
      }
    }
    
    el._tooltip = { show, hide }
    
    el.addEventListener('mouseenter', show)
    el.addEventListener('mouseleave', hide)
    el.addEventListener('focus', show)
    el.addEventListener('blur', hide)
  },
  
  updated(el: HTMLElement, binding: DirectiveBinding<string | TooltipOptions>) {
    const options: TooltipOptions = typeof binding.value === 'string'
      ? { content: binding.value, placement: 'top', delay: 200 }
      : { placement: 'top', delay: 200, ...binding.value }
    
    if (el._tooltip) {
      el._tooltip.show = () => {
        // Update content if tooltip is visible
        const tooltip = document.querySelector('.tooltip-directive') as HTMLElement
        if (tooltip) {
          tooltip.textContent = options.content
        }
      }
    }
  },
  
  unmounted(el: HTMLElement) {
    if (el._tooltip) {
      el.removeEventListener('mouseenter', el._tooltip.show)
      el.removeEventListener('mouseleave', el._tooltip.hide)
      el.removeEventListener('focus', el._tooltip.show)
      el.removeEventListener('blur', el._tooltip.hide)
      
      // Remove visible tooltip
      const tooltip = document.querySelector('.tooltip-directive')
      if (tooltip && tooltip.parentNode) {
        tooltip.parentNode.removeChild(tooltip)
      }
      
      delete el._tooltip
    }
  }
}

// Type augmentation
declare global {
  interface HTMLElement {
    _tooltip?: {
      show: () => void
      hide: () => void
    }
  }
}
