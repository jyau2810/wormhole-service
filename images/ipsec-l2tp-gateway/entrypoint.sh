#!/bin/sh
set -eu

mkdir -p /etc/accel-ppp /etc /var/run /var/log/accel-ppp "${LOG_DIR_ROOT}/gateway"
mkdir -p /etc/strongswan.d

render_remote_ip_pool_lines() {
    python3 - <<'PY'
import ipaddress
import os
import sys

pool_name = "wormhole-vpn4"
network = ipaddress.IPv4Network(f"{os.environ['VPN_NETWORK']}/{os.environ['VPN_NETMASK']}", strict=False)
gateway = ipaddress.IPv4Address(os.environ["VPN_GATEWAY_IP"])

if gateway not in network:
    raise SystemExit(f"VPN_GATEWAY_IP {gateway} is outside VPN network {network}")

if network.prefixlen < 31:
    start = int(network.network_address) + 1
    end = int(network.broadcast_address) - 1
else:
    start = int(network.network_address)
    end = int(network.broadcast_address)

gateway_int = int(gateway)
ranges = []

if start > end:
    raise SystemExit(f"VPN network {network} has no usable client addresses")

if gateway_int < start or gateway_int > end:
    ranges.append((start, end))
elif start == end == gateway_int:
    raise SystemExit(
        f"VPN network {network} leaves no client addresses after reserving gateway {gateway}"
    )
else:
    if gateway_int > start:
        ranges.append((start, gateway_int - 1))
    if gateway_int < end:
        ranges.append((gateway_int + 1, end))

for range_start, range_end in ranges:
    if range_start == range_end:
        value = str(ipaddress.IPv4Address(range_start))
    else:
        value = f"{ipaddress.IPv4Address(range_start)}-{ipaddress.IPv4Address(range_end)}"
    print(f"{value},{pool_name}")
PY
}

VPN_REMOTE_IP_POOL_LINES="$(render_remote_ip_pool_lines)"
export VPN_REMOTE_IP_POOL_LINES

VPN_IPSEC_LOCAL_ID_LINE=""
if [ -n "${VPN_IPSEC_LOCAL_ID:-}" ]; then
    VPN_IPSEC_LOCAL_ID_LINE="    leftid=${VPN_IPSEC_LOCAL_ID}"
fi
export VPN_IPSEC_LOCAL_ID_LINE

envsubst '${LOG_DIR_ROOT} ${VPN_GATEWAY_IP} ${VPN_REMOTE_IP_POOL_LINES} ${VPN_DNS_1} ${VPN_DNS_2} ${VPN_MTU} ${VPN_RADIUS_HOST} ${VPN_RADIUS_AUTH_PORT} ${VPN_RADIUS_ACCT_PORT} ${RADIUS_SHARED_SECRET} ${VPN_NAS_IDENTIFIER} ${VPN_NAS_IP_ADDRESS} ${VPN_L2TP_PORT}' \
    < /opt/wormhole/accel-ppp.conf.template > /etc/accel-ppp/accel-ppp.conf
envsubst '${VPN_IPSEC_IKE_PORT} ${VPN_IPSEC_NATT_PORT} ${VPN_IPSEC_LOCAL_ID_LINE}' \
    < /opt/wormhole/ipsec.conf.template > /etc/ipsec.conf
cat /opt/wormhole/strongswan.conf.template > /etc/strongswan.d/charon-logging.conf
cat > /etc/ipsec.secrets <<EOF
: PSK "${VPN_SHARED_PSK}"
EOF
touch /var/log/accel-ppp/accel-ppp.log /var/log/accel-ppp/core.log \
    "${LOG_DIR_ROOT}/gateway/accel-ppp.log" "${LOG_DIR_ROOT}/gateway/accel-ppp-core.log" \
    "${LOG_DIR_ROOT}/gateway/charon.log"

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
tail -F "${LOG_DIR_ROOT}/gateway/accel-ppp.log" \
    "${LOG_DIR_ROOT}/gateway/accel-ppp-core.log" \
    "${LOG_DIR_ROOT}/gateway/charon.log"
