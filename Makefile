.PHONY: install install-dev test lint clean

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt

test:
	python -m pytest tests/ -q

lint:
	ruff check src/ tests/

clean:
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -delete