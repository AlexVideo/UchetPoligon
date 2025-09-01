.PHONY: migrate test clean
PY?=python
migrate:
	$(PY) core/db/migrate.py
test:
	$(PY) -m pytest -q
clean:
	-del /q data\\uchet.db 2>nul || true
