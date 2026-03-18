FROM alpine:3.20

RUN apk add --no-cache bash logrotate gettext

COPY logrotate.conf.template /etc/logrotate.conf.template
COPY run-logrotate.sh /usr/local/bin/run-logrotate.sh

RUN chmod +x /usr/local/bin/run-logrotate.sh

ENTRYPOINT ["/usr/local/bin/run-logrotate.sh"]

