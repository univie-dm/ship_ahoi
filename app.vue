<template>
  <div>
    <NuxtLayout name="default">
      <NuxtPage />
    </NuxtLayout>
    <Toast />
  </div>
</template>

<script setup lang="ts">
import Toast from '~/components/Toast.vue';
</script>

<style>
/* Global styles */
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  background-color: #ffffff; /* Consistent with new design */
  color: #37352f;
  line-height: 1.5;
}

/* Add more global styles or import a global CSS file here */
</style>
