FROM debian:12-slim

ARG ACCEL_PPP_VERSION=1.14.0

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        cmake \
        curl \
        gettext-base \
        iproute2 \
        iptables \
        libnl-3-dev \
        libnl-genl-3-dev \
        libpcre2-dev \
        libpcre2-8-0 \
        libssl-dev \
        libssl3 \
        ppp \
        python3-minimal \
        strongswan \
        strongswan-starter \
        tini \
    && mkdir -p /tmp/accel-ppp \
    && curl -fsSL "https://github.com/accel-ppp/accel-ppp/archive/refs/tags/${ACCEL_PPP_VERSION}.tar.gz" \
        | tar -xz -C /tmp/accel-ppp --strip-components=1 \
    && mkdir -p /tmp/accel-ppp/build \
    && cd /tmp/accel-ppp/build \
    && cmake \
        -DBUILD_DRIVER=FALSE \
        -DNETSNMP=FALSE \
        -DLUA=FALSE \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_INSTALL_PREFIX=/usr \
        .. \
    && make -j"$(nproc)" \
    && make install \
    && rm -rf /tmp/accel-ppp \
    && apt-get purge -y --auto-remove \
        build-essential \
        ca-certificates \
        cmake \
        curl \
        libnl-3-dev \
        libnl-genl-3-dev \
        libpcre2-dev \
        libssl-dev \
    && rm -rf /var/lib/apt/lists/*

COPY entrypoint.sh /opt/wormhole/entrypoint.sh
COPY accel-ppp.conf.template /opt/wormhole/accel-ppp.conf.template
COPY ipsec.conf.template /opt/wormhole/ipsec.conf.template
RUN chmod +x /opt/wormhole/entrypoint.sh

ENTRYPOINT ["/usr/bin/tini", "--", "/opt/wormhole/entrypoint.sh"]
