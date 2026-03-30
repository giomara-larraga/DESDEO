import os
import warnings
from sqlalchemy import create_engine, inspect
from sqlalchemy_utils import database_exists
from sqlmodel import Session, SQLModel

from desdeo.api.config import SettingsConfig
from desdeo.api.db import engine
import desdeo.api.models  # noqa: F401 — registers all SQLModel table classes in metadata

LOCAL_SQLITE_DB_PATH = "local_copy.db"
local_engine = create_engine(f"sqlite:///{LOCAL_SQLITE_DB_PATH}")

RESET_DB = 0  # Dont reset the database by default, as this file is meant to be used for copying data from Postgres to SQLite.
SEED_DB = 0  # Dont seed the database by default, as this file is meant to be used for copying data from Postgres to SQLite.


# Ensure the postgres database exists before trying to copy data from it.
def ensure_remote_database_exists():
    # Return true if the database exists, false otherwise.
    if SettingsConfig.debug:
        print("Debug mode: Please ensure the configuration is not in debug mode.")
        return False
    else:
        if not database_exists(engine.url):
            return False
        else:
            return True


def copy_data_from_postgres_to_sqlite():
    # This function will copy data from the remote Postgres database to the local SQLite database. It will use SQLAlchemy sessions to read data from the remote database and write it to the local database.

    # Get the list of tables defined in the SQLModel metadata
    expected_tables = list(SQLModel.metadata.tables.keys())

    with Session(engine) as remote_session, Session(local_engine) as local_session:
        for table_name in expected_tables:
            # Get the Table object from the SQLModel metadata
            table = SQLModel.metadata.tables[table_name]

            # Query all data from the remote Postgres database for this table
            remote_data = remote_session.execute(table.select()).fetchall()

            # Insert rows into the local SQLite database
            if remote_data:
                local_session.execute(
                    table.insert(), [row._asdict() for row in remote_data]
                )

        # Commit changes to the local SQLite database
        local_session.commit()

    print(
        "Data copied from remote Postgres database to local SQLite database successfully."
    )


def validate_schema():
    # This function checks if the schema of the remote Postgres database matches the expected schema defined by the SQLModel models. If there are any discrepancies, it prints a warning and exits.

    # Use the existing engine for the remote Postgres database
    remote_engine = engine

    # Create an inspector for the remote database
    inspector = inspect(remote_engine)

    # Get the list of tables in the remote database
    remote_tables = inspector.get_table_names()

    # Get the list of tables defined in the SQLModel metadata
    expected_tables = SQLModel.metadata.tables.keys()

    # Check for missing tables in the remote database
    missing_tables = set(expected_tables) - set(remote_tables)
    if missing_tables:
        warnings.warn(
            f"The following tables are defined in the SQLModel metadata but are missing in the remote database: {missing_tables}",
            stacklevel=1,
        )
        return False

    # Check for extra tables in the remote database
    extra_tables = set(remote_tables) - set(expected_tables)
    if extra_tables:
        warnings.warn(
            f"The following tables are present in the remote database but are not defined in the SQLModel metadata: {extra_tables}",
            stacklevel=1,
        )
        return False

    print(
        "Schema validation passed: The remote database schema matches the expected schema."
    )
    return True


def init_schema():
    # Create a new SQLite database file and initialize the schema there.
    # Instead of creating the database in the engine's URL, we will create it in the current directory with a fixed name, and then copy data from the remote database to this local SQLite database.
    if os.path.exists(LOCAL_SQLITE_DB_PATH):
        warnings.warn(
            f"{LOCAL_SQLITE_DB_PATH} already exists. It will be overwritten.",
            stacklevel=1,
        )
        os.remove(LOCAL_SQLITE_DB_PATH)
    SQLModel.metadata.create_all(local_engine)
    print("Database tables initialized.")


if __name__ == "__main__":
    print("Connecting to the database...")
    if not ensure_remote_database_exists():
        print("Remote database does not exist. Please check your configuration.")
        exit(1)
    else:
        print("Remote database exists. Proceeding with initialization.")
        init_schema()
        print("Database initialization complete.")
        print("Validating schema of the remote database...")
        if not validate_schema():
            print(
                "Schema validation failed. Please check the warnings and fix the schema of the remote database."
            )
            exit(1)
        print("Copying data from remote Postgres database to local SQLite database...")
        copy_data_from_postgres_to_sqlite()
