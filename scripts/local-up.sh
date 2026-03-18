#!/bin/sh
set -eu

docker compose --env-file .env up -d --build db ca-api freeradius admin-portal logrotate

