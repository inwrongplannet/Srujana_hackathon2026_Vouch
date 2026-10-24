# Why: the root Makefile delegates dev/test/lint to each zone (see scaffold-zone skill).
.PHONY: dev test lint

node_modules: package.json package-lock.json
	npm ci
	@touch node_modules

dev: node_modules
	npm run dev

test: node_modules
	npm test

lint: node_modules
	npm run lint
