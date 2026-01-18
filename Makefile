.PHONY: help dev run build-ui

help:
	@echo "Targets:"
	@echo "  make dev      - run backend + Vite dev server (two-process dev)"
	@echo "  make build-ui - build frontend into frontend/dist"
	@echo "  make run      - build UI then run single-process backend serving UI+API"

dev:
	@bash ./scripts/dev.sh

build-ui:
	@cd frontend && npm install && npm run build

run:
	@bash ./scripts/run.sh

