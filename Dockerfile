ARG PYTHON_BASE=3.12-slim-bookworm

FROM python:$PYTHON_BASE AS builder

RUN pip install -U pdm

ENV PDM_CHECK_UPDATE=false

COPY pyproject.toml pdm.lock /app/
COPY src/ /app/src

WORKDIR /app

RUN pdm install --check --prod --no-editable

FROM python:$PYTHON_BASE

COPY --from=builder /app/.venv/ /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

ENV PYTHONPATH="/app/src"

COPY src /app/src
COPY entrypoint.sh /app/entrypoint.sh

WORKDIR /app

RUN chmod +x entrypoint.sh

CMD ["sh", "-c", "./entrypoint.sh"]
