#!/bin/bash
echo "Остановка WebUI..."
pkill -f "receiver.*webui" || pkill -f "python.*receiver.webui"
sleep 2
echo "Запуск WebUI..."
cd /root/winners_preprocessor
nohup python3 -m receiver.webui.app > /tmp/webui.log 2>&1 &
PID=$!
sleep 3
if ps -p $PID > /dev/null; then
    echo "✅ WebUI перезапущен"
    echo "PID: $PID"
    echo "URL: http://localhost:7860"
    echo "Логи: tail -f /tmp/webui.log"
else
    echo "❌ Ошибка при запуске WebUI"
    tail -20 /tmp/webui.log
fi
