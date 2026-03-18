#!/bin/sh
set -eu

if [ ! -f .env ]; then
    echo ".env is required" >&2
    exit 1
fi

env_value() {
    python3 - "$1" <<'PY'
import sys
key = sys.argv[1]
with open(".env", "r", encoding="utf-8") as handle:
    for line in handle:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        left, right = line.split("=", 1)
        if left == key:
            print(right)
            break
PY
}

ADMIN_PORTAL_PORT="$(env_value ADMIN_PORTAL_PORT)"
MARIADB_ROOT_PASSWORD="$(env_value MARIADB_ROOT_PASSWORD)"
MARIADB_DATABASE="$(env_value MARIADB_DATABASE)"
RADIUS_SHARED_SECRET="$(env_value RADIUS_SHARED_SECRET)"

docker compose --env-file .env ps

python3 - <<'PY'
import os
import urllib.request

target = f"http://127.0.0.1:{os.environ['ADMIN_PORTAL_PORT']}/healthz"
with urllib.request.urlopen(target, timeout=5) as response:
    if response.status != 200:
        raise SystemExit(f"health check failed: {target} -> {response.status}")
print("admin portal health check passed")
PY

docker compose --env-file .env exec -T ca-api python - <<'PY'
import urllib.request
with urllib.request.urlopen("http://127.0.0.1:9000/healthz", timeout=5) as response:
    if response.status != 200:
        raise SystemExit(response.status)
print("ca-api health check passed")
PY

docker compose --env-file .env exec -T db mariadb \
  -u root -p"${MARIADB_ROOT_PASSWORD}" "${MARIADB_DATABASE}" <<'SQL'
DELETE FROM radcheck WHERE username = 'local-smoke';
INSERT INTO radcheck (username, attribute, op, value) VALUES
  ('local-smoke', 'Cleartext-Password', ':=', 'local-smoke'),
  ('local-smoke', 'Expiration', ':=', '31 Dec 2099 23:59:59 UTC');
SQL

docker compose --env-file .env exec -T freeradius radtest local-smoke local-smoke 127.0.0.1 0 "${RADIUS_SHARED_SECRET}" | tee /tmp/wormhole-local-smoke.out

if ! grep -q "Access-Accept" /tmp/wormhole-local-smoke.out; then
  echo "radtest failed" >&2
  exit 1
fi

rm -f /tmp/wormhole-local-smoke.out
echo "radius smoke passed"
