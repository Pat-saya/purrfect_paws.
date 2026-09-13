"""Create missing tables and optionally upsert cat breeds."""
import os
from dotenv import load_dotenv
from app import app, db
from fetch_breeds import fetch_cat_breeds


def init_db():
    with app.app_context():
        db.create_all()
        if os.getenv('CAT_API_KEY'):
            fetch_cat_breeds()
        else:
            print('CAT_API_KEY is required to load cat breeds; existing tables are untouched.')


if __name__ == '__main__':
    load_dotenv()
    init_db()
