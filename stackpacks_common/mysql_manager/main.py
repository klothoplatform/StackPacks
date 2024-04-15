import os

import pymysql


def lambda_handler(event, context):
    try:
        db_host = os.environ.get("DB_HOST")
        db_user = os.environ.get("DB_USER")
        db_password = os.environ.get("DB_PASSWORD")
        db_name = event["database_name"]

        print(f"Connecting to MySQL at {db_host} as {db_user}")
        conn = pymysql.connect(host=db_host, user=db_user, password=db_password)
        conn.autocommit(True)

        print(f"Creating database {db_name}")
        cursor = conn.cursor()
        create_database(cursor, db_name)

        connection_string = create_connection_string(
            db_host, db_user, db_password, db_name
        )

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
        if conn:
            conn.close()


def create_database(cursor, database_name):
    cursor.execute(f"SHOW DATABASES LIKE '{database_name}'")
    if not cursor.fetchone():
        # The database does not exist, create it
        cursor.execute(f"CREATE DATABASE {database_name}")


def create_connection_string(host, user, password, database_name):
    return f"mysql+pymysql://{user}:{password}@{host}/{database_name}"
