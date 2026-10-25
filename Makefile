# Makefile
# Why: one command vocabulary for the whole team and for every agent, whatever the stack ends up being.
#
# Convention: when backend/ or frontend/ is scaffolded, give it its own Makefile with
# `dev`, `test` and `lint` targets. The root targets below delegate to them and skip
# a zone that has no Makefile yet. `bash scripts/py` finds a working Python 3.10+ on any OS.
PYTHON ?= bash scripts/py
ZONES  := backend frontend

.PHONY: dev test lint check seed types readme docs structure hooks

define for_zones
	@for z in $(ZONES); do \
		if [ -f $$z/Makefile ]; then echo "== $$z: $(1) =="; $(MAKE) -C $$z $(1) || exit 1; \
		else echo "== $$z: no Makefile yet, skipping $(1) =="; fi; \
	done
endef

dev:   ## run backend + frontend
	@for z in $(ZONES); do \
		if [ -f $$z/Makefile ]; then $(MAKE) -C $$z dev & fi; \
	done; wait

test:  ## run tests (zones, then the repo scripts)
	$(call for_zones,test)
	$(PYTHON) -m unittest discover -s scripts -p 'test_*.py' -q

lint:  ## run linters/formatters
	$(call for_zones,lint)

structure: ## README markers, required files, no secrets/conflict markers tracked
	$(PYTHON) scripts/check_structure.py

docs:  ## docs gates: agent files, style and nomenclature, docs-sync
	$(PYTHON) scripts/check_agents.py
	$(PYTHON) scripts/check_docs_style.py
	$(PYTHON) scripts/check_docs.py

readme: ## regenerate the README features table from docs/frontend-features/*.md
	$(PYTHON) scripts/update_readme.py

check: structure docs lint test  ## what CI and /review-pr run
	$(PYTHON) scripts/update_readme.py --check

hooks: ## install the pre-push docs gate (once per clone)
	git config core.hooksPath scripts/hooks
	@echo "hooks installed: git push now runs the docs gates"

seed:  ## load demo data
	$(PYTHON) scripts/seed.py

types: ## generate frontend types from backend OpenAPI
	bash scripts/gen_types.sh
