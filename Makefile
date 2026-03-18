ENV_FILE ?= .env

.PHONY: local-up local-down local-smoke

local-up:
	./scripts/local-up.sh

local-down:
	./scripts/local-down.sh

local-smoke:
	./scripts/local-smoke.sh

