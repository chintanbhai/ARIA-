"""
Writer Agent — Uses Groq LLM to synthesise a cited, comprehensive answer
from retrieved context + conversation history.
"""

import logging
from typing import List, Dict, Any

from llm.client import chat_completion, GROQ_MODEL

logger = logging.getLogger("aria.agents.writer")

SYSTEM_PROMPT = """You are ARIA, an expert AI research assistant. Your job is to synthesise clear, accurate, and well-structured answers using the provided context.

Guidelines:
- Answer using ONLY the provided context and your knowledge. Cite sources using [Source N] notation.
- Structure complex answers with headers (###) and bullet points where helpful.
- Be direct and informative. Do not pad or repeat yourself.
- If the context is insufficient, say so clearly and answer from general knowledge.
- Always end with a brief 1-sentence summary.
- Use markdown formatting: **bold** for key terms, `code` for technical terms."""


class WriterAgent:
    """
    Given retrieved context, conversation history, and the user's query,
    synthesises a final answer using Groq.
    """

    def __init__(self):
        self.model = GROQ_MODEL
        logger.info(f"WriterAgent using Groq model={self.model}")

    async def run(
        self,
        query: str,
        context: str,
        conversation_history: List[Dict[str, str]],
        long_term_context: str = "",
        sources: List[Dict] = None,
    ) -> Dict[str, Any]:
        logger.info(f"[WRITER] Synthesising answer for: '{query}'")
        trace = [{"agent": "writer", "action": f"Synthesising answer with Groq ({self.model})"}]

        context_block = ""
        if long_term_context:
            context_block += long_term_context + "\n\n"
        if context:
            context_block += f"[Retrieved knowledge base context]\n{context}\n\n"

        messages = list(conversation_history)
        augmented_query = query
        if context_block:
            augmented_query = (
                f"{context_block}"
                f"---\n\nBased on the above context, answer this question:\n{query}"
            )

        if messages and messages[-1]["role"] == "user":
            messages[-1] = {"role": "user", "content": augmented_query}
        else:
            messages.append({"role": "user", "content": augmented_query})

        try:
            answer = chat_completion(messages, system=SYSTEM_PROMPT, model=self.model)
            trace.append({"agent": "writer", "action": f"Generated {len(answer)} char response"})
        except ValueError as e:
            answer = f"⚠ **{e}**"
            trace.append({"agent": "writer", "action": "Auth error — API key missing"})
        except Exception as e:
            logger.error(f"[WRITER] Groq API error: {e}")
            answer = f"⚠ Error generating answer: {str(e)}"
            trace.append({"agent": "writer", "action": f"Error: {str(e)}"})

        citations = []
        if sources:
            seen_urls = set()
            for s in sources:
                url = s.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    citations.append({"title": s.get("title", url), "url": url})

        return {
            "answer":    answer,
            "citations": citations,
            "trace":     trace,
        }
