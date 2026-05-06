.PHONY: test lint lint-yaml lint-actions lint-markdown install hooks test-bats test-prompts test-workflows

YAMLLINT    := yamllint
ACTIONLINT  := ./actionlint
MARKDOWNLINT := markdownlint
BATS        := $(shell command -v bats 2>/dev/null || echo "./tests/bin/bats")

## install: Install required lint tools and configure git hooks
install:
	pip install --quiet yamllint
	npm install -g markdownlint-cli
	@if [ ! -f ./actionlint ]; then \
		curl -sSfL https://raw.githubusercontent.com/rhysd/actionlint/main/scripts/download-actionlint.bash | bash; \
	fi
	@$(MAKE) hooks

## test: Run linters and behavioral tests
test: lint test-bats

## lint: Lint YAML, GitHub Actions, and Markdown files
lint: lint-yaml lint-actions lint-markdown

## lint-yaml: Validate all YAML files with yamllint
lint-yaml:
	@echo "--- yamllint ---"
	$(YAMLLINT) -c .yamllint.yml .github/

## lint-actions: Validate GitHub Actions workflows with actionlint
lint-actions:
	@echo "--- actionlint ---"
	@if [ -f $(ACTIONLINT) ]; then \
		$(ACTIONLINT) -shellcheck= .github/workflows/*.yml; \
	else \
		echo "⚠️  Skipping actionlint — binary not found. Run 'make install' to install."; \
	fi

## lint-markdown: Validate Markdown files with markdownlint
lint-markdown:
	@echo "--- markdownlint ---"
	$(MARKDOWNLINT) --config .markdownlint.json "**/*.md" --ignore node_modules --ignore tests

## test-bats: Run BATS behavioral tests
test-bats:
	@echo "--- bats ---"
	@if [ ! -f "$(BATS)" ]; then \
		echo "Installing bats..."; \
		mkdir -p tests && \
		curl -sSfL https://github.com/bats-core/bats-core/archive/refs/tags/v1.11.1.tar.gz | \
		tar xz -C tests --strip-components=1 bats-core-1.11.1; \
	fi
	$(BATS) tests/

## test-prompts: Run agent prompt smoke tests (alias for test-bats)
test-prompts: test-bats

## test-workflows: Run workflow structural tests (alias for test-bats)
test-workflows: test-bats
## hooks: Configure git to use .githooks directory
hooks:
	@echo "Configuring git hooks path..."
	@git config core.hooksPath .githooks
	@echo "Done."
