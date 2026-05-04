# ============================================================
# Build stage — install deps, then copy only runtime artifacts
# ============================================================
FROM python:3.13-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir --prefix=/install -r requirements.txt

# ============================================================
# Runtime stage — only production files
# ============================================================
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/install/bin:$PATH"
ENV PYTHONPATH="/install/lib/python3.13/site-packages"

WORKDIR /app

# Copy installed deps from builder
COPY --from=builder /install /install

# Copy only needed source files
COPY app.py run_server.py start.py run_admin.py ./
COPY alembic/ alembic/
COPY alembic.ini ./
COPY database/ database/
COPY pipeline/ pipeline/
COPY routers/ routers/
COPY services/ services/
COPY tools/ tools/
COPY admin/__init__.py admin/deps.py admin/
COPY admin/routers/ admin/routers/
COPY scripts/docker_app_start.sh scripts/docker_admin_start.sh scripts/
COPY requirements.txt ./

# Force IPv4 DNS (Supabase IPv6 unreachable)
RUN echo "precedence ::ffff:0:0/96 100" > /etc/gai.conf

EXPOSE 8000

CMD ["sh", "scripts/docker_app_start.sh"]
