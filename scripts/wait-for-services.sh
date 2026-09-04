#!/usr/bin/env sh
set -eu

for url in http://127.0.0.1:8000/health/ready http://127.0.0.1:3000 http://127.0.0.1:3001/overview; do
  i=0
  until curl -fsS "$url" >/dev/null 2>&1; do
    i=$((i + 1))
    if [ "$i" -gt 60 ]; then
      echo "Timed out waiting for $url" >&2
      exit 1
    fi
    sleep 2
  done
  echo "Ready: $url"
done
