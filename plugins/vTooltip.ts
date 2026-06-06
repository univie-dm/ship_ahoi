import type { App, Directive } from 'vue';
import { setupTooltip, setupTooltipFromKey, globalTooltipManager } from '~/composables/useTooltipManager';
import type { TooltipConfig } from '~/composables/useTooltipManager';

interface TooltipDirectiveBinding {
  value: string | TooltipConfig | { key: string; options?: Partial<TooltipConfig> };
  modifiers?: {
    hover?: boolean;
    click?: boolean;
    focus?: boolean;
    interactive?: boolean;
    light?: boolean;
    info?: boolean;
    warning?: boolean;
    error?: boolean;
    small?: boolean;
    large?: boolean;
    top?: boolean;
    bottom?: boolean;
    left?: boolean;
    right?: boolean;
    rich?: boolean;
  };
}

interface TooltipElement extends HTMLElement {
  _tooltipCleanup?: () => void;
  _tooltipConfig?: TooltipConfig;
}

const parseModifiers = (modifiers: any = {}): Partial<TooltipConfig> => {
  const config: Partial<TooltipConfig> = {};

  // Trigger modifiers
  if (modifiers.click) config.trigger = 'click';
  else if (modifiers.focus) config.trigger = 'focus';
  else config.trigger = 'hover'; // default

  // Theme modifiers
  if (modifiers.light) config.theme = 'light';
  else if (modifiers.info) config.theme = 'info';
  else if (modifiers.warning) config.theme = 'warning';
  else if (modifiers.error) config.theme = 'error';
  else config.theme = 'dark'; // default

  // Size modifiers
  if (modifiers.small) config.size = 'small';
  else if (modifiers.large) config.size = 'large';
  else config.size = 'medium'; // default

  // Position modifiers
  if (modifiers.top) config.position = 'top';
  else if (modifiers.bottom) config.position = 'bottom';
  else if (modifiers.left) config.position = 'left';
  else if (modifiers.right) config.position = 'right';
  else config.position = 'auto'; // default

  // Behavior modifiers
  if (modifiers.interactive) {
    config.interactive = true;
    config.showClose = true;
  }

  if (modifiers.rich) {
    config.isRichContent = true;
  }

  return config;
};

const setupTooltipForElement = (
  el: TooltipElement,
  binding: TooltipDirectiveBinding
): void => {
  // Clean up existing tooltip if any
  if (el._tooltipCleanup) {
    el._tooltipCleanup();
    el._tooltipCleanup = undefined;
  }

  if (!binding.value) return;

  const modifierConfig = parseModifiers(binding.modifiers);
  
  let cleanup: () => void;

  if (typeof binding.value === 'string') {
    // Simple string content
    cleanup = setupTooltip(el, binding.value, modifierConfig);
  } else if (typeof binding.value === 'object') {
    if ('key' in binding.value) {
      // Predefined tooltip key
      const { key, options = {} } = binding.value;
      cleanup = setupTooltipFromKey(el, key, { ...modifierConfig, ...options });
    } else {
      // Full config object
      cleanup = setupTooltip(el, { ...modifierConfig, ...binding.value });
    }
  } else {
    console.warn('v-tooltip: Invalid binding value type');
    return;
  }

  // Store cleanup function for later use
  el._tooltipCleanup = cleanup;
};

const vTooltip: Directive<TooltipElement, TooltipDirectiveBinding['value']> = {
  mounted(el: TooltipElement, binding) {
    setupTooltipForElement(el, binding as TooltipDirectiveBinding);
  },

  updated(el: TooltipElement, binding) {
    // Only re-setup if the value actually changed
    if (binding.value !== binding.oldValue) {
      setupTooltipForElement(el, binding as TooltipDirectiveBinding);
    }
  },

  beforeUnmount(el: TooltipElement) {
    if (el._tooltipCleanup) {
      el._tooltipCleanup();
      el._tooltipCleanup = undefined;
    }
  },
};

// Plugin installation function
export default defineNuxtPlugin((nuxtApp) => {
  nuxtApp.vueApp.directive('tooltip', vTooltip);
});

// Export directive for manual registration if needed
export { vTooltip };

// Type declarations for better TypeScript support
declare module '@vue/runtime-core' {
  interface ComponentCustomProperties {
    $tooltip: typeof globalTooltipManager;
  }
}

// Helper functions for programmatic tooltip usage
export const showTooltip = (
  element: HTMLElement,
  content: string | TooltipConfig,
  options?: Partial<TooltipConfig>
) => {
  const config = typeof content === 'string' 
    ? { content, ...options }
    : { ...content, ...options };
  
  globalTooltipManager.show(element, config);
};

export const hideTooltip = () => {
  globalTooltipManager.hide();
};

export const showTooltipFromKey = (
  element: HTMLElement,
  tooltipKey: string,
  options?: Partial<TooltipConfig>
) => {
  const tooltipConfig = globalTooltipManager.getTooltipContent(tooltipKey);
  if (tooltipConfig) {
    globalTooltipManager.show(element, { ...tooltipConfig, ...options });
  }
};

// Export types for use in components
export type { TooltipConfig, TooltipDirectiveBinding };