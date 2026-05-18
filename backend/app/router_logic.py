import asyncio
import json
import logging
import re
from openai import OpenAI
from app.config import settings
from app.models import RoutingResponse
from app.realtime_data import build_realtime_context, direct_realtime_answer

logger = logging.getLogger(__name__)

DEEPSEEK_INTENTS = {"translation", "summary"}
ROUTER_INTENTS = {"realtime", "simple"}
REASONING_INTENTS = {"analysis", "code", "math", "planning", "reasoning"}

TRANSLATION_PATTERNS = (
    "translate",
    "translation",
    "convert this text",
    "in french",
    "in spanish",
    "in german",
    "in italian",
    "in polish",
    "in turkish",
    "in azerbaijani",
)

SUMMARY_PATTERNS = (
    "summarize",
    "summary",
    "tl;dr",
    "tldr",
    "recap",
    "key points",
)

SIMPLE_PATTERNS = (
    "what is",
    "who is",
    "when is",
    "where is",
    "define",
    "explain briefly",
)

REASONING_PATTERNS = (
    "reason step by step",
    "think through",
    "analyze",
    "compare and contrast",
    "tradeoffs",
    "debug",
    "root cause",
    "write code",
    "generate code",
    "refactor",
    "prove",
    "solve",
    "calculate",
    "optimize",
)

ARCHITECTURE_PLANNING_PATTERNS = (
    "architecture",
    "landing zone",
    "deployment plan",
    "step by step",
    "design a",
    "design an",
    "plan for",
    "roadmap",
)

REALTIME_PATTERNS = (
    "real time",
    "real-time",
    "realtime",
    "live data",
    "current",
    "latest",
    "today",
    "right now",
    "now",
    "this week",
    "this month",
    "recent",
    "news",
    "stock price",
    "share price",
    "crypto price",
    "exchange rate",
    "weather",
    "score",
    "standings",
    "schedule",
)

MAX_HISTORY_MESSAGES = 6
MAX_MESSAGE_CHARS = 1200
CLASSIFIER_TIMEOUT_SECONDS = 10
FAST_MODEL_TIMEOUT_SECONDS = 15
FAST_RETRY_TIMEOUT_SECONDS = 10
REASONING_TIMEOUT_SECONDS = 25

class ModelRouter:
    def __init__(self):
        endpoint = settings.AZURE_OPENAI_ENDPOINT.rstrip("/")
        self.client = OpenAI(
            api_key=settings.AZURE_OPENAI_KEY,
            base_url=f"{endpoint}/openai/v1/"
        )
        self.deepseek_model = settings.DEEPSEEK_MODEL
        self.router_model = settings.ROUTER_MODEL
        self.reasoning_model = settings.REASONING_MODEL

    async def route_prompt(self, prompt: str, messages: list = None) -> RoutingResponse:
        """
        Main routing logic:
        1. Use deterministic rules for obvious routes
        2. Use GPT-5-mini to classify ambiguous prompts
        3. Route to the selected model
        """
        
        try:
            direct_answer = direct_realtime_answer(prompt)
            if direct_answer:
                return RoutingResponse(
                    modelUsed="realtime-clock",
                    reason="Direct realtime utility: date/time",
                    answer=direct_answer
                )

            intent_classification = self._rule_based_route(prompt)
            if intent_classification is None:
                intent_classification = await self._classify_intent(prompt)
            
            route = intent_classification["route"]

            if route == "reasoning":
                try:
                    response = await self._call_reasoning_model(prompt, messages)
                    return RoutingResponse(
                        modelUsed=self.reasoning_model,
                        reason=intent_classification["reason"],
                        answer=response
                    )
                except (asyncio.TimeoutError, Exception) as reasoning_error:
                    logger.warning(f"Reasoning route fallback to mini: {reasoning_error}")
                    response = await self._call_mini_answer_model(prompt, messages)
                    return RoutingResponse(
                        modelUsed=self.router_model,
                        reason=f"{intent_classification['reason']} | GPT-5-Pro unavailable/slow, fallback → GPT-5-mini",
                        answer=response
                    )
            if route == "router":
                if intent_classification.get("intent") == "realtime":
                    response = await self._call_router_model(prompt, messages)
                else:
                    response = await self._call_mini_answer_model(prompt, messages)
                return RoutingResponse(
                    modelUsed=self.router_model,
                    reason=intent_classification["reason"],
                    answer=response
                )

            else:
                response = await self._call_deepseek_model(prompt, messages)
                return RoutingResponse(
                    modelUsed=self.deepseek_model,
                    reason=intent_classification["reason"],
                    answer=response
                )
                
        except asyncio.TimeoutError:
            logger.error("Routing timed out")
            try:
                response = await self._call_mini_answer_model(prompt, messages, compact=True)
                return RoutingResponse(
                    modelUsed=self.router_model,
                    reason="Selected model timed out, compact fallback → GPT-5-mini",
                    answer=response
                )
            except Exception as fallback_error:
                logger.error(f"Compact fallback model error: {fallback_error}")
                return RoutingResponse(
                    modelUsed="none",
                    reason="Model timeout",
                    answer="The selected model and fallback model both took too long. Please retry in a moment."
                )
        except Exception as e:
            logger.error(f"Routing error: {e}")
            try:
                response = await self._call_mini_answer_model(prompt, messages)
                return RoutingResponse(
                    modelUsed=self.router_model,
                    reason="Fallback after error → GPT-5-mini",
                    answer=response
                )
            except Exception as fallback_error:
                logger.error(f"Fallback model error: {fallback_error}")
                return RoutingResponse(
                    modelUsed="none",
                    reason="Model timeout/error",
                    answer="The model request took too long or failed. Please try again with a shorter prompt."
                )

    def _rule_based_route(self, prompt: str) -> dict | None:
        text = prompt.strip().lower()
        word_count = len(text.split())

        if self._contains_any(text, REALTIME_PATTERNS):
            return {
                "route": "router",
                "reason": "Rule match: real-time/current data → GPT-5-mini",
                "intent": "realtime",
                "confidence": 0.9
            }

        if self._contains_any(text, TRANSLATION_PATTERNS):
            return {
                "route": "deepseek",
                "reason": "Rule match: translation → DeepSeek",
                "intent": "translation",
                "confidence": 0.95
            }

        if self._contains_any(text, SUMMARY_PATTERNS) and word_count < 900:
            return {
                "route": "deepseek",
                "reason": "Rule match: summary → DeepSeek",
                "intent": "summary",
                "confidence": 0.9
            }

        if self._contains_any(text, ARCHITECTURE_PLANNING_PATTERNS):
            return {
                "route": "router",
                "reason": "Rule match: architecture/planning → GPT-5-mini",
                "intent": "simple",
                "confidence": 0.85
            }

        if self._contains_any(text, REASONING_PATTERNS):
            return {
                "route": "reasoning",
                "reason": "Rule match: complex reasoning → GPT-5-Pro",
                "intent": "reasoning",
                "confidence": 0.9
            }

        if word_count <= 18 and (text.endswith("?") or self._contains_any(text, SIMPLE_PATTERNS)):
            return {
                "route": "router",
                "reason": "Rule match: short/simple query → GPT-5-mini",
                "intent": "simple",
                "confidence": 0.85
            }

        return None

    async def _classify_intent(self, prompt: str) -> dict:
        """
        Classify prompt intent:
        - Translation → DeepSeek (fast, cheap)
        - Simple/Summary → DeepSeek
        - Real-time/current-data questions → GPT-5-mini
        - Complex/Reasoning → GPT-5-Pro
        """
        
        classification_prompt = f"""Classify the best model for this prompt in a multi-model Azure AI demo.
        
Prompt: "{prompt}"

Respond with only one JSON object:
{{
  "intent": "translation|summary|simple|realtime|analysis|code|math|planning|reasoning",
  "confidence": 0.0-1.0,
  "route": "deepseek|router|reasoning",
  "reason": "short explanation"
}}

Rules:
- Translation and short summaries: deepseek
- Simple factual questions, definitions, and brief explanations: router
- Current/latest/real-time/live-data questions, including news, prices, weather, sports scores, recent events, or anything where freshness matters: router
- Multi-step analysis, architecture, planning, debugging, math/logic, code generation, code review, and optimization: reasoning
- If the user asks for tradeoffs, a plan, root cause, or a deep comparison: reasoning

Return ONLY valid JSON."""

        try:
            response = await self._run_blocking(
                CLASSIFIER_TIMEOUT_SECONDS,
                self.client.chat.completions.create,
                model=self.router_model,
                messages=[{"role": "user", "content": classification_prompt}],
                max_completion_tokens=150,
                timeout=CLASSIFIER_TIMEOUT_SECONDS
            )
            
            classification_text = response.choices[0].message.content or ""
            classification = self._parse_classifier_json(classification_text)
            
            route = str(classification.get("route", "")).lower()
            intent = classification.get("intent", "simple")
            confidence = float(classification.get("confidence", 0.0))
            selected_route = route
            if intent in REASONING_INTENTS:
                selected_route = "reasoning"
            if intent in ROUTER_INTENTS:
                selected_route = "router"
            if intent in DEEPSEEK_INTENTS:
                selected_route = "deepseek"
            if selected_route not in {"deepseek", "router", "reasoning"}:
                selected_route = "deepseek"
            
            reason_map = {
                "translation": "Classifier: translation → DeepSeek",
                "summary": "Classifier: summary → DeepSeek",
                "simple": "Classifier: simple query → GPT-5-mini",
                "realtime": "Classifier: real-time/current data → GPT-5-mini",
                "analysis": "Classifier: analysis → GPT-5-Pro",
                "code": "Classifier: code task → GPT-5-Pro",
                "math": "Classifier: math/logic → GPT-5-Pro",
                "planning": "Classifier: planning → GPT-5-Pro",
                "reasoning": "Classifier: reasoning task → GPT-5-Pro"
            }
            
            reason = reason_map.get(intent)
            if not reason:
                route_labels = {
                    "deepseek": "cost-optimized route → DeepSeek",
                    "router": "freshness-sensitive route → GPT-5-mini",
                    "reasoning": "complex task → GPT-5-Pro"
                }
                reason = f"Classifier: {route_labels[selected_route]}"
            
            return {
                "route": selected_route,
                "reason": f"{reason} ({confidence:.0%} confidence)",
                "intent": intent,
                "confidence": confidence
            }
            
        except Exception as e:
            logger.warning(f"Classification error, defaulting to DeepSeek: {e}")
            return {
                "route": "deepseek",
                "reason": "Classification fallback → DeepSeek",
                "intent": "simple",
                "confidence": 0.0
            }

    async def _call_deepseek_model(self, prompt: str, messages: list = None) -> str:
        """Call DeepSeek-V4-Flash model"""
        
        message_list = self._prepare_messages(messages)
        message_list.append({"role": "user", "content": prompt})
        
        try:
            response = await self._run_blocking(
                FAST_MODEL_TIMEOUT_SECONDS,
                self.client.chat.completions.create,
                model=self.deepseek_model,
                messages=message_list,
                max_completion_tokens=700,
                timeout=FAST_MODEL_TIMEOUT_SECONDS
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"DeepSeek error: {e}")
            raise

    async def _call_mini_answer_model(
        self,
        prompt: str,
        messages: list = None,
        compact: bool = False
    ) -> str:
        """Call GPT-5-mini as a fast fallback/general answer model."""

        max_tokens = 300 if compact else 450
        timeout_seconds = FAST_RETRY_TIMEOUT_SECONDS if compact else FAST_MODEL_TIMEOUT_SECONDS
        system_message = {
            "role": "system",
            "content": (
                "Answer clearly and practically. For architecture, planning, or step-by-step requests, "
                "give a structured answer with enough detail to be useful, but keep it demo-friendly: "
                "prefer 5-7 concise steps unless the user explicitly asks for a very detailed plan. "
                "Avoid long introductions and avoid expanding every subtopic. "
                "If the user asks for current/live data and no source is provided, say what is missing."
            )
        }
        message_list = [system_message, *self._prepare_messages(messages)]
        message_list.append({"role": "user", "content": prompt})

        response = await self._run_blocking(
            timeout_seconds,
            self.client.chat.completions.create,
            model=self.router_model,
            messages=message_list,
            max_completion_tokens=max_tokens,
            timeout=timeout_seconds
        )
        return response.choices[0].message.content

    async def _call_router_model(self, prompt: str, messages: list = None) -> str:
        """Call GPT-5-mini for freshness-sensitive prompts."""

        realtime_context = await self._run_blocking(
            FAST_MODEL_TIMEOUT_SECONDS,
            build_realtime_context,
            prompt
        )
        context_instruction = (
            f"\n\nRetrieved realtime context:\n{realtime_context}"
            if realtime_context
            else "\n\nNo realtime source returned useful context for this prompt."
        )
        system_message = {
            "role": "system",
            "content": (
                "You are handling a freshness-sensitive request in an Azure multi-model demo. "
                "Use the retrieved realtime context below when it is relevant. "
                "Mention the source and timestamp/link if present. "
                "If live data is required but the retrieved context is missing or incomplete, say that clearly, "
                "avoid inventing current facts, and explain what data or integration would be needed."
                f"{context_instruction}"
            )
        }
        message_list = [system_message, *self._prepare_messages(messages)]
        message_list.append({"role": "user", "content": prompt})

        try:
            response = await self._run_blocking(
                FAST_MODEL_TIMEOUT_SECONDS,
                self.client.chat.completions.create,
                model=self.router_model,
                messages=message_list,
                max_completion_tokens=500,
                timeout=FAST_MODEL_TIMEOUT_SECONDS
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Router model error: {e}")
            raise

    async def _call_reasoning_model(self, prompt: str, messages: list = None) -> str:
        """Call GPT-5-Pro reasoning model through the Responses API."""
        
        message_list = self._prepare_messages(messages)
        message_list.append({"role": "user", "content": prompt})
        
        try:
            response = await self._run_blocking(
                REASONING_TIMEOUT_SECONDS,
                self.client.responses.create,
                model=self.reasoning_model,
                input=message_list,
                max_output_tokens=4000,
                timeout=REASONING_TIMEOUT_SECONDS
            )
            return self._extract_response_text(response)
        except Exception as e:
            logger.error(f"Reasoning model error: {e}")
            raise

    async def _run_blocking(self, timeout_seconds: int, func, *args, **kwargs):
        return await asyncio.wait_for(
            asyncio.to_thread(func, *args, **kwargs),
            timeout=timeout_seconds
        )

    def _parse_classifier_json(self, text: str) -> dict:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if not match:
                raise
            return json.loads(match.group(0))

    def _contains_any(self, text: str, patterns: tuple[str, ...]) -> bool:
        return any(pattern in text for pattern in patterns)

    def _prepare_messages(self, messages: list = None) -> list:
        prepared = []
        for message in list(messages or [])[-MAX_HISTORY_MESSAGES:]:
            content = str(message.get("content", ""))[:MAX_MESSAGE_CHARS]
            role = message.get("role")
            if role in {"user", "assistant", "system"} and content:
                prepared.append({"role": role, "content": content})
        return prepared

    def _extract_response_text(self, response) -> str:
        output_text = getattr(response, "output_text", None)
        if output_text:
            return output_text

        text_parts = []
        for item in getattr(response, "output", []) or []:
            for content in getattr(item, "content", []) or []:
                text = getattr(content, "text", None)
                if text:
                    text_parts.append(text)

        if text_parts:
            return "\n".join(text_parts)

        raise ValueError("Responses API returned no text output")

# Global router instance
_router = None

def get_router() -> ModelRouter:
    global _router
    if _router is None:
        _router = ModelRouter()
    return _router
