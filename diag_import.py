import os, inspect
import core.db.dao as dao

print("USING FILE:", os.path.abspath(dao.__file__))

print("\ncreate_block():")
print(inspect.getsource(dao.Database.create_block))

print("\ncreate_well():")
print(inspect.getsource(dao.Database.create_well))
