import os
import sys

import psycopg2
from psycopg2 import sql

try:
    rds_host = os.environ.get("DB_HOST")
    password = os.environ.get("DB_PASSWORD")
    user = os.environ.get("DB_USER")
    print(f"Connecting to {rds_host} as {user}")
    conn = psycopg2.connect(
        dbname="postgres", user=user, password=password, host=rds_host
    )
    conn.autocommit = True
except Exception as e:
    print(f"Database connection failed: {str(e)}")
    sys.exit()


def lambda_handler(event, context):
    print(f"Creating database {event['database_name']}")

    try:
        cursor = conn.cursor()
        create_database(event["database_name"], cursor)
        connection_string = create_connection_string("postgres", event["database_name"])

        return {
            "StatusCode": 200,
            "ConnectionString": connection_string,
        }
    except Exception as e:
        print(f"Database creation failed: {str(e)}")
        return {
            "StatusCode": 500,
            "body": f"Database creation failed: {str(e)}",
        }
    finally:
        cursor.close()


def create_database(database_name: str, cursor: psycopg2.extensions.cursor):

    cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (database_name,))
    if cursor.fetchone() is None:
        # The database does not exist, create it
        cursor.execute(
            sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name))
        )


def create_connection_string(engine: str, database_name: str):
    if engine == "postgres":
        return f"postgresql://{user}:{password}@{rds_host}/{database_name}"
    else:
        raise ValueError(f"Unsupported engine: {engine}")
