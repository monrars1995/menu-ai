import traceback
from pipeline.llm_litellm import get_litellm_config

try:
    cfg = get_litellm_config("glm-5-1")
    print(f"OpenRouter initialized successfully: {cfg.model}")
except Exception as e:
    print(f"Error initializing OpenRouter config: {e}")
    traceback.print_exc()
