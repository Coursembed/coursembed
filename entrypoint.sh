#!/bin/sh
exec /app/.venv/bin/python -m uvicorn app:app --host 0.0.0.0 --port ${SERVER_PORT} --reload --reload-dir .
