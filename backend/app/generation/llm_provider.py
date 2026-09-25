import os
import json
import re
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import httpx

class BaseLLMProvider(ABC):
    """Abstract interface for pluggable LLM generation providers."""

    @abstractmethod
    def generate_cited_answer(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """
        Executes generation and returns parsed JSON:
        {"answer": str, "citations": [{"chunk_id": int, "quoted_snippet": str}]}
        """
        pass


class OpenAILLMProvider(BaseLLMProvider):
    """
    OpenAI and OpenAI-compatible API provider (supports DeepSeek, Groq, OpenRouter, local vLLM).
    Falls back gracefully to GroundedRuleLLMProvider if balance/network/auth errors occur.
    """
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None, base_url: Optional[str] = None):
        import openai
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL") or os.getenv("OPENAI_API_BASE")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        
        kwargs = {"api_key": self.api_key}
        if self.base_url:
            kwargs["base_url"] = self.base_url
        self.client = openai.OpenAI(**kwargs)
        self._fallback = GroundedRuleLLMProvider()

    def generate_cited_answer(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        try:
            # Request JSON object format
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=0.1,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            content = response.choices[0].message.content or "{}"
            try:
                parsed = json.loads(content)
                if isinstance(parsed, dict) and "answer" in parsed:
                    return parsed
            except json.JSONDecodeError:
                return self._extract_json_fallback(content)
        except Exception as e:
            print(f"[LLM Warning] Remote API error ({type(e).__name__}: {e}). Using local grounded fallback.")
            return self._fallback.generate_cited_answer(system_prompt, user_prompt)

        return self._fallback.generate_cited_answer(system_prompt, user_prompt)

    def _extract_json_fallback(self, text: str) -> Dict[str, Any]:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                pass
        return {"answer": text, "citations": []}


class OllamaLLMProvider(BaseLLMProvider):
    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None):
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = model or os.getenv("OLLAMA_MODEL", "llama3")
        self._fallback = GroundedRuleLLMProvider()

    def generate_cited_answer(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        url = f"{self.base_url.rstrip('/')}/api/chat"
        payload = {
            "model": self.model,
            "format": "json",
            "stream": False,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "options": {"temperature": 0.1}
        }
        try:
            with httpx.Client(timeout=60.0) as client:
                resp = client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                content = data.get("message", {}).get("content", "{}")
                try:
                    return json.loads(content)
                except Exception:
                    match = re.search(r'\{.*\}', content, re.DOTALL)
                    if match:
                        return json.loads(match.group(0))
                    return {"answer": content, "citations": []}
        except Exception as e:
            print(f"[Ollama Warning] {e}. Falling back to local grounded engine.")
            return self._fallback.generate_cited_answer(system_prompt, user_prompt)


class AnthropicLLMProvider(BaseLLMProvider):
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model = model or os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
        self._fallback = GroundedRuleLLMProvider()

    def generate_cited_answer(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": self.api_key or "",
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        prompt_with_format = f"{user_prompt}\n\nYou must reply ONLY with a valid JSON object matching the requested schema."
        payload = {
            "model": self.model,
            "max_tokens": 1024,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": prompt_with_format}
            ],
            "temperature": 0.1
        }
        try:
            with httpx.Client(timeout=60.0) as client:
                resp = client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                res_data = resp.json()
                content = res_data["content"][0]["text"]
                match = re.search(r'\{.*\}', content, re.DOTALL)
                if match:
                    return json.loads(match.group(0))
                return json.loads(content)
        except Exception as e:
            print(f"[Anthropic Warning] {e}. Falling back to local grounded engine.")
            return self._fallback.generate_cited_answer(system_prompt, user_prompt)


class GroundedRuleLLMProvider(BaseLLMProvider):
    """
    Local deterministic LLM engine for environments without active cloud credits.
    Extracts relevant claims directly from retrieved chunks,
    guaranteeing faithful citations, source tracking, and exact snippets.
    """

    def generate_cited_answer(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        # Regex to extract each labeled context chunk
        chunk_pattern = re.compile(
            r'\[chunk_id:\s*(\d+)\s*\|\s*source:\s*([^|\]]+)(?:\|\s*([^\]]+))?\]\s*\n(.*?)(?=\n\n\[chunk_id|\Z|\n----------------)',
            re.DOTALL
        )
        matches = chunk_pattern.findall(user_prompt)

        # Extract user query
        query_match = re.search(r'User Question:\s*(.*?)(?:\n\nProvide|\Z)', user_prompt, re.DOTALL)
        query = query_match.group(1).strip() if query_match else ""
        stopwords = {
            "what", "is", "the", "a", "an", "and", "or", "in", "on", "for", "of", "to",
            "how", "many", "does", "do", "when", "where", "are", "can", "you", "tell", "me"
        }
        query_words = set(re.findall(r'[a-zA-Z0-9]+', query.lower())) - stopwords

        found_citations = []
        answer_sentences = []

        for cid_str, source, loc, chunk_text in matches:
            cid = int(cid_str)
            # Break into sentences/lines
            lines = [l.strip() for l in chunk_text.splitlines() if l.strip()]
            for line in lines:
                line_words = set(re.findall(r'[a-zA-Z0-9]+', line.lower()))
                overlap = query_words.intersection(line_words)
                if len(overlap) >= 1:
                    answer_sentences.append(line)
                    found_citations.append({
                        "chunk_id": cid,
                        "quoted_snippet": line[:150]
                    })
                    break

        if not found_citations:
            # If no direct keyword match, inspect top chunk if relevant
            if matches:
                cid = int(matches[0][0])
                first_lines = [l.strip() for l in matches[0][3].splitlines() if l.strip()]
                if first_lines:
                    answer_sentences.append(first_lines[0])
                    found_citations.append({
                        "chunk_id": cid,
                        "quoted_snippet": first_lines[0][:150]
                    })

        if not found_citations:
            return {
                "answer": "I cannot answer this based on the provided documents.",
                "citations": []
            }

        answer_text = " ".join(answer_sentences[:3])
        return {
            "answer": answer_text,
            "citations": found_citations[:3]
        }


def get_llm_provider() -> BaseLLMProvider:
    """
    Factory function returning the active LLM provider based on .env configuration.
    Supported: 'openai', 'anthropic', 'ollama', 'deepseek', 'rule'
    """
    provider_name = os.getenv("LLM_PROVIDER", "").lower()

    if provider_name == "anthropic" and os.getenv("ANTHROPIC_API_KEY"):
        return AnthropicLLMProvider()
    elif provider_name == "ollama":
        return OllamaLLMProvider()
    elif provider_name in ["openai", "deepseek"] or os.getenv("OPENAI_API_KEY"):
        return OpenAILLMProvider()
    else:
        return GroundedRuleLLMProvider()
