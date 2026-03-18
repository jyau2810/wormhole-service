FROM freeradius/freeradius-server:3.2.8

USER root

RUN apt-get update \
    && apt-get install -y --no-install-recommends gettext-base freeradius-utils \
    && rm -rf /var/lib/apt/lists/*

COPY config/clients.conf.template /opt/wormhole/clients.conf.template
COPY config/mods-enabled/sql.template /opt/wormhole/sql.template
COPY config/mods-config/sql/main/mysql/queries.conf /opt/wormhole/queries.conf
COPY config/sites-enabled/default /opt/wormhole/default
COPY config/sites-enabled/inner-tunnel /opt/wormhole/inner-tunnel
COPY scripts/render-config.sh /usr/local/bin/render-config.sh

RUN chmod +x /usr/local/bin/render-config.sh

ENTRYPOINT ["/usr/local/bin/render-config.sh"]
