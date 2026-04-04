# Architecture

The current stack is a small-scale remote-access control plane built around:

- `ipsec-l2tp-gateway`
  - `strongSwan` for IPSec PSK
  - `accel-ppp` for L2TP/PPP, RADIUS auth, and accounting
- `FreeRADIUS` for authentication, expiration enforcement, and bandwidth replies
- `MariaDB` for accounts, speed profiles, accounting logs, and anomaly events
- `admin-portal` for account operations, gateway metadata, traffic, and event handling

## Authentication model

Each native VPN login depends on:

1. The shared IPSec PSK
2. The account username and password

The portal syncs these RADIUS control attributes:

- `NT-Password`
- `Expiration`
- `Simultaneous-Use`

It also writes reply attributes for the gateway:

- `Filter-Id`
- `WISPr-Bandwidth-Max-Up`
- `WISPr-Bandwidth-Max-Down`

## Account policy

Each account carries:

- enabled or disabled status
- expiration timestamp
- speed profile
- max concurrent sessions

The previous client-certificate, device-slot, and CA/CRL model has been removed from the active deployment path.

## Observability

The portal combines:

- `radpostauth` for recent auth successes and failures
- `radacct` for active sessions and byte counters
- `vpn_account_events` for anomaly tracking

Built-in anomaly signals include excessive concurrency, repeated auth rejects, gateway hopping, and 5-minute traffic spikes.

## UniConnect boundary

The repository reserves a future integration surface for an external UniConnect SSL VPN gateway, but does not implement a UniConnect-compatible SSL gateway itself.
