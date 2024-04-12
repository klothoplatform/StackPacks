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

        cursor.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (event["database_name"],)
        )
        if cursor.fetchone() is None:
            # The database does not exist, create it
            cursor.execute(
                sql.SQL("CREATE DATABASE {}").format(
                    sql.Identifier(event["database_name"])
                )
            )
        return {
            "StatusCode": 200,
            "body": f"Database {event['database_name']} successfully created.",
        }
    except Exception as e:
        print(f"Database creation failed: {str(e)}")
        return {
            "StatusCode": 500,
            "body": f"Database creation failed: {str(e)}",
        }
    finally:
        cursor.close()
