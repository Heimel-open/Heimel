.PHONY: setup test run-offline run-filtered run-direct run-gemini-filtered run-gemini-direct clean

setup:
	python3 -m venv .venv
	. .venv/bin/activate && pip install -r requirements.txt

test:
	. .venv/bin/activate && pytest -q

run-offline:
	. .venv/bin/activate && python src/run_case.py cases/anchorage.json --no-kimi
	. .venv/bin/activate && python src/run_case.py cases/chemical_plant.json --no-kimi

run-filtered:
	. .venv/bin/activate && python src/run_case.py cases/anchorage.json
	. .venv/bin/activate && python src/run_case.py cases/chemical_plant.json

run-direct:
	. .venv/bin/activate && python src/run_case.py cases/anchorage.json --direct
	. .venv/bin/activate && python src/run_case.py cases/chemical_plant.json --direct

run-gemini-filtered:
	. .venv/bin/activate && python src/run_gemini_case.py cases/anchorage.json
	. .venv/bin/activate && python src/run_gemini_case.py cases/chemical_plant.json

run-gemini-direct:
	. .venv/bin/activate && python src/run_gemini_case.py cases/anchorage.json --direct
	. .venv/bin/activate && python src/run_gemini_case.py cases/chemical_plant.json --direct

clean:
	rm -rf .venv __pycache__ src/__pycache__ tests/__pycache__ .pytest_cache
