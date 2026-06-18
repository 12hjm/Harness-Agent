from __future__ import annotations

from langgraph.graph import END, StateGraph
from langgraph.checkpoint.memory import MemorySaver

from app.agent.state import AgentState
from app.domain.models import OutboundMessage
from app.integrations.llm import LLMProvider
from app.rag.retriever import KnowledgeRetriever
from app.storage.conversations import ConversationRepository


class CustomerServiceAgent:
    def __init__(
        self,
        llm: LLMProvider,
        retriever: KnowledgeRetriever,
        conversations: ConversationRepository,
        fallback_message: str,
    ):
        self.llm = llm
        self.retriever = retriever
        self.conversations = conversations
        self.fallback_message = fallback_message
        self.graph = self._build_graph()

    def _build_graph(self):
        builder = StateGraph(AgentState)
        builder.add_node("normalize_message", self._normalize_message)
        builder.add_node("rewrite_query", self._rewrite_query)
        builder.add_node("retrieve_knowledge", self._retrieve_knowledge)
        builder.add_node("grade_evidence", self._grade_evidence)
        builder.add_node("generate_answer", self._generate_answer)
        builder.add_node("fallback_answer", self._fallback_answer)
        builder.add_node("persist_conversation", self._persist_conversation)

        builder.set_entry_point("normalize_message")
        builder.add_edge("normalize_message", "rewrite_query")
        builder.add_edge("rewrite_query", "retrieve_knowledge")
        builder.add_edge("retrieve_knowledge", "grade_evidence")
        builder.add_conditional_edges(
            "grade_evidence",
            lambda state: "generate_answer" if state["has_evidence"] else "fallback_answer",
            {"generate_answer": "generate_answer", "fallback_answer": "fallback_answer"},
        )
        builder.add_edge("generate_answer", "persist_conversation")
        builder.add_edge("fallback_answer", "persist_conversation")
        builder.add_edge("persist_conversation", END)
        return builder.compile(checkpointer=MemorySaver())

    async def answer(self, inbound) -> OutboundMessage:
        state = await self.graph.ainvoke(
            {"inbound": inbound},
            config={"configurable": {"thread_id": inbound.conversation_id}},
        )
        return state["outbound"]

    async def _normalize_message(self, state: AgentState) -> AgentState:
        inbound = state["inbound"]
        history = await self.conversations.recent_messages(inbound.conversation_id)
        return {"history": history}

    async def _rewrite_query(self, state: AgentState) -> AgentState:
        inbound = state["inbound"]
        query = await self.llm.rewrite_query(inbound.content, state.get("history", []))
        return {"rewritten_query": query}

    async def _retrieve_knowledge(self, state: AgentState) -> AgentState:
        chunks = await self.retriever.retrieve(state["rewritten_query"])
        return {"retrieved_chunks": chunks}

    async def _grade_evidence(self, state: AgentState) -> AgentState:
        chunks = state.get("retrieved_chunks", [])
        return {"has_evidence": self.retriever.has_sufficient_evidence(chunks)}

    async def _generate_answer(self, state: AgentState) -> AgentState:
        chunks = state.get("retrieved_chunks", [])
        answer = await self.llm.answer(state["rewritten_query"], chunks)
        citations = self.retriever.to_citations(chunks)
        return {"answer": answer, "citations": citations}

    async def _fallback_answer(self, state: AgentState) -> AgentState:
        return {"answer": self.fallback_message, "citations": []}

    async def _persist_conversation(self, state: AgentState) -> AgentState:
        inbound = state["inbound"]
        outbound = OutboundMessage(
            platform=inbound.platform,
            conversation_id=inbound.conversation_id,
            content=state["answer"],
            citations=state.get("citations", []),
            metadata={"query": state.get("rewritten_query"), "has_evidence": state.get("has_evidence")},
        )
        await self.conversations.append_turn(inbound, outbound)
        return {"outbound": outbound}

