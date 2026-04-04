#!/bin/sh
set -eu

mkdir -p /etc/accel-ppp /etc /var/run /var/log/accel-ppp "${LOG_DIR_ROOT}/gateway"

envsubst '${VPN_NETWORK} ${VPN_NETMASK} ${VPN_GATEWAY_IP} ${VPN_DNS_1} ${VPN_DNS_2} ${VPN_MTU} ${VPN_RADIUS_HOST} ${VPN_RADIUS_AUTH_PORT} ${VPN_RADIUS_ACCT_PORT} ${RADIUS_SHARED_SECRET} ${VPN_NAS_IDENTIFIER} ${VPN_NAS_IP_ADDRESS} ${VPN_L2TP_PORT}' \
    < /opt/wormhole/accel-ppp.conf.template > /etc/accel-ppp/accel-ppp.conf
envsubst '${VPN_IPSEC_IKE_PORT} ${VPN_IPSEC_NATT_PORT}' \
    < /opt/wormhole/ipsec.conf.template > /etc/ipsec.conf
cat > /etc/ipsec.secrets <<EOF
: PSK "${VPN_SHARED_PSK}"
EOF

netmask_to_prefix() {
    python3 - <<'PY'
import ipaddress
import os

print(ipaddress.IPv4Network(f"0.0.0.0/{os.environ['VPN_NETMASK']}").prefixlen)
PY
}

cidr="$(netmask_to_prefix)"
iptables -t nat -C POSTROUTING -s "${VPN_NETWORK}/${cidr}" -o "${VPN_NAT_DEVICE}" -j MASQUERADE 2>/dev/null || \
    iptables -t nat -A POSTROUTING -s "${VPN_NETWORK}/${cidr}" -o "${VPN_NAT_DEVICE}" -j MASQUERADE
iptables -C FORWARD -s "${VPN_NETWORK}/${cidr}" -j ACCEPT 2>/dev/null || \
    iptables -A FORWARD -s "${VPN_NETWORK}/${cidr}" -j ACCEPT
iptables -C FORWARD -d "${VPN_NETWORK}/${cidr}" -m state --state RELATED,ESTABLISHED -j ACCEPT 2>/dev/null || \
    iptables -A FORWARD -d "${VPN_NETWORK}/${cidr}" -m state --state RELATED,ESTABLISHED -j ACCEPT

ipsec start
accel-pppd -d -c /etc/accel-ppp/accel-ppp.conf >> "${LOG_DIR_ROOT}/gateway/accel-ppp.log" 2>&1 &

trap 'ipsec stop; killall accel-pppd 2>/dev/null || true' INT TERM
tail -F "${LOG_DIR_ROOT}/gateway/accel-ppp.log"
