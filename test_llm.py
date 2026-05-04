from pipeline.llm_litellm import get_litellm_config

try:
    cfg = get_litellm_config("queen-3.6")
    print(f"OpenRouter config OK: {cfg.model}")
except Exception as e:
    print(f"OpenRouter config error: {e}")

print("Finished!")
