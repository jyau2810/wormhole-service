# Local Development

## Scope

Local macOS validation is limited to the control-plane services:

- `db`
- `freeradius`
- `admin-portal`
- `logrotate`

This mode does not validate:

- `ipsec-l2tp-gateway`
- PPP forwarding
- IPSec transport
- NAT and full internet egress

## Commands

```bash
cp .env.example .env
make local-up
make local-smoke
make local-down
```

## What `local-smoke` verifies

- admin portal health endpoint
- database writes into `radcheck`
- FreeRADIUS auth using `NT-Password` and an `MSCHAP` test request
