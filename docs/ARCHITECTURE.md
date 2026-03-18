# Architecture

## Overview

This stack is designed for a single-host Docker deployment where:

- `ocserv` terminates VPN traffic on `443/tcp` and `443/udp`
- `FreeRADIUS` validates account passwords and account expiration
- `MariaDB` stores VPN accounts, device slots, RADIUS check items, accounting, and auth logs
- `ca-api` manages the internal CA, client certificate issuance, revocation, and CRL generation
- `admin-portal` provides the day-to-day operations UI

## Authentication Model

Each VPN login requires two independent factors:

1. A valid client certificate issued by the internal CA
2. A valid VPN username/password pair checked by FreeRADIUS

This is implemented in `ocserv` with:

- `auth = "certificate"`
- `auth = "radius[...]"`

Account validity is enforced by writing these `radcheck` items:

- `Crypt-Password`
- `Expiration`

When an account is disabled, the portal rewrites the effective RADIUS expiration to the current UTC time so new logins are denied immediately.

## Device Binding Model

Device binding is enforced by the application layer, not by hardware fingerprinting.

- Each account can hold at most `2` active device slots.
- Each device slot corresponds to one active client certificate.
- Revoking a device certificate frees the slot.
- Attempting to issue a third device certificate is rejected by the admin portal.

The source of truth is the `vpn_devices` table.

## Logging and Visibility

- `radpostauth` records successful and failed auth outcomes.
- `radacct` records active and historical sessions if the NAS sends accounting packets.
- The portal surfaces:
  - account expiration
  - active device count
  - recent auth attempts
  - currently open sessions from `radacct`
- File logs are written under `var/log/` on the host and rotated daily by the `logrotate` sidecar.

## Certificate Layout

The `ca-data` volume is shared between `ca-api` and `ocserv`.

- `/data/ca/ca-cert.pem`
- `/data/ca/ca-key.pem`
- `/data/ca/crl.pem`
- `/data/server/server-cert.pem`
- `/data/server/server-key.pem`
- `/data/clients/<serial>/...`

`ocserv` mounts the same volume read-only under `/srv/pki`.

## Known Boundaries

- The initial deployment uses an internally generated VPN server certificate. Replace it with a public certificate once a domain is available.
- Device "last seen" is currently inferred from RADIUS accounting and auth history, not from a dedicated device heartbeat.
- This stack targets small-scale operation, not multi-node HA deployment.
