#!/bin/bash

# Скрипт для запуска бота
# Использование:
#   ./start.sh          # Запуск в обычном режиме
#   ./start.sh debug    # Запуск в режиме отладки

uv sync

if [ "$1" = "debug" ]; then
    echo "Запуск бота в режиме отладки..."
    uv run python -m app.main --debug
else
    echo "Запуск бота в обычном режиме..."
    uv run python -m app.main
fi