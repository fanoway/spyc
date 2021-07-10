.DEFAULT_GOAL := tox
.PHONY: tox lint test build run run_d
lint:
	poetry run black spyc_spc/
	poetry run flake8 spyc_spc/
	poetry run pylint spyc_spc/ --exit-zero
	poetry run mypy spyc_spc/

test: lint  ## Run tests with coverage, lint first
	poetry run pytest --cov=spyc_spc tests/

tox:
	poetry run python -m tox -e py39

build: tox # run tox first before building
	poetry build

run_d:
	poetry run python -m spyc_spc.main plot tests -d


run:
	poetry run python -m spyc_spc.main plot tests