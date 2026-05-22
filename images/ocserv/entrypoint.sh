#!/bin/sh
set -eu

netmask_to_prefix() {
    mask="$1"
    bits=0
    OLD_IFS="$IFS"
    IFS=.
    set -- $mask
    IFS="$OLD_IFS"
    for octet in "$@"; do
        case "$octet" in
            255) bits=$((bits + 8)) ;;
            254) bits=$((bits + 7)) ;;
            252) bits=$((bits + 6)) ;;
            248) bits=$((bits + 5)) ;;
            240) bits=$((bits + 4)) ;;
            224) bits=$((bits + 3)) ;;
            192) bits=$((bits + 2)) ;;
            128) bits=$((bits + 1)) ;;
            0) ;;
            *) echo "Unsupported netmask: $mask" >&2; exit 1 ;;
        esac
    done
    echo "$bits"
}

require_file() {
    path="$1"
    until [ -f "$path" ]; do
        echo "waiting for $path"
        sleep 2
    done
}

mkdir -p /etc/ocserv /etc/radiusclient /var/run
mkdir -p "${LOG_DIR_ROOT}/ocserv"
touch "${LOG_DIR_ROOT}/ocserv/ocserv.log" "${LOG_DIR_ROOT}/ocserv/error.log" "${LOG_DIR_ROOT}/ocserv/supervisord.log"

require_file /srv/pki/server/server-cert.pem
require_file /srv/pki/server/server-key.pem

cp /opt/wormhole/ocserv.conf.template /etc/ocserv/ocserv.conf
cp /opt/wormhole/radiusclient.conf.template /etc/radiusclient/radiusclient.conf
cp /opt/wormhole/servers.template /etc/radiusclient/servers

sed -i "s/__RADIUS_SHARED_SECRET__/${RADIUS_SHARED_SECRET}/g" /etc/radiusclient/servers
sed -i "s/__OCSERV_RADIUS_HOST__/${OCSERV_RADIUS_HOST}/g" /etc/radiusclient/radiusclient.conf
sed -i "s/__OCSERV_RADIUS_AUTH_PORT__/${OCSERV_RADIUS_AUTH_PORT}/g" /etc/radiusclient/radiusclient.conf
sed -i "s/__OCSERV_RADIUS_ACCT_PORT__/${OCSERV_RADIUS_ACCT_PORT}/g" /etc/radiusclient/radiusclient.conf
sed -i "s/__OCSERV_NAS_IDENTIFIER__/${OCSERV_NAS_IDENTIFIER}/g" /etc/ocserv/ocserv.conf
sed -i "s/__OCSERV_TCP_PORT__/${OCSERV_TCP_PORT}/g" /etc/ocserv/ocserv.conf
sed -i "s/__OCSERV_UDP_PORT__/${OCSERV_UDP_PORT}/g" /etc/ocserv/ocserv.conf
sed -i "s/__OCSERV_NETWORK__/${OCSERV_NETWORK}/g" /etc/ocserv/ocserv.conf
sed -i "s/__OCSERV_NETMASK__/${OCSERV_NETMASK}/g" /etc/ocserv/ocserv.conf
sed -i "s/__OCSERV_MAX_CLIENTS__/${OCSERV_MAX_CLIENTS}/g" /etc/ocserv/ocserv.conf
sed -i "s/__OCSERV_MAX_SAME_CLIENTS__/${OCSERV_MAX_SAME_CLIENTS}/g" /etc/ocserv/ocserv.conf
sed -i "s/__OCSERV_DNS_1__/${OCSERV_DNS_1}/g" /etc/ocserv/ocserv.conf
sed -i "s/__OCSERV_DNS_2__/${OCSERV_DNS_2}/g" /etc/ocserv/ocserv.conf
sed -i "s/__OCSERV_IDLE_TIMEOUT__/${OCSERV_IDLE_TIMEOUT}/g" /etc/ocserv/ocserv.conf
sed -i "s/__OCSERV_MOBILE_IDLE_TIMEOUT__/${OCSERV_MOBILE_IDLE_TIMEOUT}/g" /etc/ocserv/ocserv.conf
sed -i "s/__OCSERV_SESSION_TIMEOUT__/${OCSERV_SESSION_TIMEOUT}/g" /etc/ocserv/ocserv.conf
sed -i "s/__OCSERV_STATS_REPORT_TIME__/${OCSERV_STATS_REPORT_TIME}/g" /etc/ocserv/ocserv.conf
sed -i "s/__OCSERV_DEFAULT_DOMAIN__/${OCSERV_DEFAULT_DOMAIN}/g" /etc/ocserv/ocserv.conf

if [ -z "${OCSERV_DEFAULT_DOMAIN}" ]; then
    sed -i '/^default-domain = /d' /etc/ocserv/ocserv.conf
fi

cidr="$(netmask_to_prefix "${OCSERV_NETMASK}")"
iptables -t nat -C POSTROUTING -s "${OCSERV_NETWORK}/${cidr}" -o "${OCSERV_NAT_DEVICE}" -j MASQUERADE 2>/dev/null || \
    iptables -t nat -A POSTROUTING -s "${OCSERV_NETWORK}/${cidr}" -o "${OCSERV_NAT_DEVICE}" -j MASQUERADE
iptables -C FORWARD -i vpns -o "${OCSERV_NAT_DEVICE}" -j ACCEPT 2>/dev/null || \
    iptables -A FORWARD -i vpns -o "${OCSERV_NAT_DEVICE}" -j ACCEPT
iptables -C FORWARD -i "${OCSERV_NAT_DEVICE}" -o vpns -m state --state RELATED,ESTABLISHED -j ACCEPT 2>/dev/null || \
    iptables -A FORWARD -i "${OCSERV_NAT_DEVICE}" -o vpns -m state --state RELATED,ESTABLISHED -j ACCEPT

exec /usr/bin/supervisord -c /opt/wormhole/supervisord.conf
