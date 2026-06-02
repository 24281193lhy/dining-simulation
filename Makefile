.PHONY: run test clean install

run:
	python -m canteen_sim

test:
	pytest tests/ -v

clean:
	rm -rf logs/*
	rm -rf __pycache__ canteen_sim/**/__pycache__
	rm -rf .pytest_cache

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"
