import json
import logging
from openai import OpenAI
from app.config import settings
from app.models import RoutingResponse

logger = logging.getLogger(__name__)

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
        1. Use GPT-5-mini to classify intent
        2. Route to appropriate model based on intent
        """
        
        try:
            # Step 1: Classify intent using GPT-5-mini
            intent_classification = await self._classify_intent(prompt)
            
            # Step 2: Route based on intent
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

    async def _classify_intent(self, prompt: str) -> dict:
        """
        Classify prompt intent:
        - Translation → DeepSeek (fast, cheap)
        - Simple/Summary → DeepSeek
        - Complex/Reasoning → GPT-5-Pro
        """
        
        classification_prompt = f"""Analyze this user prompt and classify it.
        
Prompt: "{prompt}"

Respond in JSON format:
{{
  "intent": "translation|summary|simple|complex|reasoning",
  "confidence": 0.0-1.0,
  "requires_deep_reasoning": true/false
}}

Rules:
- Translation tasks: always DeepSeek
- Simple factual questions: DeepSeek
- Summaries: DeepSeek
- Complex reasoning, analysis, creative work: GPT-5-Pro
- Code generation with explanation: GPT-5-Pro
- Math/logic problems: GPT-5-Pro

Return ONLY valid JSON."""

        try:
            response = self.client.chat.completions.create(
                model=self.router_model,
                messages=[{"role": "user", "content": classification_prompt}],
                max_completion_tokens=150
            )
            
            classification_text = response.choices[0].message.content
            classification = json.loads(classification_text)
            
            should_use_reasoning = classification.get("requires_deep_reasoning", False)
            intent = classification.get("intent", "simple")
            
            reason_map = {
                "translation": "Translation task → DeepSeek",
                "summary": "Summary task → DeepSeek",
                "simple": "Simple query → DeepSeek",
                "complex": "Complex reasoning → GPT-5-Pro",
                "reasoning": "Reasoning task → GPT-5-Pro"
            }
            
            reason = reason_map.get(intent, "Classifier routed to DeepSeek")
            
            return {
                "should_use_reasoning": should_use_reasoning,
                "reason": reason,
                "intent": intent
            }
            
        except Exception as e:
            logger.warning(f"Classification error, defaulting to DeepSeek: {e}")
            return {
                "should_use_reasoning": False,
                "reason": "Classification fallback → DeepSeek",
                "intent": "simple"
            }

    async def _call_deepseek_model(self, prompt: str, messages: list = None) -> str:
        """Call DeepSeek-V4-Flash model"""
        
        message_list = messages or []
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
        
        message_list = messages or []
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

# Global router instance
_router = None

def get_router() -> ModelRouter:
    global _router
    if _router is None:
        _router = ModelRouter()
    return _router
