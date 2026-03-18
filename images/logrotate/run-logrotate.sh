#!/bin/sh
set -eu

mkdir -p /etc/logrotate.d "${LOG_DIR_ROOT}"
envsubst '${LOG_DIR_ROOT} ${LOG_RETENTION_DAYS}' < /etc/logrotate.conf.template > /etc/logrotate.d/wormhole

while true; do
    logrotate -v /etc/logrotate.d/wormhole || true
    sleep 86400
done

