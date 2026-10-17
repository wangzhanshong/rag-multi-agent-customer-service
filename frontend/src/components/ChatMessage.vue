<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { marked } from "marked";
import SourceCard from "./SourceCard.vue";
import type { ChatMessage as ChatMessageType } from "../composables/useChat";

const props = defineProps<{
  message: ChatMessageType;
}>();

const contentRef = ref<HTMLElement | null>(null);

const renderedHtml = computed(() => {
  if (props.message.role !== "assistant") return "";
  return marked.parse(props.message.content || " ", {
    breaks: true,
    gfm: true,
  }) as string;
});

const isThinking = computed(() => props.message.role === "thinking");

// Auto scroll to bottom when content updates
onMounted(() => {
  if (contentRef.value) {
    contentRef.value.scrollIntoView({ behavior: "smooth", block: "end" });
  }
});
</script>

<template>
  <div
    class="chat-message"
    :class="{
      user: message.role === 'user',
      assistant: message.role === 'assistant',
      thinking: isThinking,
    }"
  >
    <div class="message-avatar">
      {{ message.role === "user" ? "我" : "AI" }}
    </div>
    <div class="message-body">
      <!-- Thinking state -->
      <div v-if="isThinking" class="thinking-indicator">
        <span class="dot"></span>
        <span class="dot"></span>
        <span class="dot"></span>
        {{ message.content || "分析中..." }}
      </div>

      <!-- Assistant Markdown -->
      <div
        v-else-if="message.role === 'assistant'"
        ref="contentRef"
        class="markdown-body"
        v-html="renderedHtml"
      ></div>

      <!-- User plain text -->
      <div v-else class="user-text">{{ message.content }}</div>

      <!-- Streaming cursor -->
      <span
        v-if="message.isStreaming && message.role === 'assistant'"
        class="streaming-cursor"
        >|</span
      >

      <!-- Sources -->
      <div v-if="message.sources.length > 0" class="sources-section">
        <div class="sources-label">引用来源:</div>
        <SourceCard
          v-for="(src, idx) in message.sources"
          :key="idx"
          :title="src.title"
          :snippet="src.snippet"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.chat-message {
  display: flex;
  gap: 12px;
  padding: 12px 16px;
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.chat-message.user {
  flex-direction: row-reverse;
}

.message-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
  flex-shrink: 0;
}

.chat-message.user .message-avatar {
  background: #4f46e5;
  color: #fff;
}

.chat-message.assistant .message-avatar,
.chat-message.thinking .message-avatar {
  background: #10b981;
  color: #fff;
}

.message-body {
  max-width: 75%;
  min-width: 0;
}

.chat-message.user .message-body {
  text-align: right;
}

.user-text {
  background: #4f46e5;
  color: #fff;
  padding: 10px 14px;
  border-radius: 14px 14px 4px 14px;
  display: inline-block;
  white-space: pre-wrap;
  word-break: break-word;
  text-align: left;
}

/* Markdown rendering */
.markdown-body {
  background: #fff;
  padding: 12px 16px;
  border-radius: 8px;
  border: 1px solid #e0e0e0;
  line-height: 1.7;
  font-size: 14px;
  word-break: break-word;
}

.markdown-body :deep(p) { margin: 0 0 8px; }
.markdown-body :deep(p:last-child) { margin-bottom: 0; }
.markdown-body :deep(ul), .markdown-body :deep(ol) { padding-left: 20px; margin: 4px 0; }
.markdown-body :deep(li) { margin: 2px 0; }
.markdown-body :deep(strong) { font-weight: 600; color: #333; }
.markdown-body :deep(code) {
  background: #f5f5f5;
  padding: 2px 5px;
  border-radius: 3px;
  font-size: 0.9em;
}
.markdown-body :deep(pre) {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 12px;
  border-radius: 6px;
  overflow-x: auto;
  margin: 8px 0;
}
.markdown-body :deep(pre code) {
  background: transparent;
  padding: 0;
  color: inherit;
}
.markdown-body :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 8px 0;
}
.markdown-body :deep(th), .markdown-body :deep(td) {
  border: 1px solid #ddd;
  padding: 6px 10px;
  text-align: left;
}
.markdown-body :deep(th) {
  background: #f8f9fa;
  font-weight: 600;
}

/* Thinking */
.thinking-indicator {
  display: flex;
  align-items: center;
  gap: 4px;
  color: #888;
  font-size: 13px;
  padding: 8px 0;
}

.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #aaa;
  animation: bounce 1.4s infinite ease-in-out both;
}
.dot:nth-child(1) { animation-delay: -0.32s; }
.dot:nth-child(2) { animation-delay: -0.16s; }
.dot:nth-child(3) { animation-delay: 0s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}

/* Streaming cursor */
.streaming-cursor {
  display: inline;
  color: #4f46e5;
  animation: blink 1s step-end infinite;
  font-weight: bold;
}
@keyframes blink {
  50% { opacity: 0; }
}

/* Sources */
.sources-section {
  margin-top: 8px;
}
.sources-label {
  font-size: 12px;
  color: #999;
  margin-bottom: 4px;
}
</style>
