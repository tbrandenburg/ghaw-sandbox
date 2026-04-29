.PHONY: test lint lint-yaml lint-actions lint-markdown install hooks

YAMLLINT    := yamllint
ACTIONLINT  := ./actionlint
MARKDOWNLINT := markdownlint

## install: Install required lint tools
install:
	pip install --quiet yamllint
	npm install -g markdownlint-cli
	@if [ ! -f ./actionlint ]; then \
		curl -sSfL https://raw.githubusercontent.com/rhysd/actionlint/main/scripts/download-actionlint.bash | bash; \
	fi

## test: Run all linters
test: lint

## lint: Lint YAML, GitHub Actions, and Markdown files
lint: lint-yaml lint-actions lint-markdown

## lint-yaml: Validate all YAML files with yamllint
lint-yaml:
	@echo "--- yamllint ---"
	$(YAMLLINT) -c .yamllint.yml .github/

## lint-actions: Validate GitHub Actions workflows with actionlint
lint-actions:
	@echo "--- actionlint ---"
	$(ACTIONLINT) -shellcheck= .github/workflows/*.yml

## lint-markdown: Validate Markdown files with markdownlint
lint-markdown:
	@echo "--- markdownlint ---"
	$(MARKDOWNLINT) --config .markdownlint.json "**/*.md" --ignore node_modules

## hooks: Install git hooks
hooks:
	@echo "Installing pre-push hook..."
	@cp .githooks/pre-push .git/hooks/pre-push
	@chmod +x .git/hooks/pre-push
	@echo "Done."
