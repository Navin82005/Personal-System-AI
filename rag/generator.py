from groq import Groq
from config import settings
from utils.logging import setup_logger

logger = setup_logger("generator")

def generate_answer(prompt: str) -> str:
    if not settings.groq_api_key:
        logger.error("GROQ_API_KEY is not set.")
        return "Error: GROQ_API_KEY is not set. Cannot generate answer."

    client = Groq(api_key=settings.groq_api_key)
    
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful and intelligent Personal System AI assistant. Respond directly to the prompt based on the provided context."
                },
                {"role": "user", "content": prompt},
            ],
            # Use llama3 model from Groq
            model="llama-3.1-8b-instant",
            temperature=0.3,
        )
        print("DEBUG: Groq chat completion successful")
        return chat_completion.choices[0].message.content
    except Exception as e:
        print(f"DEBUG: Groq Chat Completion failed: {e}")
        logger.error(f"Error calling Groq API: {e}")
        return f"Error generating answer: {str(e)}"
