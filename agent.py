import asyncio
import os
import logging
from config import settings

os.environ["LIVEKIT_URL"] = settings.livekit_url
os.environ["LIVEKIT_API_KEY"] = settings.livekit_api_key
os.environ["LIVEKIT_API_SECRET"] = settings.livekit_api_secret

from livekit.agents import AutoSubscribe, JobContext, WorkerOptions, cli
from livekit.agents.pipeline import VoicePipelineAgent
from livekit.plugins import silero

from application.use_cases.query_rag import RagPipeline
from vector_store.vector_db import VectorDB

from infrastructure.stt.livekit_whisper import WhisperSTT
from infrastructure.tts.livekit_magpie import MagpieTTS
from infrastructure.llm.livekit_rag_llm import RagLLM

logger = logging.getLogger("livekit-agent")

async def entrypoint(ctx: JobContext):
    logger.info("Initializing LiveKit Voice Pipeline Agent...")
    
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    logger.info("Agent connected to room")

    # Initialize context and DB
    vector_db = VectorDB()
    rag_pipeline = RagPipeline(vector_db)
    
    # Instantiate Custom Plugins
    vad_plugin = silero.VAD.load()
    stt_plugin = WhisperSTT()
    llm_plugin = RagLLM(rag_pipeline)
    tts_plugin = MagpieTTS(prompt_file="prompt.wav")

    # Tie everything together in VoicePipelineAgent
    agent = VoicePipelineAgent(
        vad=vad_plugin,
        stt=stt_plugin,
        llm=llm_plugin,
        tts=tts_plugin,
    )

    # Start the orchestrator inside the room context
    agent.start(ctx.room)
    
    await asyncio.sleep(1)
    await agent.say("Hello, I am ready to answer your questions via voice.", allow_interruptions=True)

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
