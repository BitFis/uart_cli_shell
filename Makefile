all: init check

init:
	@echo "setup virtual python environment 'ot-test-env'"
	python3 -m venv .ot-test-env
	.ot-test-env/bin/python3 -m pip install -r requirements.txt

check:
	@echo "testing test environment classes"
	./test_device_interface.py

run:
	@echo "run all simulation tests"

run-simulation:
	@echo "WIP"

run-device:
	@echo "WIP"

.PHONY: init check
