import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

new_css = """<style>
  @import url('https://fonts.googleapis.com/css2?family=Quicksand:wght@300;400;500;600;700&display=swap');

  :root {
    --bg: #f5f8fa;
    --surface: rgba(255, 255, 255, 0.65);
    --surface-2: rgba(255, 255, 255, 0.5);
    --border: rgba(255, 255, 255, 0.6);
    --text: #091a34;
    --text-dim: #1e3b61;
    --text-muted: #3a84b5;
    --accent: #112F5A;
    --accent-dim: #265A84;
    --red: #e63946;
  }

  * {
    font-family: 'Quicksand', -apple-system, BlinkMacSystemFont, system-ui, sans-serif;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
  }

  body {
    background: url('/static/bg.jpg') center center / cover no-repeat fixed;
    color: var(--text);
    overflow: hidden;
  }

  /* Overlay transparente e borrado sobre o fundo da lanchonete */
  .bg-gradient {
    position: fixed;
    inset: 0;
    background: rgba(245, 248, 250, 0.5); /* Textura leve em transparência */
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    z-index: -1;
  }

  /* Efeitos Bevel de Vidro da Apple */
  .apple-glass {
    background: var(--surface);
    backdrop-filter: blur(40px) saturate(200%);
    -webkit-backdrop-filter: blur(40px) saturate(200%);
    border: 1px solid var(--border);
    border-top: 1px solid rgba(255, 255, 255, 0.8);
    border-left: 1px solid rgba(255, 255, 255, 0.8);
    box-shadow: 
      inset 1px 1px 2px rgba(255, 255, 255, 0.9),
      inset -1px -1px 2px rgba(0, 0, 0, 0.05),
      0 10px 30px rgba(9, 26, 52, 0.15);
  }

  /* Aplicando o Bisel Apple no painel principal */
  .glass {
    background: var(--surface);
    backdrop-filter: blur(40px) saturate(200%);
    -webkit-backdrop-filter: blur(40px) saturate(200%);
    border: 1px solid var(--border);
    border-top: 1px solid rgba(255, 255, 255, 0.8);
    border-left: 1px solid rgba(255, 255, 255, 0.8);
    box-shadow: 
      inset 1px 1px 2px rgba(255, 255, 255, 0.9),
      inset -1px -1px 2px rgba(0, 0, 0, 0.05),
      0 10px 30px rgba(9, 26, 52, 0.15);
  }

  /* Scrollbar minimalista */
  ::-webkit-scrollbar { width: 6px; height: 6px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb {
    background: rgba(9, 26, 52, 0.15);
    border-radius: 3px;
  }
  ::-webkit-scrollbar-thumb:hover { background: rgba(9, 26, 52, 0.3); }

  /* Botão principal em Bisel de Vidro (Apple Style) */
  .btn-primary {
    background: linear-gradient(135deg, rgba(30, 59, 97, 0.95), rgba(9, 26, 52, 0.95));
    color: white;
    font-weight: 600;
    letter-spacing: -0.01em;
    padding: 14px 28px;
    border-radius: 20px;
    border: 1px solid rgba(255,255,255,0.2);
    border-top-color: rgba(255,255,255,0.4);
    box-shadow: 
      inset 0 1px 2px rgba(255,255,255,0.3), 
      inset 0 -1px 2px rgba(0,0,0,0.4),
      0 8px 16px rgba(9, 26, 52, 0.25);
    backdrop-filter: blur(10px);
    transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
  }
  .btn-primary:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: 
      inset 0 1px 2px rgba(255,255,255,0.4), 
      inset 0 -1px 2px rgba(0,0,0,0.4),
      0 12px 24px rgba(9, 26, 52, 0.3);
  }
  .btn-primary:active:not(:disabled) {
    transform: translateY(0);
  }
  .btn-primary:disabled { opacity: 0.4; cursor: not-allowed; }

  /* Botão secundário de Vidro */
  .btn-secondary {
    background: rgba(255,255,255,0.4);
    backdrop-filter: blur(10px);
    color: var(--text);
    padding: 10px 18px;
    border-radius: 20px;
    border: 1px solid rgba(255,255,255,0.7);
    border-bottom-color: rgba(0,0,0,0.05);
    box-shadow: 
      inset 0 1px 1px rgba(255,255,255,0.9), 
      0 2px 8px rgba(9, 26, 52, 0.05);
    transition: all 0.2s ease;
    font-weight: 600;
    font-size: 13px;
  }
  .btn-secondary:hover {
    background: rgba(255,255,255,0.6);
  }

  /* Input estilo vidro Apple */
  .input-apple {
    background: rgba(255, 255, 255, 0.7);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.8);
    border-bottom-color: rgba(9, 26, 52, 0.1);
    border-radius: 12px;
    padding: 11px 14px;
    color: var(--text);
    font-size: 15px;
    width: 100%;
    box-shadow: inset 0 2px 4px rgba(9, 26, 52, 0.02);
    transition: all 0.2s ease;
  }
  .input-apple:focus {
    outline: none;
    background: rgba(255, 255, 255, 0.95);
    border-color: rgba(17, 47, 90, 0.4);
    box-shadow: 
      inset 0 2px 4px rgba(9, 26, 52, 0.05),
      0 0 0 3px rgba(17, 47, 90, 0.15);
  }
  .input-apple::placeholder { color: var(--text-muted); }
  textarea.input-apple { resize: vertical; min-height: 80px; line-height: 1.5; }

  /* Label */
  .label-apple {
    font-size: 12px;
    font-weight: 600;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-bottom: 6px;
    display: block;
  }

  /* Card do agente Apple Glass */
  .agent-card {
    background: rgba(255,255,255,0.5);
    backdrop-filter: blur(20px);
    border: 1px solid rgba(255,255,255,0.6);
    border-top-color: rgba(255,255,255,0.9);
    border-left-color: rgba(255,255,255,0.9);
    border-radius: 14px;
    padding: 14px;
    transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
    position: relative;
    overflow: hidden;
    box-shadow: 
      inset 1px 1px 2px rgba(255,255,255,0.8),
      inset -1px -1px 2px rgba(0,0,0,0.02),
      0 6px 16px rgba(9,26,52,0.08);
  }
  .agent-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0;
    width: 4px;
    height: 100%;
    background: transparent;
    transition: all 0.3s ease;
  }
  .agent-card.waiting { opacity: 0.6; }
  .agent-card.active {
    background: rgba(58, 132, 181, 0.15);
    border-color: rgba(255,255,255,0.8);
  }
  .agent-card.active::before { background: var(--accent); }
  .agent-card.done {
    background: rgba(255,255,255,0.4);
  }
  .agent-card.done::before { background: var(--accent-dim); }

  /* Pulse animation */
  @keyframes pulse-dot {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.3; transform: scale(0.7); }
  }
  .pulse-dot { display: inline-block; width: 8px; height: 8px; background: var(--accent); border-radius: 50%; animation: pulse-dot 1.4s infinite; margin-right: 8px; }

  /* Log entry */
  @keyframes slide-in {
    from { opacity: 0; transform: translateX(-8px); }
    to { opacity: 1; transform: translateX(0); }
  }
  .log-entry {
    animation: slide-in 0.3s cubic-bezier(0.16, 1, 0.3, 1);
    padding: 8px 12px;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 500;
    line-height: 1.5;
    margin-bottom: 4px;
    background: rgba(255,255,255,0.6);
    border-left: 3px solid var(--border);
    box-shadow: inset 1px 1px 1px rgba(255,255,255,0.8), 0 2px 4px rgba(0,0,0,0.03);
  }
  .log-entry.progress { border-left-color: var(--accent); }
  .log-entry.error { border-left-color: var(--red); background: rgba(230, 57, 70, 0.1); }

  /* Progress bar */
  .progress-bar { background: rgba(9, 26, 52, 0.08); border-radius: 100px; height: 6px; overflow: hidden; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); }
  .progress-fill {
    background: linear-gradient(90deg, #112F5A 0%, #3a84b5 100%);
    height: 100%; border-radius: 100px; transition: width 0.6s cubic-bezier(0.16, 1, 0.3, 1); box-shadow: 0 0 8px rgba(58, 132, 181, 0.4);
  }

  /* Drop zone Apple Glass */
  .drop-zone {
    border: 1.5px dashed rgba(9, 26, 52, 0.3);
    border-radius: 16px;
    padding: 24px 16px;
    text-align: center;
    cursor: pointer;
    transition: all 0.25s ease;
    background: rgba(255,255,255,0.4);
    backdrop-filter: blur(10px);
    box-shadow: inset 1px 1px 2px rgba(255,255,255,0.7);
  }
  .drop-zone:hover, .drop-zone.drag-over {
    border-color: var(--accent);
    background: rgba(255,255,255,0.7);
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(9,26,52,0.1), inset 1px 1px 2px rgba(255,255,255,0.9);
  }

  /* Result table */
  .result-table { width: 100%; border-collapse: collapse; font-size: 13px; }
  .result-table th {
    background: rgba(255, 255, 255, 0.4);
    backdrop-filter: blur(8px);
    color: var(--text-dim);
    font-weight: 600;
    padding: 12px 14px;
    text-align: left;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    border-bottom: 2px solid rgba(9, 26, 52, 0.1);
  }
  .result-table td { padding: 12px 14px; border-bottom: 1px solid rgba(9, 26, 52, 0.08); color: var(--text); }
  .result-table tr:hover td { background: rgba(255,255,255,0.5); }

  .fade-in { animation: fadeIn 0.4s ease; }
  @keyframes fadeIn { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }

  .tab { padding: 12px 16px; font-size: 13px; font-weight: 600; color: var(--text-dim); cursor: pointer; border-bottom: 2px solid transparent; transition: all 0.2s ease; }
  .tab:hover { color: var(--text); }
  .tab.active { color: var(--accent); border-bottom-color: var(--accent); }

  input[type=number]::-webkit-inner-spin-button, input[type=number]::-webkit-outer-spin-button { -webkit-appearance: none; margin: 0; }
  .smooth-appear { animation: smoothAppear 0.5s cubic-bezier(0.16, 1, 0.3, 1); }
  @keyframes smoothAppear { from { opacity: 0; transform: scale(0.98); } to { opacity: 1; transform: scale(1); } }
</style>"""

text = re.sub(r'<style>.*?</style>', new_css, text, flags=re.DOTALL)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(text)

