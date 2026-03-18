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

mkdir -p /etc/ocserv /etc/radcli /var/run
mkdir -p "${LOG_DIR_ROOT}/ocserv"
touch "${LOG_DIR_ROOT}/ocserv/ocserv.log" "${LOG_DIR_ROOT}/ocserv/error.log" "${LOG_DIR_ROOT}/ocserv/supervisord.log"

require_file /srv/pki/ca/ca-cert.pem
require_file /srv/pki/ca/crl.pem
require_file /srv/pki/server/server-cert.pem
require_file /srv/pki/server/server-key.pem

cp /opt/wormhole/ocserv.conf.template /etc/ocserv/ocserv.conf
cp /opt/wormhole/radiusclient.conf.template /etc/radcli/radiusclient.conf
cp /opt/wormhole/servers.template /etc/radcli/servers

sed -i "s/__RADIUS_SHARED_SECRET__/${RADIUS_SHARED_SECRET}/g" /etc/radcli/servers
sed -i "s/__VPN_TCP_PORT__/${VPN_TCP_PORT}/g" /etc/ocserv/ocserv.conf
sed -i "s/__VPN_UDP_PORT__/${VPN_UDP_PORT}/g" /etc/ocserv/ocserv.conf
sed -i "s/__VPN_NETWORK__/${VPN_NETWORK}/g" /etc/ocserv/ocserv.conf
sed -i "s/__VPN_NETMASK__/${VPN_NETMASK}/g" /etc/ocserv/ocserv.conf
sed -i "s/__VPN_MAX_CLIENTS__/${VPN_MAX_CLIENTS}/g" /etc/ocserv/ocserv.conf
sed -i "s/__VPN_DNS_1__/${VPN_DNS_1}/g" /etc/ocserv/ocserv.conf
sed -i "s/__VPN_DNS_2__/${VPN_DNS_2}/g" /etc/ocserv/ocserv.conf
sed -i "s/__VPN_IDLE_TIMEOUT__/${VPN_IDLE_TIMEOUT}/g" /etc/ocserv/ocserv.conf
sed -i "s/__VPN_MOBILE_IDLE_TIMEOUT__/${VPN_MOBILE_IDLE_TIMEOUT}/g" /etc/ocserv/ocserv.conf
sed -i "s/__VPN_SESSION_TIMEOUT__/${VPN_SESSION_TIMEOUT}/g" /etc/ocserv/ocserv.conf
sed -i "s/__VPN_STATS_REPORT_TIME__/${VPN_STATS_REPORT_TIME}/g" /etc/ocserv/ocserv.conf
sed -i "s/__VPN_DEFAULT_DOMAIN__/${VPN_DEFAULT_DOMAIN}/g" /etc/ocserv/ocserv.conf

if [ -z "${VPN_DEFAULT_DOMAIN}" ]; then
    sed -i '/^default-domain = /d' /etc/ocserv/ocserv.conf
fi

cidr="$(netmask_to_prefix "${VPN_NETMASK}")"
iptables -t nat -C POSTROUTING -s "${VPN_NETWORK}/${cidr}" -o "${OCSERV_NAT_DEVICE}" -j MASQUERADE 2>/dev/null || \
    iptables -t nat -A POSTROUTING -s "${VPN_NETWORK}/${cidr}" -o "${OCSERV_NAT_DEVICE}" -j MASQUERADE
iptables -C FORWARD -i vpns -o "${OCSERV_NAT_DEVICE}" -j ACCEPT 2>/dev/null || \
    iptables -A FORWARD -i vpns -o "${OCSERV_NAT_DEVICE}" -j ACCEPT
iptables -C FORWARD -i "${OCSERV_NAT_DEVICE}" -o vpns -m state --state RELATED,ESTABLISHED -j ACCEPT 2>/dev/null || \
    iptables -A FORWARD -i "${OCSERV_NAT_DEVICE}" -o vpns -m state --state RELATED,ESTABLISHED -j ACCEPT

exec /usr/bin/supervisord -c /opt/wormhole/supervisord.conf
