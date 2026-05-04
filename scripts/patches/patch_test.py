import re
with open('app.py', 'r') as f:
    content = f.read()

# I will add a print to the step callback to see what is going on
new_callback = """
        def on_step_complete(step, **kwargs):
            import re as regex
            print(f"STEP CALLBACK CALLED! Type: {type(step)}")
            try:
                text = ""
                if hasattr(step, "thought") and step.thought:
                    text = step.thought
                elif hasattr(step, "log") and step.log:
                    text = step.log
                elif hasattr(step, "text") and step.text:
                    text = step.text
                elif isinstance(step, tuple) and len(step) > 0 and hasattr(step[0], "log"):
                    text = step[0].log
                else:
                    text = str(step)
                
                print(f"TEXT EXTRACTED: {len(text)} chars")
                if text:
                    text = regex.sub(r'\\x1B(?:[@-Z\\\\-_]|\\\\[[0-?]*[ -/]*[@-~])', '', text)
                    preview = text[:5000].strip() # Do NOT remove newlines
                    if preview:
                        agent_name = kwargs.get("agent_name", "")
                        print(f"EMITTING THOUGHT FOR {agent_name}")
                        emit("agent_thought", thought=preview, agent=agent_name)
            except Exception as e:
                print(f"ERROR IN STEP CALLBACK: {e}")
"""

content = re.sub(r'def on_step_complete\(step, \*\*kwargs\):.*?emit\("agent_thought", thought=preview, agent=agent_name\)', new_callback.strip(), content, flags=re.DOTALL)

with open('app.py', 'w') as f:
    f.write(content)
