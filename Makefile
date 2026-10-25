# Pipeline entry points. Targets are added phase by phase (mas/03_ROADMAP.md).
# Override the interpreter with: make PYTHON=python3 <target>

PYTHON ?= .venv/bin/python

.PHONY: help venv test inventory preprocess explore

help:
	@echo "make venv       create .venv and install requirements.txt"
	@echo "make test       run the synthetic test suite (no real data)"
	@echo "make inventory  P00: header + MARK inventory of the raw recordings -> reports/raw_inventory.csv"
	@echo "make preprocess P02: legacy 7-channel windows + PSD (--legacy-p02) -> data/processed/<S>/"
	@echo "make explore    P03: occipital spectra + PSD by class (fs 250 legacy) -> outputs/figures/exploration/<S>/"

venv:
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements.txt

test:
	$(PYTHON) -m pytest tests/ -q

inventory:
	$(PYTHON) scripts/exploration/inventory_raw.py

preprocess:
	$(PYTHON) -m scripts.preprocessing.run_preprocessing --all --legacy-p02

explore:
	$(PYTHON) -m scripts.exploration.diagnose_occipital_spectra --all
	$(PYTHON) -m scripts.exploration.visualize_data --all
