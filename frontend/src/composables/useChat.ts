import { ref, nextTick } from "vue";

export interface SourceDoc {
  title: string;
  snippet?: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "thinking";
  content: string;
  sources: SourceDoc[];
  createdAt: Date;
  isStreaming: boolean;
}

function genId(): string {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
}

export function useChat() {
  const messages = ref<ChatMessage[]>([]);
  const isStreaming = ref(false);
  const sessionId = ref<string>(genId());
  const inputText = ref("");
  const error = ref("");

  async function sendMessage(): Promise<void> {
    const content = inputText.value.trim();
    if (!content || isStreaming.value) return;
    inputText.value = "";
    error.value = "";

    const userMsg: ChatMessage = {
      id: genId(), role: "user", content, sources: [],
      createdAt: new Date(), isStreaming: false,
    };
    messages.value.push(userMsg);

    const assistantMsg: ChatMessage = {
      id: genId(), role: "assistant", content: "", sources: [],
      createdAt: new Date(), isStreaming: true,
    };
    messages.value.push(assistantMsg);

    isStreaming.value = true;

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: content, session_id: sessionId.value }),
      });

      if (!response.ok) {
        error.value = `服务器错误 HTTP ${response.status}`;
        assistantMsg.content = `[错误] HTTP ${response.status}`;
        isStreaming.value = false;
        assistantMsg.isStreaming = false;
        return;
      }

      // 用 resp.text() 一次性获取（简单可靠），然后模拟逐字显示
      const raw = await response.text();
      const lines = raw.split(/\r?\n/);

      let currentEvent = "";
      let fullText = "";

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) { currentEvent = ""; continue; }

        if (trimmed.startsWith("event: ")) {
          currentEvent = trimmed.slice(7);
        } else if (trimmed.startsWith("data: ")) {
          const data = trimmed.slice(6);

          if (currentEvent === "token" && data) {
            fullText += data;
          } else if (currentEvent === "source") {
            try {
              const parsed = JSON.parse(data);
              if (Array.isArray(parsed)) assistantMsg.sources = parsed;
            } catch { /* ignore */ }
          } else if (currentEvent === "error") {
            error.value = data;
            fullText += `\n[错误] ${data}`;
          } else if (currentEvent === "thinking") {
            assistantMsg.role = "thinking";
            assistantMsg.content = data || "思考中...";
            await nextTick();
          }
        }
      }

      // 逐字动画显示
      assistantMsg.role = "assistant";
      for (let i = 0; i < fullText.length; i++) {
        assistantMsg.content = fullText.slice(0, i + 1);
        await nextTick();
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "未知错误";
      error.value = msg;
      assistantMsg.content = `[请求失败] ${msg}`;
    } finally {
      assistantMsg.isStreaming = false;
      isStreaming.value = false;
    }
  }

  function newSession(): void {
    sessionId.value = genId();
    messages.value = [];
    error.value = "";
  }

  return { messages, isStreaming, sessionId, inputText, error, sendMessage, newSession };
}
