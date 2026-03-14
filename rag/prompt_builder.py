def build_prompt(query: str, context: str) -> str:
    prompt = f"""You are a helpful and intelligent Personal System AI assistant. 
You must answer questions using ONLY the provided document context.

If you don't know the answer or the context doesn't contain the information, just say that you don't know, don't try to make up an answer.
Keep the answer concise and strictly based on the provided context.

Context:
{context}

Question:
{query}

Answer:"""
    return prompt
