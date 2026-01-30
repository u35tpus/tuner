.PHONY: help test test-verbose test-integration test-unit venv install clean run run-demo coverage

# Prefer project virtualenv when it exists.
PYTHON := $(shell if [ -x .venv/bin/python ]; then echo .venv/bin/python; else echo python3; fi)
PIP := $(shell if [ -x .venv/bin/pip ]; then echo .venv/bin/pip; else echo pip3; fi)

help:
	@echo "Intonation Trainer - Makefile targets"
	@echo ""
	@echo "Setup & Environment:"
	@echo "  make venv          Create Python virtual environment"
	@echo "  make install       Install dependencies (requires active venv)"
	@echo ""
	@echo "Testing:"
	@echo "  make test          Run all unit tests"
	@echo "  make test-verbose  Run all unit tests with verbose output"
	@echo "  make test-unit     Run only unit tests (not integration)"
	@echo "  make test-integration Run only integration tests"
	@echo "  make coverage      Run tests and display coverage report"
	@echo ""
	@echo "Running:"
	@echo "  make run           Run trainer with config_template.yaml (requires venv)"
	@echo "  make run-demo      Generate demo with dry-run (text log only)"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean         Remove generated files (*.mp3, *.mid, *.txt, *.wav)"
	@echo ""

venv:
	python3 -m venv .venv
	. .venv/bin/activate && pip install --upgrade pip
	@echo "Virtual environment created. Activate with: . .venv/bin/activate"

install:
	$(PIP) install -r requirements.txt
	@echo "Dependencies installed."

test:
	$(PYTHON) -m unittest discover -s test -p "test_*.py" -q

test-verbose:
	$(PYTHON) -m unittest discover -s test -p "test_*.py" -v

test-unit:
	$(PYTHON) -m unittest test_intonation_trainer test_abc_notation test_coverage -v

test-integration:
	$(PYTHON) -m unittest test_integration test_intonation_trainer.TestIntegration test_intonation_trainer.TestSessionMIDIGeneration -v

coverage:
	$(PYTHON) -m coverage run -m unittest discover -s test -p "test_*.py" -q
	$(PYTHON) -m coverage report -m
	$(PYTHON) -m coverage html
	@echo "Coverage report generated in htmlcov/index.html"

run:
	$(PYTHON) intonation_trainer.py config_template.yaml --verbose

run-demo:
	$(PYTHON) intonation_trainer.py config_template.yaml --dry-run --max-duration 180 --text-file demo_exercises.txt

clean:
	rm -f *.mp3 *.mid .log *.wav *.m4a
	@echo "Cleaned up generated files."
