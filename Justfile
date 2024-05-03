@default:
  @just --list

# Run pyproject-build
@build: check lint test
  pipenv run pyproject-build

#  Run ruff format --check
@check:
  pipenv run ruff format --check

# Run check, lint, and test
@checks: check lint test

# Remove dist and egg-info
@clean:
  -rm dist/*
  -rmdir dist
  -rm fbx.egg-info/*
  -rmdir fbx.egg-info

# Run ruff format
@format:
  pipenv run ruff format

# Run ruff check
@lint:
  pipenv run ruff check

# Run pytest
@test:
  pipenv run pytest
