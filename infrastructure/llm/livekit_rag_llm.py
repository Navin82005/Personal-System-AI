import asyncio
from typing import AsyncIterable
from livekit.agents import llm
from application.use_cases.query_rag import RagPipeline

class RagLLMStream(llm.LLMStream):
    def __init__(self, answer_task: asyncio.Task, chat_ctx: llm.ChatContext):
        super().__init__(chat_ctx=chat_ctx, fnc_ctx=None)
        self._task = answer_task

    async def __anext__(self) -> llm.ChatChunk:
        if self._task is None:
            raise StopAsyncIteration
            
        answer = await self._task
        self._task = None # mark as delivered
        
        return llm.ChatChunk(
            choices=[
                llm.Choice(
                    delta=llm.ChatMessage(role="assistant", content=answer),
                    index=0
                )
            ]
        )


class RagLLM(llm.LLM):
    def __init__(self, rag_pipeline: RagPipeline):
        from livekit.agents.llm import LLMCapabilities
        super().__init__(capabilities=LLMCapabilities(streaming=False))
        self.rag = rag_pipeline

    def chat(self, *, chat_ctx: llm.ChatContext, **kwargs) -> llm.LLMStream:
        # We find the latest user message
        user_message = ""
        for msg in chat_ctx.messages:
            if msg.role == "user":
                user_message = msg.content
                
        # Fire off the RAG generation in a separate thread/task
        # We need an asyncio wrapper for the blocking run() call
        loop = asyncio.get_event_loop()
        answer_task = loop.run_in_executor(None, self.rag.run, user_message)
        
        return RagLLMStream(answer_task, chat_ctx)
