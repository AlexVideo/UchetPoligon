import os, inspect
import core.db.dao as dao

print("DAO FILE:", os.path.abspath(dao.__file__))

print("\n=== mode_of_well_on (source) ===")
print(inspect.getsource(dao.Database.mode_of_well_on))
