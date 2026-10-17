<script setup lang="ts">
import { ref } from "vue";

defineProps<{
  title: string;
  snippet?: string;
}>();

const expanded = ref(false);

function toggle(): void {
  expanded.value = !expanded.value;
}
</script>

<template>
  <div class="source-card" :class="{ expanded }">
    <button class="source-toggle" @click="toggle">
      <span class="source-icon">{{ expanded ? "▾" : "▸" }}</span>
      <span class="source-title">{{ title }}</span>
    </button>
    <div v-if="expanded && snippet" class="source-snippet">
      {{ snippet }}
    </div>
  </div>
</template>

<style scoped>
.source-card {
  margin-top: 4px;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  overflow: hidden;
}
.source-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  padding: 4px 10px;
  border: none;
  background: #f8f9fa;
  font-size: 12px;
  color: #666;
  cursor: pointer;
  text-align: left;
}
.source-toggle:hover {
  background: #e9ecef;
}
.source-icon {
  font-size: 10px;
  flex-shrink: 0;
}
.source-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.source-snippet {
  padding: 8px 10px;
  font-size: 12px;
  color: #555;
  line-height: 1.5;
  border-top: 1px solid #e0e0e0;
  background: #fff;
  max-height: 120px;
  overflow-y: auto;
}
</style>
