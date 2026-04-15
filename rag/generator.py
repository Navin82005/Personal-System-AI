import json
import urllib.request
from config import settings
from utils.logging import setup_logger

logger = setup_logger("generator")

def generate_answer(prompt: str) -> str | None:
    try:
        url = "http://localhost:11434/api/chat"
        data = {
            "model": "phi3:mini",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful and intelligent Personal System AI assistant. Respond directly to the prompt based on the provided context."
                },
                {"role": "user", "content": prompt}
            ],
            "stream": False,
            "options": {
                "temperature": 0.3
            }
        }
        
        req = urllib.request.Request(
            url, 
            data=json.dumps(data).encode('utf-8'), 
            headers={'Content-Type': 'application/json'}
        )
        
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            print("DEBUG: Ollama chat completion successful")
            return result['message']['content']
            
    except Exception as e:
        print(f"DEBUG: Ollama Chat Completion failed: {e}")
        logger.error(f"Error calling Ollama API: {e}")
        return f"Error generating answer: {str(e)}"
