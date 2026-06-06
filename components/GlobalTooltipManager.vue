<template>
  <TooltipComponent
    :visible="state.visible"
    :content="state.config.content"
    :title="state.config.title"
    :position="state.config.position"
    :theme="state.config.theme"
    :size="state.config.size"
    :target-element="state.targetElement"
    :offset="state.config.offset"
    :show-arrow="state.config.showArrow"
    :interactive="state.config.interactive"
    :show-close="state.config.showClose"
    :max-width="state.config.maxWidth"
    :delay="state.config.delay"
    :is-rich-content="state.config.isRichContent"
    :z-index="state.config.zIndex"
    @close="handleClose"
    @show="handleShow"
    @hide="handleHide"
  />
</template>

<script setup lang="ts">
import { globalTooltipManager } from '~/composables/useTooltipManager';
import TooltipComponent from './TooltipComponent.vue';

const { globalState: state } = globalTooltipManager;

const handleClose = () => {
  globalTooltipManager.hide(true);
};

const handleShow = () => {
  // Tooltip is now visible
};

const handleHide = () => {
  // Tooltip is now hidden
};
</script>