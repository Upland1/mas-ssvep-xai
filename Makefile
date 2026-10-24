# Pipeline entry points. Targets are added phase by phase (mas/03_ROADMAP.md).
# Override the interpreter with: make PYTHON=python3 <target>

PYTHON ?= .venv/bin/python

.PHONY: help venv test inventory

help:
	@echo "make venv       create .venv and install requirements.txt"
	@echo "make test       run the synthetic test suite (no real data)"
	@echo "make inventory  P00: header + MARK inventory of the raw recordings -> reports/raw_inventory.csv"

venv:
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements.txt

test:
	$(PYTHON) -m pytest tests/ -q

inventory:
	$(PYTHON) scripts/exploration/inventory_raw.py
