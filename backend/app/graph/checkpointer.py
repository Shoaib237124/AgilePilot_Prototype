from contextlib import contextmanager

from langgraph.checkpoint.postgres import PostgresSaver

from app.database.database import (
    USER,
    PASSWORD,
    HOST,
    PORT,
    DBNAME,
)


def get_database_uri() -> str:

    return (
        f"postgresql://"
        f"{USER}:{PASSWORD}@"
        f"{HOST}:{PORT}/"
        f"{DBNAME}"
        f"?sslmode=require"
    )


@contextmanager
def create_checkpointer():

    database_uri = get_database_uri()

    with PostgresSaver.from_conn_string(
        database_uri
    ) as checkpointer:

        checkpointer.setup()

        yield checkpointer