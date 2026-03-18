FROM mariadb:11.4

USER root

RUN apt-get update \
    && apt-get install -y --no-install-recommends gettext-base \
    && rm -rf /var/lib/apt/lists/*

COPY conf/logging.cnf.template /opt/wormhole/logging.cnf.template
COPY render-config.sh /usr/local/bin/render-config.sh

RUN chmod +x /usr/local/bin/render-config.sh

ENTRYPOINT ["/usr/local/bin/render-config.sh"]

