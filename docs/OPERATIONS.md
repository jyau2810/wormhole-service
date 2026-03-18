# Operations Guide

## Admin Login

The portal admin user is bootstrapped from:

- `ADMIN_USERNAME`
- `ADMIN_PASSWORD`

On every container start, the portal ensures that this admin account exists and updates its password hash from `.env`.

## Log Files

The preferred first-stop logs are file logs under `var/log/`:

- `var/log/admin-portal/app.log`
- `var/log/admin-portal/access.log`
- `var/log/admin-portal/error.log`
- `var/log/ca-api/app.log`
- `var/log/ca-api/access.log`
- `var/log/ca-api/error.log`
- `var/log/freeradius/freeradius.log`
- `var/log/ocserv/ocserv.log`
- `var/log/ocserv/error.log`
- `var/log/mariadb/error.log`
- `var/log/mariadb/slow.log`

Retention is 7 days via the `logrotate` sidecar.

## Common Tasks

### Create a VPN account

In the portal:

1. Enter `username`
2. Enter the VPN password
3. Choose the expiration date
4. Submit

The portal writes:

- `vpn_accounts`
- `radcheck` `Crypt-Password`
- `radcheck` `Expiration`

### Extend account validity

Open the account page and submit a new expiration date.

No device certificate re-issuance is required.

### Disable or enable an account

Use the toggle button on the account page.

- `enabled`: restores the configured expiration date
- `disabled`: forces an immediate effective RADIUS expiration

### Issue a device certificate

On the account page:

1. Enter a device label
2. Click `Issue Device Certificate`

If both device slots are already occupied, issuance is rejected.

### Revoke a device certificate

On the account page, click `Revoke`.

This:

- marks the DB record as revoked
- regenerates the CRL
- frees the device slot for reuse

## Backup

Back up:

- MariaDB volume
- `ca-data` volume
- `.env`

Recommended commands:

```bash
docker compose exec db mysqldump -u root -p"$MARIADB_ROOT_PASSWORD" "$MARIADB_DATABASE" > backup.sql
docker run --rm -v wormhole-vpn_ca-data:/from -v "$PWD":/to alpine sh -c 'cd /from && tar czf /to/ca-data.tgz .'
```

## Restore

Restore sequence:

1. Stop the stack
2. Restore MariaDB data or import `backup.sql`
3. Restore the `ca-data` volume
4. Start the stack again

Restoring the CA volume is critical. Without it, previously issued device certificates will no longer match the CA and CRL state.

## Useful Commands

```bash
docker compose logs -f admin-portal
docker compose logs -f ca-api
docker compose logs -f freeradius
docker compose logs -f ocserv
docker compose exec ocserv occtl show users
tail -f var/log/admin-portal/app.log
tail -f var/log/ca-api/error.log
tail -f var/log/freeradius/freeradius.log
```
