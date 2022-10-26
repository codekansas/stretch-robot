# Makefile

all: refresh
.PHONY: all

gunicorn:
	gunicorn \
		stretch.app:app \
		--bind 0.0.0.0:8080 \
		--reload \
		--worker-class aiohttp.GunicornWebWorker
.PHONY: gunicorn

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
	rm -rf build/ **/*.egg-info **/*.pyc **/*.so stretch/**/*.pyi stretch/**/*.so
.PHONY: clean

# ---------------
# Static analysis
# ---------------

py-files := $$(git ls-files '*.py')
cpp-files := $$(git ls-files '*.c' '*.cpp' '*.h' '*.hpp' '*.cu' '*.cuh')
cmake-files := $$(git ls-files '*/CMakeLists.txt')

format:
	cmake-format -i $(cmake-files)
	clang-format -i $(cpp-files)
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
