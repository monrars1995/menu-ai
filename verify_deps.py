import sys
import traceback

def check_imports():
    modules = [
        "fastapi", "uvicorn", "pydantic", "litellm",
        "langchain_core", "slowapi", "pandas", "numpy", "openpyxl",
    ]
    failed = []
    for m in modules:
        try:
            __import__(m)
        except Exception as e:
            failed.append((m, e))
            print(f"FAILED IMPORT: {m} -> {e}")
            traceback.print_exc()

    try:
        from pipeline.orchestrator import MenuOrchestrator
        _ = MenuOrchestrator  # fachada de pipeline; execução via litellm_runner
        print("MenuOrchestrator / pipeline OK")
    except ImportError as e:
        failed.append(("MenuOrchestrator", e))
        print(f"FAILED MenuOrchestrator: {e}")
        traceback.print_exc()

    if failed:
        sys.exit(1)
    else:
        print("TODAS AS DEPENDENCIAS IMPORTADAS COM SUCESSO!")

check_imports()
