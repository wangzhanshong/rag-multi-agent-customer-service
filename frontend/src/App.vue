<script setup lang="ts">
import ChatView from "./views/ChatView.vue";
</script>

<template>
  <ChatView />
</template>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
    "Helvetica Neue", Arial, "Noto Sans SC", sans-serif;
  background: #f5f5f5;
  color: #333;
}

html, body, #app {
  height: 100%;
  overflow: hidden;
}
</style>
