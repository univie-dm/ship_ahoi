import { ref, reactive, nextTick, onUnmounted, getCurrentInstance } from 'vue';
import type { Component } from 'vue';

export interface TooltipConfig {
  content: string;
  title?: string;
  position?: 'top' | 'bottom' | 'left' | 'right' | 'auto';
  theme?: 'dark' | 'light' | 'info' | 'warning' | 'error';
  size?: 'small' | 'medium' | 'large';
  offset?: number;
  showArrow?: boolean;
  interactive?: boolean;
  showClose?: boolean;
  maxWidth?: number;
  delay?: number;
  isRichContent?: boolean;
  zIndex?: number;
  trigger?: 'hover' | 'click' | 'focus' | 'manual';
  hideOnClick?: boolean;
  hideDelay?: number;
}

export interface TooltipState {
  visible: boolean;
  targetElement: HTMLElement | null;
  config: TooltipConfig;
  timeoutId: number | null;
  hideTimeoutId: number | null;
}

const defaultConfig: TooltipConfig = {
  content: '',
  position: 'auto',
  theme: 'dark',
  size: 'medium',
  offset: 8,
  showArrow: true,
  interactive: false,
  showClose: false,
  maxWidth: 300,
  delay: 0,
  isRichContent: false,
  zIndex: 9999,
  trigger: 'hover',
  hideOnClick: true,
  hideDelay: 0,
};

// Global tooltip state
const globalTooltipState = reactive<TooltipState>({
  visible: false,
  targetElement: null,
  config: { ...defaultConfig },
  timeoutId: null,
  hideTimeoutId: null,
});

// Keyboard navigation state
const keyboardFocusTracker = ref<HTMLElement | null>(null);

export const useTooltipManager = () => {
  // Local tooltip state for component-level tooltips
  const localTooltipState = reactive<TooltipState>({
    visible: false,
    targetElement: null,
    config: { ...defaultConfig },
    timeoutId: null,
    hideTimeoutId: null,
  });

  const show = (
    targetElement: HTMLElement,
    config: Partial<TooltipConfig> = {},
    useGlobal = true
  ) => {
    const state = useGlobal ? globalTooltipState : localTooltipState;
    const finalConfig = { ...defaultConfig, ...config };

    // Clear any existing timeouts
    clearTimeouts(state);

    // Hide any existing tooltip first
    if (state.visible) {
      hide(useGlobal);
    }

    const showTooltip = () => {
      state.targetElement = targetElement;
      state.config = finalConfig;
      state.visible = true;

      // Add ARIA attributes
      if (!targetElement.hasAttribute('aria-describedby')) {
        const tooltipId = `tooltip-${Math.random().toString(36).substr(2, 9)}`;
        targetElement.setAttribute('aria-describedby', tooltipId);
      }

      // Track for keyboard navigation
      if (finalConfig.interactive) {
        keyboardFocusTracker.value = targetElement;
      }
    };

    if (finalConfig.delay && finalConfig.delay > 0) {
      state.timeoutId = window.setTimeout(showTooltip, finalConfig.delay);
    } else {
      showTooltip();
    }
  };

  const hide = (useGlobal = true, force = false) => {
    const state = useGlobal ? globalTooltipState : localTooltipState;

    // Clear any existing timeouts
    clearTimeouts(state);

    const hideTooltip = () => {
      state.visible = false;
      
      // Clean up ARIA attributes
      if (state.targetElement) {
        state.targetElement.removeAttribute('aria-describedby');
      }
      
      // Reset state
      state.targetElement = null;
      state.config = { ...defaultConfig };
      
      // Clear keyboard focus tracker
      if (keyboardFocusTracker.value === state.targetElement) {
        keyboardFocusTracker.value = null;
      }
    };

    if (!force && state.config.hideDelay && state.config.hideDelay > 0) {
      state.hideTimeoutId = window.setTimeout(hideTooltip, state.config.hideDelay);
    } else {
      hideTooltip();
    }
  };

  const toggle = (
    targetElement: HTMLElement,
    config: Partial<TooltipConfig> = {},
    useGlobal = true
  ) => {
    const state = useGlobal ? globalTooltipState : localTooltipState;
    if (state.visible && state.targetElement === targetElement) {
      hide(useGlobal);
    } else {
      show(targetElement, config, useGlobal);
    }
  };

  const update = (config: Partial<TooltipConfig>, useGlobal = true) => {
    const state = useGlobal ? globalTooltipState : localTooltipState;
    if (state.visible) {
      state.config = { ...state.config, ...config };
    }
  };

  const clearTimeouts = (state: TooltipState) => {
    if (state.timeoutId) {
      window.clearTimeout(state.timeoutId);
      state.timeoutId = null;
    }
    if (state.hideTimeoutId) {
      window.clearTimeout(state.hideTimeoutId);
      state.hideTimeoutId = null;
    }
  };

  // Event handlers for different trigger types
  const createEventHandlers = (
    element: HTMLElement,
    config: Partial<TooltipConfig> = {},
    useGlobal = true
  ) => {
    const finalConfig = { ...defaultConfig, ...config };
    const state = useGlobal ? globalTooltipState : localTooltipState;

    const handleMouseEnter = () => {
      if (finalConfig.trigger === 'hover') {
        show(element, config, useGlobal);
      }
    };

    const handleMouseLeave = () => {
      if (finalConfig.trigger === 'hover' && !finalConfig.interactive) {
        hide(useGlobal);
      }
    };

    const handleClick = (event: Event) => {
      if (finalConfig.trigger === 'click') {
        event.preventDefault();
        event.stopPropagation();
        toggle(element, config, useGlobal);
      } else if (finalConfig.hideOnClick && state.visible) {
        hide(useGlobal);
      }
    };

    const handleFocus = () => {
      if (finalConfig.trigger === 'focus') {
        show(element, config, useGlobal);
      }
    };

    const handleBlur = () => {
      if (finalConfig.trigger === 'focus') {
        hide(useGlobal);
      }
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      if (state.visible && state.targetElement === element) {
        switch (event.key) {
          case 'Escape':
            event.preventDefault();
            hide(useGlobal);
            break;
          case 'Tab':
            if (!finalConfig.interactive) {
              hide(useGlobal);
            }
            break;
        }
      }
    };

    return {
      handleMouseEnter,
      handleMouseLeave,
      handleClick,
      handleFocus,
      handleBlur,
      handleKeyDown,
    };
  };

  // Attach tooltip to element
  const attachTooltip = (
    element: HTMLElement,
    config: Partial<TooltipConfig> = {},
    useGlobal = true
  ) => {
    const handlers = createEventHandlers(element, config, useGlobal);
    const finalConfig = { ...defaultConfig, ...config };

    // Add event listeners based on trigger type
    if (finalConfig.trigger === 'hover') {
      element.addEventListener('mouseenter', handlers.handleMouseEnter);
      element.addEventListener('mouseleave', handlers.handleMouseLeave);
    }

    if (finalConfig.trigger === 'click') {
      element.addEventListener('click', handlers.handleClick);
    }

    if (finalConfig.trigger === 'focus') {
      element.addEventListener('focus', handlers.handleFocus);
      element.addEventListener('blur', handlers.handleBlur);
    }

    // Always add keyboard support
    element.addEventListener('keydown', handlers.handleKeyDown);

    // Global click handler for hiding interactive tooltips
    if (finalConfig.hideOnClick) {
      document.addEventListener('click', handlers.handleClick);
    }

    // Return cleanup function
    return () => {
      element.removeEventListener('mouseenter', handlers.handleMouseEnter);
      element.removeEventListener('mouseleave', handlers.handleMouseLeave);
      element.removeEventListener('click', handlers.handleClick);
      element.removeEventListener('focus', handlers.handleFocus);
      element.removeEventListener('blur', handlers.handleBlur);
      element.removeEventListener('keydown', handlers.handleKeyDown);
      document.removeEventListener('click', handlers.handleClick);
    };
  };

  // Helper function to get tooltip content from predefined tooltips
  const getTooltipContent = (tooltipKey: string): Partial<TooltipConfig> | null => {
    // This will be populated from the useTooltips composable
    const { tooltips } = useTooltips();
    
    const keys = tooltipKey.split('.');
    let content: any = tooltips;
    
    for (const key of keys) {
      content = content?.[key];
      if (content === undefined) {
        console.warn(`Tooltip content not found for key: ${tooltipKey}`);
        return null;
      }
    }
    
    if (typeof content === 'string') {
      return { content };
    } else if (typeof content === 'object' && content.content) {
      return content;
    } else {
      console.warn(`Invalid tooltip content format for key: ${tooltipKey}`);
      return null;
    }
  };

  // Cleanup function
  const cleanup = () => {
    clearTimeouts(globalTooltipState);
    clearTimeouts(localTooltipState);
    hide(true, true);
    hide(false, true);
  };

  // Auto-cleanup on unmount (only if in component context)
  const currentInstance = getCurrentInstance();
  if (currentInstance) {
    onUnmounted(() => {
      cleanup();
    });
  }

  return {
    // State
    state: localTooltipState,
    globalState: globalTooltipState,
    
    // Core methods
    show,
    hide,
    toggle,
    update,
    
    // Utility methods
    attachTooltip,
    createEventHandlers,
    getTooltipContent,
    cleanup,
    
    // Keyboard navigation
    keyboardFocusTracker,
  };
};

// Import useTooltips at the end to avoid circular dependency
import { useTooltips } from './useTooltips';

// Global instance for use across the app
export const globalTooltipManager = useTooltipManager();

// Helper function for quick tooltip setup
export const setupTooltip = (
  element: HTMLElement,
  content: string | Partial<TooltipConfig>,
  options: Partial<TooltipConfig> = {}
) => {
  const config = typeof content === 'string' 
    ? { content, ...options }
    : { ...content, ...options };
    
  return globalTooltipManager.attachTooltip(element, config);
};

// Helper function for tooltip from predefined content
export const setupTooltipFromKey = (
  element: HTMLElement,
  tooltipKey: string,
  options: Partial<TooltipConfig> = {}
) => {
  const tooltipConfig = globalTooltipManager.getTooltipContent(tooltipKey);
  if (tooltipConfig) {
    return globalTooltipManager.attachTooltip(element, { ...tooltipConfig, ...options });
  }
  return () => {}; // Return empty cleanup function if no content found
};