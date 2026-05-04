try:
    import openai
    print(f"OpenAI OK ({openai.__version__})")
except Exception as e:
    print(f"OpenAI error: {e}")

try:
    import anthropic
    print(f"Anthropic OK ({anthropic.__version__})")
except Exception as e:
    print(f"Anthropic error: {e}")

try:
    from importlib.metadata import version
    import litellm
    print(f"LiteLLM OK ({version('litellm')})")
except Exception as e:
    print(f"LiteLLM error: {e}")

try:
from pipeline.orchestrator import MenuOrchestrator
from pipeline.litellm_runner import run_lite_pipeline
    print("Pipeline LiteLLM OK")
except Exception as e:
    print(f"Pipeline error: {e}")

try:
    import httpcore
    from httpcore._async.connection_pool import AsyncConnectionPool
    print("AsyncConnectionPool OK")
except Exception as e:
    print(f"httpcore error: {e}")
