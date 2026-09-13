from app import app, db
from models import CatBreed
import requests
import os
from dotenv import load_dotenv

def init_db():
    with app.app_context():
        # Create all tables
        db.create_all()
        print("Created all database tables")

        # Check if we already have cat breeds
        if CatBreed.query.first() is None:
            # Load cat breeds from The Cat API
            CAT_API_KEY = os.getenv('CAT_API_KEY')
            if not CAT_API_KEY:
                print('CAT_API_KEY is required to load cat breeds; existing tables are untouched.')
                return
            headers = {'x-api-key': CAT_API_KEY}
            response = requests.get('https://api.thecatapi.com/v1/breeds', headers=headers, timeout=15)
            
            if response.status_code == 200:
                breeds = response.json()
                for breed in breeds:
                    # Create attributes string
                    attributes = f"temperament: {breed.get('temperament', '')}, "
                    attributes += f"origin: {breed.get('origin', '')}, "
                    attributes += f"description: {breed.get('description', '')}, "
                    attributes += f"life_span: {breed.get('life_span', '')}, "
                    attributes += f"adaptability: {breed.get('adaptability', '')}, "
                    attributes += f"affection_level: {breed.get('affection_level', '')}, "
                    attributes += f"child_friendly: {breed.get('child_friendly', '')}, "
                    attributes += f"dog_friendly: {breed.get('dog_friendly', '')}, "
                    attributes += f"energy_level: {breed.get('energy_level', '')}, "
                    attributes += f"grooming: {breed.get('grooming', '')}, "
                    attributes += f"health_issues: {breed.get('health_issues', '')}, "
                    attributes += f"intelligence: {breed.get('intelligence', '')}, "
                    attributes += f"shedding_level: {breed.get('shedding_level', '')}, "
                    attributes += f"social_needs: {breed.get('social_needs', '')}, "
                    attributes += f"stranger_friendly: {breed.get('stranger_friendly', '')}, "
                    attributes += f"vocalisation: {breed.get('vocalisation', '')}"

                    new_breed = CatBreed(
                        name=breed.get('name', ''),
                        attributes=attributes,
                        image_url=breed.get('id')
                    )
                    db.session.add(new_breed)
                
                db.session.commit()
                print(f"Added {len(breeds)} cat breeds to the database")
            else:
                print("Failed to fetch cat breeds from API")

if __name__ == '__main__':
    load_dotenv()
    init_db() 