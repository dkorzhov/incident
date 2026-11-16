FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# DMI-12: кэши тестов/линта — в /tmp, а не рядом с кодом. Иначе прогон в
# контейнере с bind-mount (`docker run -v "$PWD/backend:/app" ...`) оставляет
# в worktree каталоги, принадлежащие root, и `git worktree remove` /
# `orca worktree rm` после мержа падают с Permission denied (нужен sudo).
# Значения можно переопределить при запуске: `-e RUFF_CACHE_DIR=...`.
ENV RUFF_CACHE_DIR=/tmp/ruff-cache \
    PYTEST_ADDOPTS="-o cache_dir=/tmp/pytest-cache" \
    HOME=/tmp

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod +x entrypoint.sh

EXPOSE 8000

CMD ["./entrypoint.sh"]