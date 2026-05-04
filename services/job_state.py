"""Estado em memória dos jobs SSE (pode ser reidratado a partir de JobAgente após restart)."""
import queue
from typing import Any, Dict

jobs: Dict[str, Dict[str, Any]] = {}
job_queues: Dict[str, "queue.Queue"] = {}
