#!/bin/sh
set -eu

docker compose --env-file .env up -d --build db freeradius ca-api admin-portal logrotate
