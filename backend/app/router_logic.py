import json
import logging
import re
from openai import OpenAI
from app.config import settings
from app.models import RoutingResponse

logger = logging.getLogger(__name__)

DEEPSEEK_INTENTS = {"translation", "summary", "simple"}
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
    "architecture",
    "debug",
    "root cause",
    "design a",
    "write code",
    "generate code",
    "refactor",
    "prove",
    "solve",
    "calculate",
    "optimize",
)

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
            intent_classification = self._rule_based_route(prompt)
            if intent_classification is None:
                intent_classification = await self._classify_intent(prompt)
            
            if intent_classification["should_use_reasoning"]:
                response = await self._call_reasoning_model(prompt, messages)
                return RoutingResponse(
                    modelUsed=self.reasoning_model,
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
                
        except Exception as e:
            logger.error(f"Routing error: {e}")
            # Fallback to DeepSeek on error
            response = await self._call_deepseek_model(prompt, messages)
            return RoutingResponse(
                modelUsed=self.deepseek_model,
                reason="Fallback after error",
                answer=response
            )

    def _rule_based_route(self, prompt: str) -> dict | None:
        text = prompt.strip().lower()
        word_count = len(text.split())

        if self._contains_any(text, TRANSLATION_PATTERNS):
            return {
                "should_use_reasoning": False,
                "reason": "Rule match: translation → DeepSeek",
                "intent": "translation",
                "confidence": 0.95
            }

        if self._contains_any(text, SUMMARY_PATTERNS) and word_count < 900:
            return {
                "should_use_reasoning": False,
                "reason": "Rule match: summary → DeepSeek",
                "intent": "summary",
                "confidence": 0.9
            }

        if self._contains_any(text, REASONING_PATTERNS):
            return {
                "should_use_reasoning": True,
                "reason": "Rule match: complex reasoning → GPT-5-Pro",
                "intent": "reasoning",
                "confidence": 0.9
            }

        if word_count <= 18 and (text.endswith("?") or self._contains_any(text, SIMPLE_PATTERNS)):
            return {
                "should_use_reasoning": False,
                "reason": "Rule match: short/simple query → DeepSeek",
                "intent": "simple",
                "confidence": 0.85
            }

        return None

    async def _classify_intent(self, prompt: str) -> dict:
        """
        Classify prompt intent:
        - Translation → DeepSeek (fast, cheap)
        - Simple/Summary → DeepSeek
        - Complex/Reasoning → GPT-5-Pro
        """
        
        classification_prompt = f"""Classify the best model for this prompt in a multi-model Azure AI demo.
        
Prompt: "{prompt}"

Respond with only one JSON object:
{{
  "intent": "translation|summary|simple|analysis|code|math|planning|reasoning",
  "confidence": 0.0-1.0,
  "route": "deepseek|reasoning",
  "reason": "short explanation"
}}

Rules:
- Translation, short summaries, simple factual questions, definitions, and brief explanations: deepseek
- Multi-step analysis, architecture, planning, debugging, math/logic, code generation, code review, and optimization: reasoning
- If the user asks for tradeoffs, a plan, root cause, or a deep comparison: reasoning

Return ONLY valid JSON."""

        try:
            response = self.client.chat.completions.create(
                model=self.router_model,
                messages=[{"role": "user", "content": classification_prompt}],
                max_completion_tokens=150
            )
            
            classification_text = response.choices[0].message.content or ""
            classification = self._parse_classifier_json(classification_text)
            
            route = str(classification.get("route", "")).lower()
            intent = classification.get("intent", "simple")
            confidence = float(classification.get("confidence", 0.0))
            should_use_reasoning = route == "reasoning" or intent in REASONING_INTENTS
            if intent in DEEPSEEK_INTENTS:
                should_use_reasoning = False
            
            reason_map = {
                "translation": "Classifier: translation → DeepSeek",
                "summary": "Classifier: summary → DeepSeek",
                "simple": "Classifier: simple query → DeepSeek",
                "analysis": "Classifier: analysis → GPT-5-Pro",
                "code": "Classifier: code task → GPT-5-Pro",
                "math": "Classifier: math/logic → GPT-5-Pro",
                "planning": "Classifier: planning → GPT-5-Pro",
                "reasoning": "Classifier: reasoning task → GPT-5-Pro"
            }
            
            reason = reason_map.get(intent)
            if not reason:
                reason = "Classifier: complex task → GPT-5-Pro" if should_use_reasoning else "Classifier: cost-optimized route → DeepSeek"
            
            return {
                "should_use_reasoning": should_use_reasoning,
                "reason": f"{reason} ({confidence:.0%} confidence)",
                "intent": intent,
                "confidence": confidence
            }
            
        except Exception as e:
            logger.warning(f"Classification error, defaulting to DeepSeek: {e}")
            return {
                "should_use_reasoning": False,
                "reason": "Classification fallback → DeepSeek",
                "intent": "simple",
                "confidence": 0.0
            }

    async def _call_deepseek_model(self, prompt: str, messages: list = None) -> str:
        """Call DeepSeek-V4-Flash model"""
        
        message_list = list(messages or [])
        message_list.append({"role": "user", "content": prompt})
        
        try:
            response = self.client.chat.completions.create(
                model=self.deepseek_model,
                messages=message_list,
                max_completion_tokens=2000
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"DeepSeek error: {e}")
            raise

    async def _call_reasoning_model(self, prompt: str, messages: list = None) -> str:
        """Call GPT-5-Pro reasoning model"""
        
        message_list = list(messages or [])
        message_list.append({"role": "user", "content": prompt})
        
        try:
            response = self.client.chat.completions.create(
                model=self.reasoning_model,
                messages=message_list,
                max_completion_tokens=4000
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Reasoning model error: {e}")
            raise

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

# Global router instance
_router = None

def get_router() -> ModelRouter:
    global _router
    if _router is None:
        _router = ModelRouter()
    return _router
