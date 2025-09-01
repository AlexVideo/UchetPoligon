from core.db.dao import Database, DEFAULT_DB
import os

db = Database()
print("DEFAULT_DB =", DEFAULT_DB)
print("db.db_path =", db.db_path)
print("DB exists? ", os.path.exists(db.db_path))
