#!/bin/sh
set -eu

docker compose --env-file .env up -d --build db freeradius admin-portal logrotate
