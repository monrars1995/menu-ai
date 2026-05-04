"""
Menu.AI — Compatibilidade do decorator @tool

LangChain (langchain_core.tools.StructuredTool) é o path principal.
Fallback: SimpleTool puro Python para ambientes sem langchain-core.

Uso (idêntico ao decorator antigo):

    from tools.compat import tool

    @tool("Nome da Ferramenta")
    def minha_ferramenta(parametro: str) -> str:
        \"\"\"Descrição da ferramenta usada pelo LLM.\"\"\"
        return f"resultado: {parametro}"
"""
import inspect
import re
from typing import Any, Callable, Optional, Type


def _make_tool(name: str, func: Callable) -> Any:
    """
    Envolve uma função Python numa ferramenta com schema.
    LangChain preferido; SimpleTool como fallback sem dependências externas.
    """
    # ── Preferência: LangChain (LiteLLM + function calling) ───────────
    try:
        from langchain_core.tools import StructuredTool
        tool_name = re.sub(r"\s+", "_", name)[:64] or "tool"
        doc = inspect.getdoc(func) or ""
        return StructuredTool.from_function(
            name=tool_name,
            description=doc,
            func=func,
        )
    except (ImportError, Exception):
        pass

    # ── Fallback: wrapper simples (sem dependências externas) ─────────
    class SimpleTool:
        """Wrapper mínimo para uso sem langchain-core instalado."""
        def __init__(self, fn: Callable, tool_name: str):
            self.func = fn
            self.name = tool_name
            self.description = inspect.getdoc(fn) or ""

        def __call__(self, *args, **kwargs):
            return self.func(*args, **kwargs)

        def run(self, *args, **kwargs):
            return self.func(*args, **kwargs)

        def _run(self, *args, **kwargs):
            return self.func(*args, **kwargs)

    return SimpleTool(func, name)


def tool(name_or_func):
    """
    Decorator @tool com LangChain primário e SimpleTool fallback.

    Uso:
        @tool("Nome da Ferramenta")
        def minha_func(param: str) -> str:
            \"\"\"Descrição.\"\"\"
            ...

        # Ou sem nome (usa o nome da função):
        @tool
        def minha_func(param: str) -> str:
            ...
    """
    if isinstance(name_or_func, str):
        tool_name = name_or_func
        def decorator(func: Callable):
            return _make_tool(tool_name, func)
        return decorator

    func = name_or_func
    tool_name = func.__name__.replace("_", " ").title()
    return _make_tool(tool_name, func)
