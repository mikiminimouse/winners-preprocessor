#!/bin/bash

# Скрипт вызывается OpenVPN при поднятии туннеля (опция `up` в .ovpn)
# Задача: направить только zakupki.gov.ru через VPN-интерфейс ($dev),
# НЕ трогая default route и, соответственно, SSH.

set -euo pipefail

LOG_TAG="[vpn-route-up]"

DEV="${dev:-$1:-unset}"
echo "$LOG_TAG dev=${DEV}, script started" >&2 || true

# Хосты, которые должны идти через VPN.
# Можно расширять список/подсети по мере необходимости.
HOSTS=(
  "zakupki.gov.ru"
)

for host in "${HOSTS[@]}"; do
  # Разрешаем имя в один или несколько IP
  # getent более универсален, чем nslookup/host.
  IP_LIST=$(getent ahosts "$host" 2>/dev/null | awk '{print $1}' | sort -u || true)

  if [[ -z "$IP_LIST" ]]; then
    echo "$LOG_TAG failed to resolve $host" >&2 || true
    continue
  fi

  for ip in $IP_LIST; do
    # Прописываем маршрут /32 на каждый IP через интерфейс VPN.
    # НЕ меняем default route, только конкретные адреса.
    echo "$LOG_TAG adding route $ip/32 via dev $DEV" >&2 || true
    ip route replace "$ip/32" dev "$DEV" metric 100 2>/dev/null || true
  done
done

echo "$LOG_TAG done" >&2 || true


