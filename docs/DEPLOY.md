# Deployment Guide

## 1. Host prerequisites

Prepare an Ubuntu 22.04 or Debian 12 host with:

- Docker 26+
- Docker Compose plugin
- `/dev/net/tun`
- `/dev/ppp`
- Public access to `500/udp`, `4500/udp`, and `1701/udp`

## 2. Enable forwarding

```bash
sudo sysctl -w net.ipv4.ip_forward=1
echo 'net.ipv4.ip_forward=1' | sudo tee /etc/sysctl.d/99-wormhole-vpn.conf
sudo sysctl --system
```

## 3. Configure the environment

```bash
cp .env.example .env
```

At minimum set:

- `MARIADB_PASSWORD`
- `MARIADB_ROOT_PASSWORD`
- `RADIUS_SHARED_SECRET`
- `ADMIN_PASSWORD`
- `ADMIN_SESSION_SECRET`
- `VPN_SHARED_PSK`
- `VPN_GATEWAYS`

## 4. Start the stack

```bash
docker compose --env-file .env up -d --build
```

Expected services:

- `db`
- `freeradius`
- `admin-portal`
- `ipsec-l2tp-gateway`
- `logrotate`

## 5. Validate

```bash
docker compose ps
docker compose logs --tail=50 freeradius
docker compose logs --tail=50 ipsec-l2tp-gateway
docker compose logs --tail=50 admin-portal
```

Then:

1. Create a test VPN account in the portal.
2. Open the account detail page and confirm the shared PSK, gateway list, and speed profile.
3. Connect from a native `L2TP/IPSec PSK` client.
4. Verify that sessions, traffic, and events appear in the portal.
