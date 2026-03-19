#!/bin/sh
set -eu

if [ -d /etc/raddb ]; then
    RADIUS_ETC="/etc/raddb"
elif [ -d /etc/freeradius/3.0 ]; then
    RADIUS_ETC="/etc/freeradius/3.0"
else
    RADIUS_ETC="/etc/raddb"
fi

mkdir -p "${RADIUS_ETC}/mods-enabled" "${RADIUS_ETC}/mods-config/sql/main/mysql" "${RADIUS_ETC}/sites-enabled"
mkdir -p "${LOG_DIR_ROOT}/freeradius"
touch "${LOG_DIR_ROOT}/freeradius/freeradius.log"

envsubst '${RADIUS_SHARED_SECRET}' < /opt/wormhole/clients.conf.template > "${RADIUS_ETC}/clients.conf"
envsubst '${RADIUS_DB_HOST} ${RADIUS_DB_PORT} ${RADIUS_DB_USER} ${RADIUS_DB_PASSWORD} ${RADIUS_DB_NAME}' \
    < /opt/wormhole/sql.template > "${RADIUS_ETC}/mods-enabled/sql"
cp /opt/wormhole/queries.conf "${RADIUS_ETC}/mods-config/sql/main/mysql/queries.conf"
cp /opt/wormhole/default "${RADIUS_ETC}/sites-enabled/default"
cp /opt/wormhole/inner-tunnel "${RADIUS_ETC}/sites-enabled/inner-tunnel"

[ -e "${RADIUS_ETC}/mods-enabled/expiration" ] || ln -sf ../mods-available/expiration "${RADIUS_ETC}/mods-enabled/expiration"
[ -e "${RADIUS_ETC}/mods-enabled/pap" ] || ln -sf ../mods-available/pap "${RADIUS_ETC}/mods-enabled/pap"
[ -e "${RADIUS_ETC}/mods-enabled/chap" ] || ln -sf ../mods-available/chap "${RADIUS_ETC}/mods-enabled/chap"
[ -e "${RADIUS_ETC}/mods-enabled/mschap" ] || ln -sf ../mods-available/mschap "${RADIUS_ETC}/mods-enabled/mschap"

if command -v freeradius >/dev/null 2>&1; then
    exec sh -c "freeradius -f >> '${LOG_DIR_ROOT}/freeradius/freeradius.log' 2>&1"
fi

exec sh -c "radiusd -f >> '${LOG_DIR_ROOT}/freeradius/freeradius.log' 2>&1"
