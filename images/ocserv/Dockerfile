FROM alpine:3.20

ARG OCSERV_VERSION=1.4.1

RUN build_deps="\
        curl-dev \
        freeradius-client-dev \
        g++ \
        gnutls-dev \
        http-parser-dev \
        ipcalc \
        krb5-dev \
        libev-dev \
        libmaxminddb-dev \
        libnl3-dev \
        libseccomp-dev \
        linux-headers \
        linux-pam-dev \
        lz4-dev \
        make \
        oath-toolkit-dev \
        protobuf-c-compiler \
        readline-dev \
        tar \
        wget \
        xz" \
    && apk add --no-cache --virtual .build-deps ${build_deps} \
    && wget -O /tmp/ocserv.tar.xz "ftp://ftp.infradead.org/pub/ocserv/ocserv-${OCSERV_VERSION}.tar.xz" \
    && mkdir -p /usr/src/ocserv \
    && tar -xf /tmp/ocserv.tar.xz -C /usr/src/ocserv --strip-components=1 \
    && rm -f /tmp/ocserv.tar.xz \
    && cd /usr/src/ocserv \
    && ./configure --enable-radius --disable-oidc-auth \
    && make -j"$(nproc)" \
    && make install \
    && run_deps="$(scanelf --needed --nobanner /usr/local/sbin/ocserv /usr/local/sbin/ocserv-worker /usr/local/bin/occtl /usr/local/bin/ocpasswd | awk '{ gsub(/,/, \"\\nso:\", $2); print \"so:\" $2 }' | xargs -r apk info --installed | sort -u)" \
    && apk add --no-cache --virtual .run-deps ${run_deps} bash coreutils gnutls-utils iptables iproute2 libnl3 pwgen supervisor \
    && apk del .build-deps \
    && rm -rf /usr/src/ocserv

COPY ocserv.conf.template /opt/wormhole/ocserv.conf.template
COPY radiusclient.conf.template /opt/wormhole/radiusclient.conf.template
COPY servers.template /opt/wormhole/servers.template
COPY supervisord.conf /opt/wormhole/supervisord.conf
COPY entrypoint.sh /usr/local/bin/entrypoint.sh

RUN chmod +x /usr/local/bin/entrypoint.sh

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
