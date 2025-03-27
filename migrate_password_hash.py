from app import app, db
from sqlalchemy import text

def migrate_password_hash():
    with app.app_context():
        # Alter the password_hash column to be longer
        db.session.execute(text('ALTER TABLE users ALTER COLUMN password_hash TYPE VARCHAR(256)'))
        db.session.commit()
        print("Successfully updated password_hash column length")

if __name__ == '__main__':
    migrate_password_hash() 