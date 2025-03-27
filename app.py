from flask import Flask, request, jsonify, render_template, flash, redirect, url_for
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_cors import CORS
from models import db, User, Question, Choice, CatBreed, UserResponse, connect_db, UserQuestionnaire, QuizResult
from flask_wtf.csrf import CSRFProtect
import os
from dotenv import load_dotenv
import requests
from werkzeug.security import generate_password_hash, check_password_hash
from forms_module import RegistrationForm, LoginForm

import logging
from sqlalchemy import text
from collections import Counter

# Load environment variables first
load_dotenv()

app = Flask(__name__)
CORS(app)

# Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'purrfect_paws_secret_key_2024_secure_xyz123')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://patsaya@localhost:5432/purrfect_paws')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = True
app.config['WTF_CSRF_ENABLED'] = True
app.config['WTF_CSRF_SECRET_KEY'] = os.getenv('SECRET_KEY', 'purrfect_paws_secret_key_2024_secure_xyz123')
app.config['DEBUG'] = True
app.config['SESSION_COOKIE_SECURE'] = True  
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Set port configuration
PORT = 5001

# Initialize database
connect_db(app)

# Initialize login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Initialize CSRF protection
csrf = CSRFProtect(app)

# Get API key
CAT_API_KEY = os.getenv('CAT_API_KEY')

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Questions data
QUESTIONS = [
    {
        "questionNumber": 1,
        "question": "How active are you daily?",
        "answers": ["Couch potato (Calm)", "Moderately active (Playful)", "Highly energetic (Active)"]
    },
    {
        "questionNumber": 2,
        "question": "Where do you live?",
        "answers": ["Apartment", "House", "Rural area"]
    },
    {
        "questionNumber": 3,
        "question": "How much time can you spend daily interacting with your cat?",
        "answers": ["Less than 1 hour", "1–3 hours", "More than 3 hours"]
    },
    {
        "questionNumber": 4,
        "question": "Do you want a clingy 'lap cat' or an independent cat?",
        "answers": ["Clingy lap cat", "Balanced", "Independent cat"]
    },
    {
        "questionNumber": 5,
        "question": "Are you willing to brush your cat daily?",
        "answers": ["Yes, daily brushing", "Weekly brushing", "Prefer low-maintenance"]
    },
    {
        "questionNumber": 6,
        "question": "Do you have children or other pets?",
        "answers": ["Yes, children/pets", "Occasional visitors", "No, live alone"]
    },
    {
        "questionNumber": 7,
        "question": "Are you okay with a vocal, chatty cat?",
        "answers": ["Yes, love chatty cats", "Moderate vocalization", "Prefer quiet cats"]
    },
    {
        "questionNumber": 8,
        "question": "What's your experience with cats?",
        "answers": ["First-time owner", "Some experience", "Very experienced"]
    },
    {
        "questionNumber": 9,
        "question": "Do you travel often?",
        "answers": ["Often travel", "Occasionally travel", "Rarely travel"]
    },
    {
        "questionNumber": 10,
        "question": "Would you prefer a kitten or adult cat?",
        "answers": ["Kitten", "No preference", "Adult cat"]
    }
]

@login_manager.user_loader
def load_user(user_id):
    try:
        return User.query.get(int(user_id))
    except Exception as e:
        logger.error(f"Error loading user: {e}")
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = RegistrationForm()
    
    if form.validate_on_submit():
        try:
            logger.debug(f"Registration attempt for username: {form.username.data}, email: {form.email.data}")
            
            # Check if username or email already exists
            existing_username = User.query.filter_by(username=form.username.data).first()
            if existing_username:
                logger.debug("Username already registered")
                flash('Username already exists', 'danger')
                return render_template('register.html', form=form)
            
            existing_email = User.query.filter_by(email=form.email.data).first()
            if existing_email:
                logger.debug("Email already registered")
                flash('Email already registered. Please use a different email.', 'danger')
                return render_template('register.html', form=form)
            
            logger.debug("Creating new user")
            # Create new user with password
            user = User(
                username=form.username.data,
                email=form.email.data
            )
            user.set_password(form.password.data)
            
            logger.debug("Adding user to database")
            db.session.add(user)
            
            try:
                logger.debug("Committing transaction")
                db.session.commit()
                logger.debug("Registration successful")
                flash('Registration successful! Please log in.', 'success')
                return redirect(url_for('login'))
            except Exception as commit_error:
                logger.error(f"Database commit error: {str(commit_error)}")
                db.session.rollback()
                raise commit_error
            
        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            logger.error(f"Error type: {type(e)}")
            logger.error(f"Error details: {e.__dict__}")
            logger.error(f"Form data: username={form.username.data}, email={form.email.data}")
            logger.error(f"Database URL: {app.config['SQLALCHEMY_DATABASE_URI']}")
            db.session.rollback()
            flash('Registration failed. Please try again.', 'danger')
    else:
        logger.debug(f"Form validation errors: {form.errors}")
        logger.debug(f"Form data: {form.data}")
    
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    try:
        if current_user.is_authenticated:
            return redirect(url_for('index'))
        
        form = LoginForm()
        if form.validate_on_submit():
            logger.debug(f"Login attempt for email: {form.email.data}")
            try:
                user = User.query.filter_by(email=form.email.data).first()
                if user and user.check_password(form.password.data):
                    logger.debug("Password check successful")
                    login_user(user)
                    flash(f'Welcome back, {user.username}!', 'success')
                    next_page = request.args.get('next')
                    return redirect(next_page or url_for('index'))
                else:
                    logger.debug("Invalid credentials")
                    flash('Invalid email or password', 'danger')
                    return render_template('login.html', form=form)
            except Exception as db_error:
                logger.error(f"Database error during login: {str(db_error)}")
                flash('An error occurred. Please try again.', 'danger')
                return render_template('login.html', form=form)
        else:
            logger.debug(f"Form validation errors: {form.errors}")
            return render_template('login.html', form=form)
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        flash('An error occurred. Please try again.', 'danger')
        return render_template('login.html', form=form)
    
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out', 'success')
    return redirect(url_for('index'))

@app.route('/questionnaire', methods=['GET', 'POST'])
@login_required
def questionnaire():
    """Render the questionnaire page and handle form submission."""
    if request.method == 'POST':
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'message': 'No data received'}), 400
                
            answers = data.get('answers', {})
            if not answers:
                return jsonify({'success': False, 'message': 'No answers provided'}), 400

            # Create keyword counter from answers
            keywords = []
            for answer in answers.values():
                keywords.extend(answer.lower().split())

            keyword_counts = Counter(keywords)
            
            # Get all breeds
            breeds = CatBreed.query.all()
            best_match = None
            best_score = 0
            breed_scores = []

            for breed in breeds:
                score = 0
                attributes = breed.attributes.lower()
                
                # Match keywords against breed attributes
                for keyword in keywords:
                    if keyword in attributes:
                        score += 1

                # Store breed and its score
                breed_scores.append({
                    'name': breed.name,
                    'score': score,
                    'attributes': breed.attributes
                })

                # Update best match if this breed has a higher score
                if score > best_score:
                    best_score = score
                    best_match = breed

            # Sort breeds by score
            breed_scores.sort(key=lambda x: x['score'], reverse=True)

            # Save questionnaire
            questionnaire = UserQuestionnaire(
                user_id=current_user.id,
                answers=answers,
                completed=True,
                matched_breed_id=best_match.id if best_match else None
            )
            db.session.add(questionnaire)
            db.session.commit()

            return jsonify({
                'success': True,
                'redirect': '/results',
                'breed_scores': breed_scores[:1]  
            })

        except Exception as e:
            logger.error(f"Questionnaire submission error: {str(e)}")
            db.session.rollback()
            return jsonify({
                'success': False,
                'message': 'An error occurred while processing your submission'
            }), 500

    return render_template('questionnaire.html')

@app.route('/api/questionnaire', methods=['GET'])
@login_required
def get_questionnaire():
    questionnaire = UserQuestionnaire.query.filter_by(
        user_id=current_user.id, completed=False
    ).order_by(UserQuestionnaire.created_at.desc()).first()
    
    return jsonify({
        'questions': QUESTIONS,
        'current_answers': questionnaire.answers if questionnaire else {}
    })

@app.route('/results')
@login_required
def results():
    """Display the matched cat breeds based on questionnaire answers."""
    # Get the most recent completed questionnaire
    questionnaire = UserQuestionnaire.query.filter_by(
        user_id=current_user.id, completed=True
    ).order_by(UserQuestionnaire.created_at.desc()).first()
    
    if not questionnaire or not questionnaire.matched_breed_id:
        flash('Please complete the questionnaire first.', 'warning')
        return redirect(url_for('questionnaire'))
    
    # Get the matched breed
    breed = CatBreed.query.get(questionnaire.matched_breed_id)
    if not breed:
        flash('Error finding matched breed. Please try the questionnaire again.', 'error')
        return redirect(url_for('questionnaire'))
    
    # Get all breeds and calculate scores
    breeds = CatBreed.query.all()
    breed_scores = []
    
    # Create keyword counter from answers
    keywords = []
    for answer in questionnaire.answers.values():
        keywords.extend(answer.lower().split())
    
    keyword_counts = Counter(keywords)
    
    for b in breeds:
        score = 0
        attributes = b.attributes.lower()
        
        # Match keywords against breed attributes
        for keyword in keywords:
            if keyword in attributes:
                score += 1
        
        breed_scores.append({
            'name': b.name,
            'score': score,
            'attributes': b.attributes,
            'image_url': b.image_url
        })
    
    # Sort breeds by score
    breed_scores.sort(key=lambda x: x['score'], reverse=True)
    
    return render_template('results.html', breed_scores=breed_scores[:1])  # Show only the best match

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500

def verify_db_setup():
    """Verify database setup and tables"""
    try:
        with app.app_context():
            # Check if tables exist
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            logger.debug(f"Existing tables: {tables}")
            
            # Check if users table exists and has correct columns
            if 'users' in tables:
                columns = inspector.get_columns('users')
                column_names = [col['name'] for col in columns]
                logger.debug(f"Users table columns: {column_names}")
                
                # Check constraints
                constraints = inspector.get_check_constraints('users')
                logger.debug(f"Users table constraints: {constraints}")
                
                # Check indexes
                indexes = inspector.get_indexes('users')
                logger.debug(f"Users table indexes: {indexes}")
            else:
                logger.error("Users table does not exist!")
                return False

            # Check if cat_breeds table exists and has data
            if 'cat_breeds' in tables:
                breed_count = CatBreed.query.count()
                logger.debug(f"Number of cat breeds in database: {breed_count}")
                
                if breed_count == 0:
                    logger.error("No cat breeds found in database!")
                    return False
            else:
                logger.error("Cat breeds table does not exist!")
                return False
            
            return True
    except Exception as e:
        logger.error(f"Database verification error: {str(e)}")
        logger.error(f"Error type: {type(e)}")
        logger.error(f"Error details: {e.__dict__}")
        return False

# Create database tables
def init_db():
    with app.app_context():
        logger.debug("Checking database tables...")
        # Create tables if they don't exist
        db.create_all()
        
        # Always fetch breeds from API to ensure we have the latest data
        logger.debug("Fetching cat breeds from API...")
        try:
            # Clear related tables first to avoid foreign key violations
            UserQuestionnaire.query.delete()
            QuizResult.query.delete()
            UserResponse.query.delete()
            db.session.commit()
            
            # Clear existing breeds
            CatBreed.query.delete()
            db.session.commit()
            
            # Fetch breeds from API
            fetch_cat_breeds()
            
            # Verify breeds were fetched
            breed_count = CatBreed.query.count()
            logger.info(f"Successfully fetched {breed_count} cat breeds from API")
            
            if breed_count == 0:
                logger.error("No breeds were fetched from the API!")
                raise Exception("Failed to fetch cat breeds from API")
                
        except Exception as e:
            logger.error(f"Failed to fetch cat breeds: {str(e)}")
            raise
        
        # Verify the database setup
        if not verify_db_setup():
            logger.error("Database setup verification failed!")
            raise Exception("Database setup verification failed")
            
        logger.info("Database initialization completed successfully")

def fetch_cat_breeds():
    """Fetch cat breeds from The Cat API and store them in the database."""
    try:
        if not CAT_API_KEY:
            logger.error("CAT_API_KEY is not set!")
            raise ValueError("CAT_API_KEY is not set")

        headers = {
            "x-api-key": CAT_API_KEY,
            "Accept": "application/json"
        }
        
        logger.info("Starting to fetch cat breeds from The Cat API...")
        
        # Fetch all breeds
        response = requests.get("https://api.thecatapi.com/v1/breeds", headers=headers)
        response.raise_for_status()
        breeds_data = response.json()
        
        if not breeds_data:
            logger.error("No breeds data received from API!")
            raise ValueError("No breeds data received from API")
            
        logger.info(f"Successfully fetched {len(breeds_data)} breeds from The Cat API")
        
        # Clear existing breeds first
        CatBreed.query.delete()
        db.session.commit()
        
        # Process each breed
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
                
                # Get breed ID for image fetching
                breed_id = breed_data['id']
                
                # Create new breed with breed ID as image_url
                new_breed = CatBreed(
                    name=breed_data['name'],
                    attributes="\n".join(attributes),
                    image_url=breed_id  # Store the breed ID for image fetching
                )
                
                db.session.add(new_breed)
                logger.debug(f"Added new breed: {breed_data['name']} with ID: {breed_id}")
                
            except Exception as e:
                logger.error(f"Error processing breed {breed_data.get('name', 'unknown')}: {str(e)}")
                continue
        
        # Commit all breeds
        db.session.commit()
        logger.info(f"Successfully committed {len(breeds_data)} breeds to database")
        
        # Verify the number of breeds in the database
        breed_count = CatBreed.query.count()
        logger.info(f"Current number of breeds in database: {breed_count}")
        
        if breed_count == 0:
            logger.error("No breeds were added to the database!")
            raise Exception("Failed to add breeds to database")
            
        if breed_count != len(breeds_data):
            logger.error(f"Warning: Number of breeds in database ({breed_count}) does not match number fetched from API ({len(breeds_data)})")
        
        return True
        
    except Exception as e:
        logger.error(f"Error fetching cat breeds: {str(e)}")
        db.session.rollback()
        raise

def check_cat_breeds():
    """Check the number and details of cat breeds in the database"""
    try:
        with app.app_context():
            # Get total count of cat breeds
            breed_count = CatBreed.query.count()
            logger.debug(f"Total number of cat breeds in database: {breed_count}")
            
            # Get all cat breeds
            breeds = CatBreed.query.all()
            logger.debug("Cat breeds in database:")
            for breed in breeds:
                logger.debug(f"- {breed.name}: {breed.attributes}")
            
            return breed_count
    except Exception as e:
        logger.error(f"Error checking cat breeds: {str(e)}")
        return 0

if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(debug=True, port=PORT, host='0.0.0.0')
  