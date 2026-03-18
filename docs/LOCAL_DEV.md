# Local Development

## Scope

Local development on macOS is limited to non-VPN data plane validation.

This mode starts:

- `db`
- `ca-api`
- `freeradius`
- `admin-portal`
- `logrotate`

This mode does not start:

- `ocserv`

Do not treat local macOS results as proof that TUN, NAT, or full VPN traffic forwarding works.

## Commands

```bash
cp .env.example .env
make local-up
make local-smoke
make local-down
```

## What `local-smoke` Verifies

- admin portal health endpoint
- CA API health endpoint from inside the container
- FreeRADIUS password authentication using `radtest`
- database write path into `radcheck`

## Local Logs

All file logs are written under:

```text
var/log/
```

Important paths:

- `var/log/admin-portal/app.log`
- `var/log/admin-portal/access.log`
- `var/log/admin-portal/error.log`
- `var/log/ca-api/app.log`
- `var/log/freeradius/freeradius.log`
- `var/log/mariadb/error.log`

