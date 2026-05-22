#!/bin/sh
set -eu

docker compose --env-file .env stop admin-portal ca-api freeradius db logrotate
