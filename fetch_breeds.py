from dotenv import load_dotenv
import os
import requests
from models import db, Breed
from app import app
import logging

# Set up logging
logger = logging.getLogger(__name__)

def fetch_cat_breeds():
    """Fetch cat breeds from The Cat API and store them in the database."""
    try:
        # Load environment variables
        load_dotenv()
        CAT_API_KEY = os.getenv('CAT_API_KEY')
        
        if not CAT_API_KEY:
            logger.error("CAT_API_KEY is not set!")
            raise ValueError("CAT_API_KEY is not set")

        headers = {
            "x-api-key": CAT_API_KEY,
            "Accept": "application/json"
        }
        
        logger.info("Starting to fetch cat breeds from The Cat API...")
        
        # Fetch all breeds
        response = requests.get("https://api.thecatapi.com/v1/breeds", headers=headers, timeout=15)
        response.raise_for_status()
        breeds_data = response.json()
        
        if not breeds_data:
            logger.error("No breeds data received from API!")
            raise ValueError("No breeds data received from API")
            
        logger.info(f"Successfully fetched {len(breeds_data)} breeds from The Cat API")
        
        # Get all existing breeds
        breed_map = {breed.api_breed_id: breed for breed in Breed.query.filter_by(species='cat').all()}
        
        # Process each breed from the API
        for breed_data in breeds_data:
            try:
                # Create detailed attributes string
                attributes = []
                if breed_data.get('temperament'):
                    attributes.append(f"Temperament: {breed_data['temperament']}")
                if breed_data.get('description'):
                    attributes.append(f"Description: {breed_data['description']}")
                if breed_data.get('origin'):
                    attributes.append(f"Origin: {breed_data['origin']}")
                if breed_data.get('life_span'):
                    attributes.append(f"Life Span: {breed_data['life_span']} years")
                if breed_data.get('weight'):
                    attributes.append(f"Weight: {breed_data['weight'].get('metric', 'N/A')} kg")
                if breed_data.get('adaptability'):
                    attributes.append(f"Adaptability: {breed_data['adaptability']}/5")
                if breed_data.get('child_friendly'):
                    attributes.append(f"Child Friendly: {breed_data['child_friendly']}/5")
                if breed_data.get('dog_friendly'):
                    attributes.append(f"Dog Friendly: {breed_data['dog_friendly']}/5")
                if breed_data.get('energy_level'):
                    attributes.append(f"Energy Level: {breed_data['energy_level']}/5")
                if breed_data.get('grooming'):
                    attributes.append(f"Grooming: {breed_data['grooming']}/5")
                if breed_data.get('health_issues'):
                    attributes.append(f"Health Issues: {breed_data['health_issues']}/5")
                if breed_data.get('intelligence'):
                    attributes.append(f"Intelligence: {breed_data['intelligence']}/5")
                if breed_data.get('shedding_level'):
                    attributes.append(f"Shedding Level: {breed_data['shedding_level']}/5")
                if breed_data.get('social_needs'):
                    attributes.append(f"Social Needs: {breed_data['social_needs']}/5")
                if breed_data.get('stranger_friendly'):
                    attributes.append(f"Stranger Friendly: {breed_data['stranger_friendly']}/5")
                if breed_data.get('vocalisation'):
                    attributes.append(f"Vocalisation: {breed_data['vocalisation']}/5")
                
                # Get breed ID and reference image
                breed_id = breed_data['id']
                if not breed_id or not breed_data.get('name'):
                    raise ValueError('missing breed ID or name')
                image_url = (breed_data.get('image') or {}).get('url')
                
                # Update existing breed or create new one
                if breed_id in breed_map:
                    breed = breed_map[breed_id]
                    breed.name = breed_data['name']
                    breed.attributes = "\n".join(attributes)
                    if image_url:
                        breed.image_url = image_url
                    logger.debug(f"Updated existing breed: {breed_data['name']} with ID: {breed_id}")
                else:
                    new_breed = Breed(
                        name=breed_data['name'],
                        attributes="\n".join(attributes),
                        species='cat',
                        api_breed_id=breed_id,
                        image_url=image_url
                    )
                    db.session.add(new_breed)
                    breed_map[breed_id] = new_breed
                    logger.debug(f"Added new breed: {breed_data['name']} with ID: {breed_id}")
                
            except Exception as e:
                logger.error("Rejected cat breed API record id=%r: %s", breed_data.get('id'), e)
                continue
        
        # Commit all changes
        db.session.commit()
        logger.info(f"Successfully updated/added breeds to database")
        
        # Verify the number of breeds in the database
        breed_count = Breed.query.filter_by(species='cat').count()
        logger.info(f"Current number of breeds in database: {breed_count}")
        
        if breed_count == 0:
            logger.error("No breeds were added to the database!")
            raise Exception("Failed to add breeds to database")
        
        return True
        
    except Exception as e:
        logger.error(f"Error fetching cat breeds: {str(e)}")
        db.session.rollback()
        raise

if __name__ == '__main__':
    with app.app_context():
        # Fetch breeds
        fetch_cat_breeds()
