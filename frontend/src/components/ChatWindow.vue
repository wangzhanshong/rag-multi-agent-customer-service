<script setup lang="ts">
import { ref, nextTick } from "vue";

interface Msg {
  role: string;
  content: string;
  sources: { title: string }[];
}

const messages = ref<Msg[]>([]);
const inputText = ref("");
const isStreaming = ref(false);
const error = ref("");
const sessionId = ref("s" + Date.now().toString(36));
const sidebarOpen = ref(false);

// 对话历史（内存中）
const history = ref<{ id: string; title: string; preview: string }[]>([]);

function newChat() {
  sessionId.value = "s" + Date.now().toString(36);
  messages.value = [];
  error.value = "";
}

function selectChat(id: string) {
  // 后续可接 MySQL 对话历史，当前切换 session
  sessionId.value = id;
}

function quickSend(text: string) {
  inputText.value = text;
  send();
}

async function send() {
  const content = inputText.value.trim();
  if (!content || isStreaming.value) return;
  inputText.value = "";
  error.value = "";

  messages.value.push({ role: "user", content, sources: [] });
  const assistantMsg: Msg = { role: "assistant", content: "", sources: [] };
  messages.value.push(assistantMsg);
  isStreaming.value = true;

  // 新增对话历史条目
  const hid = sessionId.value;
  history.value.unshift({ id: hid, title: content.slice(0, 20), preview: "" });

  try {
    const resp = await fetch("http://localhost:8000/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: content, session_id: hid }),
    });

    if (!resp.ok) {
      error.value = `HTTP ${resp.status}`;
      assistantMsg.content = "[错误]";
      isStreaming.value = false;
      return;
    }

    // === SSE 流式读取 ===
    const reader = resp.body!.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let curEvent = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split(/\r?\n/);
      buffer = lines.pop() || "";

      for (const line of lines) {
        const t = line.trim();
        if (!t) { curEvent = ""; continue; }

        if (t.startsWith("event: ")) {
          curEvent = t.slice(7);
        } else if (t.startsWith("data: ")) {
          const d = t.slice(6);

          if (curEvent === "token" && d) {
            assistantMsg.content += d;
            await nextTick();
            // 更新历史预览
            const h = history.value.find(x => x.id === hid);
            if (h) h.preview = assistantMsg.content.slice(0, 40);
          } else if (curEvent === "source") {
            try {
              const p = JSON.parse(d);
              if (Array.isArray(p)) assistantMsg.sources = p;
            } catch { /* */ }
          } else if (curEvent === "error") {
            error.value = d;
            assistantMsg.content += `\n[错误] ${d}`;
          }
        }
      }
    }
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : "网络错误";
    assistantMsg.content = "[请求失败]";
  } finally {
    isStreaming.value = false;
  }
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
}
</script>

<template>
  <div class="layout">
    <!-- 侧边栏 -->
    <aside class="sidebar" :class="{ open: sidebarOpen }">
      <div class="sidebar-hd">对话记录</div>
      <button class="new-btn" @click="newChat">+ 新对话</button>
      <div class="history-list">
        <div v-if="history.length === 0" class="empty">暂无历史</div>
        <div
          v-for="h in history" :key="h.id"
          class="history-item"
          :class="{ active: h.id === sessionId }"
          @click="selectChat(h.id)"
        >
          <div class="history-title">{{ h.title }}</div>
          <div class="history-preview">{{ h.preview || '...' }}</div>
        </div>
      </div>
    </aside>

    <!-- 遮罩 -->
    <div v-if="sidebarOpen" class="overlay" @click="sidebarOpen = false"></div>

    <!-- 主区域 -->
    <main class="main">
      <button class="menu-btn" @click="sidebarOpen = !sidebarOpen">☰</button>

      <div class="chat-area">
        <!-- 错误提示 -->
        <div v-if="error" class="err">{{ error }}</div>

        <!-- 欢迎 -->
        <div v-if="messages.length === 0" class="welcome">
          <h2>笔记本智能客服</h2>
          <p>故障排查 · 保修咨询 · 服务站导航</p>
          <div class="quick">
            <button @click="quickSend('电脑开不了机怎么办')">💻 无法开机</button>
            <button @click="quickSend('电池充不上电')">🔋 电池问题</button>
            <button @click="quickSend('附近哪有维修点')">📍 服务站</button>
            <button @click="quickSend('笔记本保修多久')">📋 保修政策</button>
          </div>
        </div>

        <!-- 消息列表 -->
        <div v-for="(m, i) in messages" :key="i" class="msg-row" :class="m.role">
          <div class="bubble" :class="m.role">
            <div class="text">{{ m.content || (isStreaming && i === messages.length - 1 ? '...' : '') }}</div>
            <div v-if="m.sources.length" class="src">
              📎
              <span v-for="(s, si) in m.sources" :key="si" class="src-tag">{{ s.title }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 输入栏 -->
      <div class="input-bar">
        <input
          v-model="inputText" class="inp" placeholder="输入问题..."
          :disabled="isStreaming" @keydown="onKeydown"
        />
        <button class="btn" :disabled="!inputText.trim() || isStreaming" @click="send">
          {{ isStreaming ? '...' : '发送' }}
        </button>
      </div>
    </main>
  </div>
</template>

<style scoped>
/* Layout */
.layout { display: flex; height: 100vh; background: #f5f5f5; }
.main { flex: 1; display: flex; flex-direction: column; min-width: 0; position: relative; }
.chat-area { flex: 1; overflow-y: auto; padding: 16px 20px; }
.input-bar { display: flex; gap: 10px; padding: 12px 16px; background: #fff; border-top: 1px solid #e0e0e0; }
.inp { flex: 1; padding: 10px 14px; border: 1px solid #ddd; border-radius: 24px; font-size: 14px; outline: none; }
.inp:focus { border-color: #4f46e5; }
.btn { padding: 10px 22px; border: none; border-radius: 24px; background: #4f46e5; color: #fff; font-size: 14px; font-weight: 500; cursor: pointer; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.menu-btn { display: none; position: absolute; top: 10px; left: 10px; z-index: 10; width: 36px; height: 36px; border: none; border-radius: 50%; background: #fff; box-shadow: 0 2px 8px rgba(0,0,0,.15); font-size: 16px; cursor: pointer; }

/* Welcome */
.welcome { text-align: center; padding: 60px 20px; }
.welcome h2 { font-size: 24px; margin-bottom: 8px; }
.welcome p { color: #888; margin-bottom: 24px; }
.quick { display: flex; flex-wrap: wrap; gap: 10px; justify-content: center; }
.quick button { padding: 10px 18px; border: 1px solid #ddd; border-radius: 20px; background: #fff; font-size: 14px; cursor: pointer; transition: all .2s; }
.quick button:hover { border-color: #4f46e5; color: #4f46e5; box-shadow: 0 2px 8px rgba(79,70,229,.15); }

/* Messages */
.msg-row { margin-bottom: 16px; display: flex; }
.msg-row.user { justify-content: flex-end; }
.bubble { max-width: 80%; padding: 10px 14px; border-radius: 12px; line-height: 1.65; font-size: 14px; }
.bubble.user { background: #4f46e5; color: #fff; }
.bubble.assistant { background: #fff; border: 1px solid #e0e0e0; white-space: pre-wrap; }
.src { margin-top: 8px; font-size: 12px; color: #888; }
.src-tag { display: inline-block; margin: 2px 4px; padding: 2px 8px; background: #e8f5e9; color: #2e7d32; border-radius: 10px; font-size: 11px; }
.err { padding: 10px 16px; margin-bottom: 12px; background: #fee2e2; border: 1px solid #fca5a5; border-radius: 8px; color: #991b1b; font-size: 13px; }

/* Sidebar */
.sidebar { width: 280px; min-width: 280px; background: #fff; border-right: 1px solid #e0e0e0; display: flex; flex-direction: column; }
.sidebar-hd { padding: 16px; font-size: 16px; font-weight: 600; border-bottom: 1px solid #eee; }
.new-btn { margin: 12px; padding: 10px; border: 1px dashed #ccc; border-radius: 8px; background: #f8f9fa; cursor: pointer; font-size: 14px; color: #555; }
.new-btn:hover { background: #e9ecef; }
.history-list { flex: 1; overflow-y: auto; padding: 4px 12px; }
.empty { color: #aaa; font-size: 13px; text-align: center; padding: 24px 0; }
.history-item { padding: 10px 12px; border-radius: 8px; cursor: pointer; margin-bottom: 4px; }
.history-item:hover, .history-item.active { background: #f0f0ff; }
.history-title { font-size: 13px; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.history-preview { font-size: 12px; color: #999; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; margin-top: 2px; }
.overlay { display: none; }

@media (max-width: 768px) {
  .sidebar { position: fixed; inset: 0; width: 75%; max-width: 300px; z-index: 10; transform: translateX(-100%); min-width: 0; }
  .sidebar.open { transform: translateX(0); }
  .menu-btn { display: flex; align-items: center; justify-content: center; }
  .overlay { display: block; position: fixed; inset: 0; background: rgba(0,0,0,.3); z-index: 5; }
}
</style>
