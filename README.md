# Wormhole VPN Stack

Chinese documentation is available in [README.zh-CN.md](README.zh-CN.md).

Dockerized VPN stack for small-scale account distribution with:

- OpenConnect/ocserv VPN
- FreeRADIUS-backed username/password auth
- Per-account expiration control
- Per-account maximum 2 bound device certificates
- Internal CA and CRL management
- Lightweight admin portal

## Quick Start

1. Copy `.env.example` to `.env` and fill in strong secrets.
2. Read `docs/DEPLOY.md` and complete the host prerequisites.
3. Start the stack:

```bash
docker compose --env-file .env up -d --build
```

4. Open the admin portal on `http://127.0.0.1:${ADMIN_PORTAL_PORT}` from the server itself or through an SSH tunnel.

## Local Non-VPN Validation

On macOS, only the non-VPN services are suitable for local validation.

```bash
cp .env.example .env
make local-up
make local-smoke
```

See `docs/LOCAL_DEV.md` for details.

## Documentation

- English:
  - `README.md`
  - `env.md`
  - `docs/ARCHITECTURE.md`
  - `docs/DEPLOY.md`
  - `docs/LOCAL_DEV.md`
  - `docs/OPERATIONS.md`
  - `docs/TROUBLESHOOTING.md`
- Chinese:
  - `README.zh-CN.md`
  - `env.zh-CN.md`
  - `docs/zh-CN/ARCHITECTURE.md`
  - `docs/zh-CN/DEPLOY.md`
  - `docs/zh-CN/LOCAL_DEV.md`
  - `docs/zh-CN/OPERATIONS.md`
  - `docs/zh-CN/TROUBLESHOOTING.md`

## Delivered Components

- `docker-compose.yml`: one-command deployment entrypoint
- `Makefile`: local smoke-test helpers
- `.env.example`: required environment variables
- `env.md`: variable reference
- `bootstrap/db`: MariaDB bootstrap schema
- `images/ocserv`: VPN server image and runtime templates
- `images/freeradius`: FreeRADIUS image and SQL-backed config
- `images/ca-api`: internal CA/CRL API
- `images/admin-portal`: admin web UI
- `docs/`: architecture, deployment, operations, troubleshooting
- `var/log/`: host-side service log directory

## Notes

- This repository bootstraps a self-signed VPN server certificate from the internal CA for initial deployment.
- For production use, replace the VPN server certificate with a public certificate after you have a domain.
- Docker is not available in the current local environment, so validation in this repository is limited to static checks and Python tests.
