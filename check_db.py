from sqlalchemy import inspect, text
from desdeo.api.db import engine

# Create an inspector
inspector = inspect(engine)

# Get all table names
tables = inspector.get_table_names()
print("\nTables in database:", tables)

# If reference_data exists, show its columns
if "reference_data" in tables:
    print("\nColumns in reference_data table:")
    columns = inspector.get_columns("reference_data")
    for column in columns:
        print(f"- {column['name']}: {column['type']}")

    # Check foreign keys
    fks = inspector.get_foreign_keys("reference_data")
    print("\nForeign keys in reference_data table:")
    for fk in fks:
        print(f"- {fk}")

    # Check actual data
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA table_info(reference_data)"))
        print("\nDetailed table info:")
        for row in result:
            print(f"- {row}")
else:
    print("\nreference_data table does not exist!")
