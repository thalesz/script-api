import psycopg2

from app.config.settings import settings


def get_connection():
    return psycopg2.connect(
        host=settings.PG_HOST,
        port=settings.PG_PORT,
        dbname=settings.PG_DATABASE,
        user=settings.PG_USER,
        password=settings.PG_PASSWORD,
    )
