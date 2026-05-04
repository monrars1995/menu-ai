import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Trocar a fonte e variáveis CSS
new_css = """<style>
  @import url('https://fonts.googleapis.com/css2?family=Quicksand:wght@300;400;500;600;700&display=swap');

  :root {
    --bg: #f5f8fa;
    --surface: rgba(255, 255, 255, 0.85);
    --surface-2: rgba(255, 255, 255, 0.6);
    --border: rgba(9, 26, 52, 0.1);
    --text: #091a34;
    --text-dim: #1e3b61;
    --text-muted: #3a84b5;
    --accent: #112F5A;
    --accent-dim: #265A84;
    --blue: #0a84ff;
    --orange: #ff9f0a;
    --red: #e63946;
  }

  * {
    font-family: 'Quicksand', -apple-system, BlinkMacSystemFont, system-ui, sans-serif;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
  }

  body {
    background: var(--bg);
    color: var(--text);
    overflow: hidden;
  }

  /* Gradiente de fundo sutil para imitar o Sabor Seguro */
  .bg-gradient {
    position: fixed;
    inset: 0;
    background:
      radial-gradient(circle at 10% 20%, rgba(58, 132, 181, 0.05) 0%, transparent 40%),
      radial-gradient(circle at 90% 80%, rgba(9, 26, 52, 0.03) 0%, transparent 40%),
      linear-gradient(135deg, #ffffff 0%, #f0f4f8 100%);
    z-index: -1;
  }

  /* Glassmorphism Claro */
  .glass {
    background: var(--surface);
    backdrop-filter: blur(24px) saturate(180%);
    -webkit-backdrop-filter: blur(24px) saturate(180%);
    border: 1px solid var(--border);
    box-shadow: 0 4px 24px rgba(9, 26, 52, 0.03);
  }

  /* Scrollbar minimalista */
  ::-webkit-scrollbar { width: 6px; height: 6px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb {
    background: rgba(9, 26, 52, 0.15);
    border-radius: 3px;
  }
  ::-webkit-scrollbar-thumb:hover { background: rgba(9, 26, 52, 0.3); }

  /* Botão principal Sabor Seguro */
  .btn-primary {
    background: linear-gradient(180deg, #1e3b61 0%, #091a34 100%);
    color: white;
    font-weight: 600;
    letter-spacing: -0.01em;
    padding: 14px 28px;
    border-radius: 20px;
    box-shadow: 0 2px 4px rgba(9, 26, 52, 0.2);
    transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
  }
  .btn-primary:hover:not(:disabled) {
    transform: translateY(-1px);
    box-shadow: 0 6px 16px rgba(9, 26, 52, 0.3);
  }
  .btn-primary:active:not(:disabled) {
    transform: translateY(0);
  }
  .btn-primary:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }

  .btn-secondary {
    background: transparent;
    color: var(--text);
    padding: 10px 18px;
    border-radius: 20px;
    border: 1px solid var(--border);
    transition: all 0.2s ease;
    font-weight: 600;
    font-size: 13px;
  }
  .btn-secondary:hover {
    background: rgba(9, 26, 52, 0.05);
    border-color: rgba(9, 26, 52, 0.2);
  }

  /* Input estilo iOS adaptado */
  .input-apple {
    background: rgba(255, 255, 255, 0.6);
    border: 1px solid rgba(9, 26, 52, 0.15);
    border-radius: 12px;
    padding: 11px 14px;
    color: var(--text);
    font-size: 15px;
    width: 100%;
    transition: all 0.15s ease;
  }
  .input-apple:focus {
    outline: none;
    border-color: var(--accent);
    box-shadow: 0 0 0 3px rgba(17, 47, 90, 0.15);
    background: rgba(255, 255, 255, 0.9);
  }
  .input-apple::placeholder {
    color: var(--text-muted);
  }

  textarea.input-apple {
    resize: vertical;
    min-height: 80px;
    line-height: 1.5;
  }

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

  /* Card do agente */
  .agent-card {
    background: var(--surface-2);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 14px;
    transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
    position: relative;
    overflow: hidden;
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
  .agent-card.waiting {
    opacity: 0.6;
  }
  .agent-card.active {
    border-color: rgba(58, 132, 181, 0.5);
    background: rgba(58, 132, 181, 0.08);
  }
  .agent-card.active::before { background: var(--accent); }
  .agent-card.done {
    border-color: rgba(58, 132, 181, 0.2);
    background: rgba(58, 132, 181, 0.03);
  }
  .agent-card.done::before { background: var(--accent-dim); }

  /* Pulse animation */
  @keyframes pulse-dot {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.3; transform: scale(0.7); }
  }
  .pulse-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    background: var(--accent);
    border-radius: 50%;
    animation: pulse-dot 1.4s infinite;
    margin-right: 8px;
  }

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
    background: rgba(255,255,255,0.5);
    border-left: 3px solid var(--border);
  }
  .log-entry.progress { border-left-color: var(--accent); }
  .log-entry.error { border-left-color: var(--red); background: rgba(230, 57, 70, 0.1); }

  /* Progress bar */
  .progress-bar {
    background: rgba(9, 26, 52, 0.08);
    border-radius: 100px;
    height: 6px;
    overflow: hidden;
  }
  .progress-fill {
    background: linear-gradient(90deg, #112F5A 0%, #3a84b5 100%);
    height: 100%;
    border-radius: 100px;
    transition: width 0.6s cubic-bezier(0.16, 1, 0.3, 1);
    box-shadow: 0 0 8px rgba(58, 132, 181, 0.4);
  }

  /* Drop zone */
  .drop-zone {
    border: 1.5px dashed rgba(9, 26, 52, 0.2);
    border-radius: 12px;
    padding: 24px 16px;
    text-align: center;
    cursor: pointer;
    transition: all 0.25s ease;
    background: rgba(255,255,255,0.4);
  }
  .drop-zone:hover, .drop-zone.drag-over {
    border-color: var(--accent);
    background: rgba(58, 132, 181, 0.1);
    transform: translateY(-1px);
  }

  /* Result table */
  .result-table { width: 100%; border-collapse: collapse; font-size: 13px; }
  .result-table th {
    background: rgba(9, 26, 52, 0.03);
    color: var(--text-dim);
    font-weight: 600;
    padding: 12px 14px;
    text-align: left;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    border-bottom: 2px solid var(--border);
  }
  .result-table td {
    padding: 12px 14px;
    border-bottom: 1px solid rgba(9, 26, 52, 0.05);
    color: var(--text);
  }
  .result-table tr:hover td { background: rgba(9, 26, 52, 0.02); }

  /* Fade transitions */
  .fade-in { animation: fadeIn 0.4s ease; }
  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(6px); }
    to { opacity: 1; transform: translateY(0); }
  }

  /* Tabs */
  .tab {
    padding: 12px 16px;
    font-size: 13px;
    font-weight: 600;
    color: var(--text-dim);
    cursor: pointer;
    border-bottom: 2px solid transparent;
    transition: all 0.2s ease;
  }
  .tab:hover { color: var(--text); }
  .tab.active {
    color: var(--accent);
    border-bottom-color: var(--accent);
  }

  /* Number input */
  input[type=number]::-webkit-inner-spin-button,
  input[type=number]::-webkit-outer-spin-button {
    -webkit-appearance: none;
    margin: 0;
  }

  /* Animação suave */
  .smooth-appear {
    animation: smoothAppear 0.5s cubic-bezier(0.16, 1, 0.3, 1);
  }
  @keyframes smoothAppear {
    from { opacity: 0; transform: scale(0.98); }
    to { opacity: 1; transform: scale(1); }
  }
</style>"""

text = re.sub(r'<style>.*?</style>', new_css, text, flags=re.DOTALL)

new_header = """<header class="glass border-b flex items-center justify-between px-6 py-4" style="border-color: var(--border);">
  <div class="flex items-center gap-4">
    <img src="/static/logo.png" alt="Grupo Lemos Passos" class="h-10 w-auto" onerror="this.src='data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI0MCIgaGVpZ2h0PSI0MCIgdmlld0JveD0iMCAwIDQwIDQwIj48Y2lyY2xlIGN4PSIyMCIgY3k9IjIwIiByPSIyMCIgZmlsbD0iIzA5MWEzNCIvPjx0ZXh0IHg9IjIwIiB5PSIyNSIgZm9udC1mYW1pbHk9InNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMjQiIGZpbGw9IiNmZmYiIHRleHQtYW5jaG9yPSJtaWRkbGUiPkw8L3RleHQ+PC9zdmc+'" />
    <div class="h-6 w-px bg-gray-300"></div>
    <div>
      <h1 class="text-xl font-bold tracking-tight" style="color: var(--accent);">Sabor Seguro</h1>
      <p class="text-xs font-medium" style="color: var(--text-dim);">Planejamento inteligente de cardápios</p>
    </div>
  </div>
  <div class="flex items-center gap-3">
    <div id="statusBadge" class="hidden px-3 py-1 rounded-full text-xs font-semibold"></div>
    <span id="baseInfo" class="text-xs font-medium" style="color: var(--text-muted);">Carregando…</span>
  </div>
</header>"""

text = re.sub(r'<header.*?</header>', new_header, text, flags=re.DOTALL)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(text)

