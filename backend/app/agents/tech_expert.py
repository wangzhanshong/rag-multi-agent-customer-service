"""
技术专家Agent (Tech Expert Agent)

职责: 处理笔记本技术咨询，通过RAG知识库检索相关文档后生成回复。
要求给出引用来源，对不确定的问题主动追问。
"""

from agents import Agent, function_tool

from app.config import AGENT_MODEL
from app.rag.retrieval import RetrievedDocument, retrieve

SYSTEM_PROMPT = """你是一位专业的笔记本售后技术支持专家。你需要基于知识库中的官方文档回答用户的问题。

规则:
1. 每次回答问题前，必须先使用 rag_search 工具检索知识库
2. 回答时引用具体的文档标题作为来源，格式: 【来源: 文档标题】
3. 如果知识库中没有相关信息，诚实告知用户，不要编造
4. 对于信息不足的问题，主动追问关键细节（如笔记本型号、操作系统版本等）
5. 回答应简洁专业，使用有序列表或分步骤说明
6. 涉及硬件操作时，提醒用户注意安全（断电、防静电等）
"""


@function_tool
async def rag_search(query: str) -> str:
    """在笔记本售后知识库中搜索相关文档。调用此工具获取官方产品信息、故障处理方案、保修政策等。

    Args:
        query: 用户的原始问题或搜索关键词，保持自然语言形式。
    """
    from app.rag.retrieval import keyword_recall

    docs: list[RetrievedDocument] = await retrieve(query, top_k=5)

    if not docs:
        import jieba
        keywords = [w for w in jieba.cut(query) if len(w) >= 2]
        seen: set[str] = set()
        for kw in keywords[:5]:
            kw_docs = await keyword_recall(kw, top_k=3)
            for d in kw_docs:
                key = d.doc_id + d.chunk_text[:50]
                if key not in seen:
                    seen.add(key)
                    docs.append(d)
        docs.sort(key=lambda d: d.score, reverse=True)
        docs = docs[:5]

    if not docs:
        return "未在知识库中找到相关信息。"

    lines: list[str] = []
    for i, doc in enumerate(docs, 1):
        lines.append(f"[{i}] 标题: {doc.title}\n内容: {doc.chunk_text}\n相关性: {doc.score:.2f}")
    return "\n\n".join(lines)


tech_expert_agent = Agent(
    name="Tech Expert",
    instructions=SYSTEM_PROMPT,
    model=AGENT_MODEL,
    tools=[rag_search],
)
