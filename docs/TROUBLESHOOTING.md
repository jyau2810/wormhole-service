# Troubleshooting

## Native L2TP client cannot connect

Check:

- host firewall exposes `500/udp`, `4500/udp`, and `1701/udp`
- `/dev/net/tun` and `/dev/ppp` are available
- `VPN_SHARED_PSK` matches what the client uses

Then inspect:

```bash
docker compose logs --tail=100 ipsec-l2tp-gateway
docker compose logs --tail=100 freeradius
```

## Account exists but auth is rejected

Check recent auth attempts in the portal first, then inspect:

```bash
docker compose exec db mariadb -uroot -p"$MARIADB_ROOT_PASSWORD" radius -e \
  "SELECT username, attribute, value FROM radcheck WHERE username='YOUR_USER';"
```

Verify that `NT-Password`, `Expiration`, and `Simultaneous-Use` exist.

## Traffic or anomaly signals look wrong

Check:

- whether `radacct` rows are receiving interim updates
- whether the gateway NAS IP and identifier match the expected values
- whether the account speed profile has realistic limits
