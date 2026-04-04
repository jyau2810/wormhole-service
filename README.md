# Wormhole Access Stack

Chinese documentation is available in [README.zh-CN.md](/Users/jyau/Documents/Projects/wormhole-service/README.zh-CN.md).

This repository provides a small-scale remote-access control plane with:

- `L2TP/IPSec PSK` as the primary native VPN path
- `FreeRADIUS` authentication, accounting, and anomaly signals
- Per-account expiration, concurrency, and bandwidth profiles
- Admin UI for connection metadata, active sessions, traffic, and security events
- Reserved integration surface for a future external `UniConnect SSL VPN` gateway

## Quick Start

1. Copy `.env.example` to `.env`.
2. Set strong values for database secrets, `RADIUS_SHARED_SECRET`, and `VPN_SHARED_PSK`.
3. Update `VPN_GATEWAYS` with your real public access points.
4. Start the stack:

```bash
docker compose --env-file .env up -d --build
```

5. Open the admin portal on `http://127.0.0.1:${ADMIN_PORTAL_PORT}` and create an account to view the exported connection profile.

## Local Validation

On macOS, local validation should stay focused on the non-VPN services:

```bash
cp .env.example .env
make local-up
make local-smoke
```

Full PPP, IPSec, and NAT validation still needs a Linux host.

## Key Components

- `docker-compose.yml`
- `.env.example`
- `bootstrap/db`
- `images/ipsec-l2tp-gateway`
- `images/freeradius`
- `images/admin-portal`

## Current Boundaries

- The repository does not implement a UniConnect-compatible SSL VPN gateway.
- The admin portal stores the VPN password in plaintext so it can derive and rotate `NT-Password` for FreeRADIUS. That is acceptable for this small-scale control plane, but production deployments should move secrets into a dedicated secret-management layer.
