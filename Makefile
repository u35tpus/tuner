.PHONY: help test test-verbose test-integration test-unit venv install clean run run-demo

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
	pip install -r requirements.txt
	@echo "Dependencies installed."

test:
	python3 -m unittest test_intonation_trainer -q

test-verbose:
	python3 -m unittest test_intonation_trainer -v

test-unit:
	python3 -m unittest discover -s . -p "test_*.py" -k "not Integration" -v

test-integration:
	python3 -m unittest test_intonation_trainer.TestIntegration -v

run:
	python3 intonation_trainer.py config_template.yaml --verbose

run-demo:
	python3 intonation_trainer.py config_template.yaml --dry-run --max-duration 180 --text-file demo_exercises.txt

clean:
	rm -f Intonation_*.mp3 Intonation_*.mid Intonation_*.txt Intonation_*.wav
	rm -f demo_*.mp3 demo_*.mid demo_*.txt demo_*.wav
	rm -f test_*.mp3 test_*.mid test_*.txt test_*.wav
	rm -f from_text_*.mp3 from_text_*.mid
	@echo "Cleaned up generated files."
