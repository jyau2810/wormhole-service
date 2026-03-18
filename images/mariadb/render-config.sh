#!/bin/sh
set -eu

mkdir -p "${LOG_DIR_ROOT}/mariadb" /etc/mysql/conf.d
touch "${LOG_DIR_ROOT}/mariadb/error.log" "${LOG_DIR_ROOT}/mariadb/slow.log"
MYSQL_SLOW_LOG_THRESHOLD_SECONDS="$(awk "BEGIN { printf \"%.3f\", ${MYSQL_SLOW_LOG_THRESHOLD_MS} / 1000 }")"
export MYSQL_SLOW_LOG_THRESHOLD_SECONDS
envsubst < /opt/wormhole/logging.cnf.template > /etc/mysql/conf.d/90-wormhole-logging.cnf

exec docker-entrypoint.sh mysqld
