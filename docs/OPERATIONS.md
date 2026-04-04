# Operations

## Portal actions

Use the admin portal to:

- create VPN accounts
- rotate passwords
- change expiration
- update speed profiles
- change max concurrent sessions
- disable suspicious accounts

## Logs

Important paths:

- `var/log/admin-portal/app.log`
- `var/log/admin-portal/access.log`
- `var/log/freeradius/freeradius.log`
- `var/log/gateway/accel-ppp.log`
- `var/log/mariadb/error.log`

## Useful commands

```bash
docker compose logs -f admin-portal
docker compose logs -f freeradius
docker compose logs -f ipsec-l2tp-gateway
docker compose exec db mariadb -uroot -p"$MARIADB_ROOT_PASSWORD" radius
```

## Day-2 checks

- Verify open events in the portal.
- Review accounts with high traffic or repeated rejects.
- Confirm that `VPN_GATEWAYS` still matches public ingress points.
