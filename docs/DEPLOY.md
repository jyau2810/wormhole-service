# Deployment Guide

## 1. Host Prerequisites

Prepare an Ubuntu 22.04 host with:

- Docker 26
- Docker Compose plugin
- `/dev/net/tun` available
- public inbound access to `443/tcp` and `443/udp`

Run these checks on the host:

```bash
docker --version
docker compose version
ls -l /dev/net/tun
```

## 2. Enable Host Forwarding

Enable IPv4 forwarding on the host:

```bash
sudo sysctl -w net.ipv4.ip_forward=1
echo 'net.ipv4.ip_forward=1' | sudo tee /etc/sysctl.d/99-wormhole-vpn.conf
sudo sysctl --system
```

## 3. Firewall and Security Group

Allow:

- `443/tcp`
- `443/udp`

Do not expose the admin portal directly to the internet. By default it binds to `127.0.0.1:${ADMIN_PORTAL_PORT}` only.

Recommended access methods:

- SSH tunnel
- Tailscale/ZeroTier side-channel
- Reverse proxy with IP allowlist and TLS

## 4. Configure Environment

Create `.env` from the example:

```bash
cp .env.example .env
```

At minimum, replace:

- `MARIADB_PASSWORD`
- `MARIADB_ROOT_PASSWORD`
- `RADIUS_SHARED_SECRET`
- `ADMIN_PASSWORD`
- `ADMIN_SESSION_SECRET`
- `CA_API_TOKEN`
- `VPN_SERVER_HOST`
- review `LOG_LEVEL`, `LOG_RETENTION_DAYS`, `MYSQL_GENERAL_LOG`, and `MYSQL_SLOW_LOG_THRESHOLD_MS`

## 5. Start the Stack

```bash
docker compose --env-file .env up -d --build
```

Expected services:

- `db`
- `ca-api`
- `freeradius`
- `admin-portal`
- `ocserv`

## 6. Verify Health

```bash
docker compose ps
docker compose logs --tail=50 ca-api
docker compose logs --tail=50 freeradius
docker compose logs --tail=50 ocserv
```

Primary file logs are also written under:

```text
var/log/
```

The admin portal should be reachable at:

```text
http://127.0.0.1:${ADMIN_PORTAL_PORT}
```

If you are connecting remotely:

```bash
ssh -L 8080:127.0.0.1:${ADMIN_PORTAL_PORT} user@your-server
```

Then open `http://127.0.0.1:8080`.

## 7. First Operational Check

After logging into the portal:

1. Create a test VPN account.
2. Issue one device certificate.
3. Download the ZIP bundle.
4. Import `client.p12` into an OpenConnect-compatible client.
5. Log in with the VPN username/password from the portal.

## 8. Production Follow-Up

Before real user distribution:

- add a domain for `VPN_SERVER_HOST`
- replace the generated server certificate with a public one
- limit admin access with a source IP allowlist
- enable automated backups
- include `var/log/` in operational log collection if you use centralized retention
