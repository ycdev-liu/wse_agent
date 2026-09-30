#!/usr/bin/env bash
set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

PYTHON="$ROOT_DIR/runtime/python/bin/python3"
ENV_FILE="$ROOT_DIR/env.sh"

if [ ! -x "$PYTHON" ]; then
    echo "Portable Python runtime not found:"
    echo "$PYTHON"
    exit 1
fi

if [ ! -f "$ENV_FILE" ]; then
    echo "env.sh not found:"
    echo "$ENV_FILE"
    exit 1
fi

source "$ENV_FILE"

if [ -z "$ANTHROPIC_BASE_URL" ]; then
    echo "ANTHROPIC_BASE_URL is not set"
    exit 1
fi

if [ -z "$ANTHROPIC_AUTH_TOKEN" ]; then
    echo "ANTHROPIC_AUTH_TOKEN is not set"
    exit 1
fi

if [ -z "$ANTHROPIC_MODEL" ]; then
    echo "ANTHROPIC_MODEL is not set"
    exit 1
fi

exec "$PYTHON" "$ROOT_DIR/agent.py"
