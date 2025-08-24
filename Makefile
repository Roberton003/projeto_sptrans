.PHONY: install install-dev test clean

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt

test:
	python -m unittest discover -s tests

clean:
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -delete