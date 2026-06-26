# """
# Writer Agent — Uses Claude to synthesise a cited, comprehensive answer
# from retrieved context + conversation history.
# """

# import os
# import logging
# from typing import List, Dict, Any

# import anthropic

# logger = logging.getLogger("aria.agents.writer")

# CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")

# SYSTEM_PROMPT = """You are ARIA, an expert AI research assistant. Your job is to synthesise clear, accurate, and well-structured answers using the provided context.

# Guidelines:
# - Answer using ONLY the provided context and your knowledge. Cite sources using [Source N] notation.
# - Structure complex answers with headers (###) and bullet points where helpful.
# - Be direct and informative. Do not pad or repeat yourself.
# - If the context is insufficient, say so clearly and answer from general knowledge.
# - Always end with a brief 1-sentence summary.
# - Use markdown formatting: **bold** for key terms, `code` for technical terms."""


# class WriterAgent:
#     """
#     Given retrieved context, conversation history, and the user's query,
#     synthesises a final answer using Claude.
#     """

#     def __init__(self):
#         self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))

#     async def run(
#         self,
#         query: str,
#         context: str,
#         conversation_history: List[Dict[str, str]],
#         long_term_context: str = "",
#         sources: List[Dict] = None,
#     ) -> Dict[str, Any]:
#         logger.info(f"[WRITER] Synthesising answer for: '{query}'")
#         trace = [{"agent": "writer", "action": "Synthesising answer with Claude"}]

#         # Build context block
#         context_block = ""
#         if long_term_context:
#             context_block += long_term_context + "\n\n"
#         if context:
#             context_block += f"[Retrieved knowledge base context]\n{context}\n\n"

#         # Build messages: inject context into user turn
#         messages = list(conversation_history)  # copy history
#         augmented_query = query
#         if context_block:
#             augmented_query = (
#                 f"{context_block}"
#                 f"---\n\nBased on the above context, answer this question:\n{query}"
#             )

#         # Replace last user message if it matches, else append
#         if messages and messages[-1]["role"] == "user":
#             messages[-1] = {"role": "user", "content": augmented_query}
#         else:
#             messages.append({"role": "user", "content": augmented_query})

#         # Claude API call
#         try:
#             response = self.client.messages.create(
#                 model=CLAUDE_MODEL,
#                 max_tokens=1500,
#                 system=SYSTEM_PROMPT,
#                 messages=messages,
#             )
#             answer = response.content[0].text
#             trace.append({"agent": "writer", "action": f"Generated {len(answer)} char response"})
#         except anthropic.AuthenticationError:
#             answer = (
#                 "⚠ **ANTHROPIC_API_KEY not configured.**\n\n"
#                 "Please add your API key to `backend/.env`.\n\n"
#                 "Get one free at https://console.anthropic.com\n\n"
#                 f"*Your question was:* {query}"
#             )
#             trace.append({"agent": "writer", "action": "Auth error — API key missing"})
#         except Exception as e:
#             logger.error(f"[WRITER] Claude API error: {e}")
#             answer = f"⚠ Error generating answer: {str(e)}"
#             trace.append({"agent": "writer", "action": f"Error: {str(e)}"})

#         # Build citations from sources
#         citations = []
#         if sources:
#             seen_urls = set()
#             for s in sources:
#                 url = s.get("url", "")
#                 if url and url not in seen_urls:
#                     seen_urls.add(url)
#                     citations.append({"title": s.get("title", url), "url": url})

#         return {
#             "answer":    answer,
#             "citations": citations,
#             "trace":     trace,
#         }

# backend/agents/writer.py  (updated — model-agnostic)
import os
import logging
from typing import List, Dict, Any

logger = logging.getLogger("aria.agents.writer")

PROVIDER = os.getenv("LLM_PROVIDER", "groq")   # groq | gemini | openrouter | mistral

SYSTEM_PROMPT = """You are ARIA, an expert AI research assistant. Synthesise clear,
accurate answers using the provided context. Cite sources using [Source N] notation.
Use markdown: **bold** for key terms, ### for headers. Be direct and informative."""


def get_client():
    if PROVIDER == "groq":
        from groq import Groq
        return Groq(api_key=os.getenv("GROQ_API_KEY")), "llama-3.3-70b-versatile"

    elif PROVIDER == "gemini":
        import google.generativeai as genai
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        return genai.GenerativeModel("gemini-1.5-flash"), "gemini"

    elif PROVIDER == "openrouter":
        from openai import OpenAI
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
        )
        return client, "meta-llama/llama-3.1-8b-instruct:free"

    elif PROVIDER == "mistral":
        from mistralai import Mistral
        return Mistral(api_key=os.getenv("MISTRAL_API_KEY")), "mistral-small-latest"

    else:
        raise ValueError(f"Unknown provider: {PROVIDER}")


class WriterAgent:
    def __init__(self):
        self.client, self.model = get_client()
        logger.info(f"WriterAgent using provider={PROVIDER} model={self.model}")

    async def run(self, query, context, conversation_history,
                  long_term_context="", sources=None) -> Dict[str, Any]:

        context_block = ""
        if long_term_context:
            context_block += long_term_context + "\n\n"
        if context:
            context_block += f"[Retrieved context]\n{context}\n\n"

        augmented_query = (
            f"{context_block}---\nAnswer this question:\n{query}"
            if context_block else query
        )

        messages = list(conversation_history)
        if messages and messages[-1]["role"] == "user":
            messages[-1] = {"role": "user", "content": augmented_query}
        else:
            messages.append({"role": "user", "content": augmented_query})

        try:
            answer = self._call(messages)
        except Exception as e:
            logger.error(f"Writer error: {e}")
            answer = f"⚠ Error: {e}"

        citations = []
        if sources:
            seen = set()
            for s in sources:
                url = s.get("url", "")
                if url and url not in seen:
                    seen.add(url)
                    citations.append({"title": s.get("title", url), "url": url})

        return {
            "answer":    answer,
            "citations": citations,
            "trace":     [{"agent": "writer", "action": f"Used {PROVIDER}/{self.model}"}],
        }

    def _call(self, messages: List[Dict]) -> str:
        # Gemini has different API shape
        if PROVIDER == "gemini":
            # Convert to Gemini format
            gemini_msgs = []
            for m in messages:
                role = "user" if m["role"] == "user" else "model"
                gemini_msgs.append({"role": role, "parts": [m["content"]]})
            chat = self.client.start_chat(history=gemini_msgs[:-1])
            response = chat.send_message(gemini_msgs[-1]["parts"][0])
            return response.text

        # OpenAI-compatible (Groq, OpenRouter, Mistral)
        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=1500,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + messages,
        )
        return response.choices[0].message.content