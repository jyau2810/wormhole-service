FROM debian:12-slim

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        accel-ppp \
        gettext-base \
        iproute2 \
        iptables \
        ppp \
        python3-minimal \
        strongswan \
        strongswan-starter \
        tini \
    && rm -rf /var/lib/apt/lists/*

COPY entrypoint.sh /opt/wormhole/entrypoint.sh
COPY accel-ppp.conf.template /opt/wormhole/accel-ppp.conf.template
COPY ipsec.conf.template /opt/wormhole/ipsec.conf.template
RUN chmod +x /opt/wormhole/entrypoint.sh

ENTRYPOINT ["/usr/bin/tini", "--", "/opt/wormhole/entrypoint.sh"]
