#!/bin/sh
set -eu

docker compose --env-file .env stop admin-portal freeradius db logrotate
