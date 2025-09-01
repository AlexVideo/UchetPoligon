# UchetPoligon

Минималистичный учёт (SQLite) с DAO-слоем и тестами.

## Быстрый старт (Windows PowerShell)

```powershell
# 1) создать и активировать venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2) зависимости
python -m pip install -r requirements.txt

# 3) (если есть скрипт миграций)
# python core\db\migrate.py

# 4) тесты
python -m pytest -q
