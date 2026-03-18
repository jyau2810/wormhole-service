# Troubleshooting

## `docker: command not found`

Docker is not installed on the host. Install Docker and the Compose plugin first.

## `Cannot open TUN/TAP dev`

The host is missing `/dev/net/tun`, or the container runtime is not allowed to pass it through.

Check:

```bash
ls -l /dev/net/tun
docker compose ps
```

## VPN connects but no internet access

Check host forwarding:

```bash
sysctl net.ipv4.ip_forward
```

Check the ocserv container NAT rules:

```bash
docker compose exec ocserv iptables -t nat -S
docker compose exec ocserv iptables -S FORWARD
```

If your outbound interface is not `eth0`, set `OCSERV_NAT_DEVICE` correctly in `.env`.

## Admin portal opens but login fails

`ADMIN_PASSWORD` from `.env` is the source of truth after startup. If you changed `.env`, recreate the portal container:

```bash
docker compose up -d --build admin-portal
```

## Account exists but VPN login is rejected

Check FreeRADIUS file logs first:

```bash
tail -n 100 var/log/freeradius/freeradius.log
```

Check the generated `radcheck` rows:

```bash
docker compose exec db mariadb -u root -p"$MARIADB_ROOT_PASSWORD" "$MARIADB_DATABASE" -e \
'SELECT username, attribute, op, value FROM radcheck ORDER BY username, attribute;'
```

## Device bundle imports but certificate login still fails

Common causes:

- the device certificate was revoked
- the CRL was regenerated and the client is still presenting an old certificate
- the account password is wrong
- the account is expired or disabled

Check:

- portal auth history
- `var/log/ca-api/error.log`
- `var/log/ocserv/error.log`

## Application error but `docker logs` looks empty

This stack writes primary service logs to files under `var/log/`.

Check the relevant file first:

- admin portal: `var/log/admin-portal/error.log`
- CA API: `var/log/ca-api/error.log`
- FreeRADIUS: `var/log/freeradius/freeradius.log`
- ocserv: `var/log/ocserv/error.log`
- MariaDB: `var/log/mariadb/error.log`

## Third device cannot be issued

This is expected. Each account has a maximum of two active device slots.

Revoke one active device first, then issue the replacement.
