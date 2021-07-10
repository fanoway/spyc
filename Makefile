.DEFAULT_GOAL := tox
.PHONY: tox lint test build run
lint:
	poetry run black spyc/
	poetry run flake8 spyc/
	poetry run pylint spyc/ --exit-zero
	poetry run mypy spyc/

test: lint  ## Run tests with coverage, lint first
	poetry run pytest --cov=spyc tests/

tox:
	poetry run python -m tox -e py39

build: tox # run tox first before building
	poetry build

run:
	poetry run python -m spyc.main plot tests -d
