import re

# 1. Patch app.py
with open('app.py', 'r', encoding='utf-8') as f:
    app_py = f.read()

step_callback_code = """
        def on_step_complete(step, **kwargs):
            text = ""
            if hasattr(step, "thought") and step.thought:
                text = step.thought
            elif hasattr(step, "log") and step.log:
                text = step.log
            elif isinstance(step, tuple) and len(step) > 0 and hasattr(step[0], "log"):
                text = step[0].log
            else:
                text = str(step)
            
            if text:
                import re as regex
                text = regex.sub(r'\\x1B(?:[@-Z\\\\-_]|\\\\[[0-?]*[ -/]*[@-~])', '', text)
                preview = text[:200].replace("\\n", " ").strip()
                if preview:
                    emit("agent_thought", thought=preview)

        progress(15, "🏁 Orquestrando agentes...", "Coordenador")

        from pipeline.orchestrator import MenuOrchestrator

        crew = MenuOrchestrator(
            contrato_path=contrato_path,
            dias=dias,
            target_custo_total=target_custo_total,
            target_custo_proteico=target_custo_proteico,
            restricoes_usuario=restricoes_usuario,
            empresa_id=empresa_id,
            contrato_id=contrato_id,
            task_callback=on_task_complete,
            step_callback=on_step_complete,
            db_disponivel=db_ok,
        )
"""
app_py = re.sub(r'progress\(15, "🏁 Orquestrando agentes\.\.\.", "Coordenador"\)\s+from pipeline\.orchestrator import MenuOrchestrator\s+crew = MenuOrchestrator\((.*?)\)', step_callback_code, app_py, flags=re.DOTALL)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(app_py)

# 2. Patch cardapio_crew.py
with open('crew/cardapio_crew.py', 'r', encoding='utf-8') as f:
    crew_py = f.read()

crew_py = crew_py.replace("verbose=True,", "verbose=True,\n            step_callback=self.step_callback,")

with open('crew/cardapio_crew.py', 'w', encoding='utf-8') as f:
    f.write(crew_py)

# 3. Patch index.html
with open('templates/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

js_patch = """      case 'agent_thought':
        const card = document.querySelector('.agent-card.active');
        if (card) {
          const p = card.querySelector('.agent-preview');
          p.textContent = "🧠 " + msg.thought + "…";
          p.classList.remove('hidden');
        }
        break;
      case 'agents_ready':"""

html = html.replace("case 'agents_ready':", js_patch)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(html)
