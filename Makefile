# Makefile

all: refresh
.PHONY: all

# --------------
# Build commands
# --------------

refresh:
	git checkout master
	git pull
	pip install -e '.[dev]'

install:
	pip install -e '.[dev]'
.PHONY: install

clean:
	rm -rf build/ **/*.egg-info **/*.pyc **/*.so ml/**/*.pyi ml/**/*.so
.PHONY: clean

# ---------------
# Static analysis
# ---------------

py-files := $$(git ls-files '*.py')

format:
	black $(py-files)
	isort $(py-files)
.PHONY: format

lint:
	black --diff --check $(py-files)
	isort --check-only $(py-files)
	mypy $(py-files)
	flake8 --count --show-source --statistics $(py-files)
	pylint $(py-files)
.PHONY: lint

# ----------
# Unit tests
# ----------

test:
	pytest .
.PHONY: test
