from flask import Flask, request, jsonify, render_template, flash, redirect, url_for, session
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_cors import CORS
from models import db, User, Question, Choice, Breed, UserResponse, connect_db, UserQuestionnaire, QuizResult
from flask_wtf.csrf import CSRFProtect
import os
import secrets
import re
from dotenv import load_dotenv

from werkzeug.security import generate_password_hash, check_password_hash
from forms_module import RegistrationForm, LoginForm

import logging
from sqlalchemy import text

# Load environment variables first
load_dotenv()

app = Flask(__name__)
CORS(app)

# Configuration
debug_enabled = os.getenv('FLASK_DEBUG', '').lower() in ('1', 'true', 'yes')
secret_key = os.getenv('SECRET_KEY')
if not secret_key and not debug_enabled:
    raise RuntimeError('SECRET_KEY must be set when debug mode is disabled')
app.config['SECRET_KEY'] = secret_key or secrets.token_hex(32)
database_url = os.getenv('DATABASE_URL', 'postgresql://patsaya@localhost:5432/purrfect_paws')
app.config['SQLALCHEMY_DATABASE_URI'] = database_url.replace('postgres://', 'postgresql://', 1) if database_url.startswith('postgres://') else database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = os.getenv('SQLALCHEMY_ECHO', '').lower() in ('1', 'true', 'yes')
app.config['WTF_CSRF_ENABLED'] = True
app.config['DEBUG'] = debug_enabled
app.config['SESSION_COOKIE_SECURE'] = os.getenv('SESSION_COOKIE_SECURE', '').lower() in ('1', 'true', 'yes')
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
DOG_API_KEY = os.getenv('DOG_API_KEY')

# Set up logging
logging.basicConfig(level=logging.DEBUG if debug_enabled else logging.INFO)
logger = logging.getLogger(__name__)

# Questions data
CAT_QUESTIONS = [
    {
        "id": "c1", "questionNumber": 1,
        "question": "How active are you daily?",
        "answers": ["Couch potato (Calm)", "Moderately active (Playful)", "Highly energetic (Active)"]
    },
    {
        "id": "c2", "questionNumber": 2,
        "question": "Where do you live?",
        "answers": ["Apartment", "House", "Rural area"]
    },
    {
        "id": "c3", "questionNumber": 3,
        "question": "How much time can you spend daily interacting with your cat?",
        "answers": ["Less than 1 hour", "1–3 hours", "More than 3 hours"]
    },
    {
        "id": "c4", "questionNumber": 4,
        "question": "Do you want a clingy 'lap cat' or an independent cat?",
        "answers": ["Clingy lap cat", "Balanced", "Independent cat"]
    },
    {
        "id": "c5", "questionNumber": 5,
        "question": "Are you willing to brush your cat daily?",
        "answers": ["Yes, daily brushing", "Weekly brushing", "Prefer low-maintenance"]
    },
    {
        "id": "c6", "questionNumber": 6,
        "question": "Do you have children or other pets?",
        "answers": ["Yes, children/pets", "Occasional visitors", "No, live alone"]
    },
    {
        "id": "c7", "questionNumber": 7,
        "question": "Are you okay with a vocal, chatty cat?",
        "answers": ["Yes, love chatty cats", "Moderate vocalization", "Prefer quiet cats"]
    },
    {
        "id": "c8", "questionNumber": 8,
        "question": "What's your experience with cats?",
        "answers": ["First-time owner", "Some experience", "Very experienced"]
    },
    {
        "id": "c9", "questionNumber": 9,
        "question": "Do you travel often?",
        "answers": ["Often travel", "Occasionally travel", "Rarely travel"]
    },
    {
        "id": "c10", "questionNumber": 10,
        "question": "Would you prefer a kitten or adult cat?",
        "answers": ["Kitten", "No preference", "Adult cat"]
    }
]

DOG_QUESTIONS = [
    {"id": "d1", "question": "Preferred dog size?", "answers": ["Small", "Medium", "Large"]},
    {"id": "d2", "question": "How active are you daily?", "answers": ["Relaxed", "Moderately active", "Very active"]},
    {"id": "d3", "question": "How much daily exercise can you provide?", "answers": ["Under 30 minutes", "30–60 minutes", "More than 60 minutes"]},
    {"id": "d4", "question": "Where do you live?", "answers": ["Apartment", "House with limited outdoor space", "House with a yard"]},
    {"id": "d5", "question": "What is your dog-owning experience?", "answers": ["First-time owner", "Some experience", "Very experienced"]},
    {"id": "d6", "question": "How long will your dog usually be home alone?", "answers": ["Rarely — less than 2 hours", "Sometimes — 2 to 6 hours", "Often — more than 6 hours"]},
    {"id": "d7", "question": "Will the dog live with children?", "answers": ["Yes", "Sometimes", "No"]},
    {"id": "d8", "question": "Will the dog live with other pets?", "answers": ["Yes", "Sometimes", "No"]},
    {"id": "d9", "question": "What personality do you prefer?", "answers": ["Calm and gentle", "Friendly and playful", "Alert and protective"]},
    {"id": "d10", "question": "What kind of companion are you looking for?", "answers": ["Lap or companion dog", "Family dog", "Outdoor, sporting, or working dog"]},
]

QUESTION_SETS = {'cat': CAT_QUESTIONS, 'dog': DOG_QUESTIONS}


def score_dog_breed(breed, answers):
    """Score a dog with simple lifestyle, temperament and purpose clues."""
    details = (breed.attributes or '').lower()
    score = 0
    weight_line = next((line for line in details.splitlines() if line.startswith('weight:')), '')
    weights = [float(value) for value in re.findall(r'\d+(?:\.\d+)?', weight_line)]
    if weights:
        weight = sum(weights[:2]) / min(len(weights), 2)
        size = answers['d1']
        if ((size == 'Small' and weight < 10) or
                (size == 'Medium' and 10 <= weight < 25) or
                (size == 'Large' and weight >= 25)):
            score += 3  # A practical size match is the strongest signal.
    else:
        height_line = next((line for line in details.splitlines() if line.startswith('height:')), '')
        heights = [float(value) for value in re.findall(r'\d+(?:\.\d+)?', height_line)]
        if heights:
            height = sum(heights[:2]) / min(len(heights), 2)
            size = answers['d1']
            if ((size == 'Small' and height < 35) or
                    (size == 'Medium' and 35 <= height < 55) or
                    (size == 'Large' and height >= 55)):
                score += 3  # Height helps when the API has no usable weight.

    # Temperament and original purpose provide useful, but imperfect, clues.
    personality_words = {
        'Calm and gentle': ('calm', 'gentle', 'easygoing'),
        'Friendly and playful': ('friendly', 'playful', 'outgoing'),
        'Alert and protective': ('alert', 'protective', 'watchdog'),
    }
    if any(word in details for word in personality_words[answers['d9']]):
        score += 2
    purpose_words = {
        'Lap or companion dog': ('companion', 'lap', 'toy'),
        'Family dog': ('family', 'friendly', 'gentle'),
        'Outdoor, sporting, or working dog': ('sporting', 'working', 'hunting', 'herding', 'retriev'),
    }
    if any(word in details for word in purpose_words[answers['d10']]):
        score += 2
    if answers['d7'] == 'Yes' and any(word in details for word in ('child', 'family', 'gentle')):
        score += 2
    if answers['d8'] == 'Yes' and any(word in details for word in ('dog friendly', 'social', 'friendly')):
        score += 2

    active = any(word in details for word in ('energetic', 'active', 'sporting', 'working', 'hunting', 'herding'))
    calm = any(word in details for word in ('calm', 'gentle', 'companion', 'toy'))
    if answers['d2'] == 'Very active' and active or answers['d2'] == 'Relaxed' and calm:
        score += 1
    if answers['d3'] == 'More than 60 minutes' and active or answers['d3'] == 'Under 30 minutes' and calm:
        score += 1
    if answers['d4'] == 'Apartment' and calm or answers['d4'] == 'House with a yard' and active:
        score += 1
    if answers['d5'] == 'First-time owner' and calm or answers['d5'] == 'Very experienced' and active:
        score += 1
    if answers['d6'] == 'Often — more than 6 hours' and 'independent' in details:
        score += 1
    return score


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
    """Choose a species, validate its answers, and save one match."""
    if request.method == 'GET':
        session['questionnaire_token'] = secrets.token_urlsafe(24)
        return render_template('questionnaire.html', submission_token=session['questionnaire_token'])

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({'success': False, 'message': 'Send questionnaire answers as JSON.'}), 400
    species = data.get('species')
    if not isinstance(species, str) or species not in QUESTION_SETS:
        return jsonify({'success': False, 'message': 'Choose cat or dog.'}), 400
    answers = data.get('answers')
    questions = QUESTION_SETS[species]
    expected_ids = {question['id'] for question in questions}
    if not isinstance(answers, dict) or set(answers) != expected_ids:
        return jsonify({'success': False, 'message': 'Answer all 10 questions with no extra answers.'}), 400
    for question in questions:
        if answers[question['id']] not in question['answers']:
            return jsonify({'success': False, 'message': f"Invalid answer for {question['id']}."}), 400
    token = data.get('submission_token')
    if not token or token != session.get('questionnaire_token'):
        return jsonify({'success': False, 'message': 'This quiz was already submitted. Start a new quiz to try again.'}), 409

    breeds = Breed.query.filter_by(species=species).all()
    if not breeds:
        return jsonify({'success': False, 'message': f'No {species} breeds are available yet.'}), 503

    if species == 'cat':
        # Keep the existing cat keyword matching behavior.
        keywords = [word for answer in answers.values() for word in answer.lower().split()]
        score = lambda breed: sum(word in (breed.attributes or '').lower() for word in keywords)
    else:
        score = lambda breed: score_dog_breed(breed, answers)
    # Name and ID make ties deterministic. A zero-score result is still useful
    # as a starting point when imported attributes are incomplete.
    best_match = min(breeds, key=lambda breed: (-score(breed), breed.name.lower(), breed.id))
    try:
        saved = UserQuestionnaire(
            user_id=current_user.id, species=species, answers=answers,
            completed=True, matched_breed_id=best_match.id,
        )
        db.session.add(saved)
        db.session.commit()
        session.pop('questionnaire_token', None)
        return jsonify({'success': True, 'redirect': url_for('results')})
    except Exception:
        db.session.rollback()
        logger.exception('Questionnaire submission failed')
        return jsonify({'success': False, 'message': 'Could not save your match. Please try again.'}), 500


@app.route('/api/questionnaire', methods=['GET'])
@login_required
def get_questionnaire():
    species = request.args.get('species')
    if species not in QUESTION_SETS:
        return jsonify({'message': 'Choose cat or dog.'}), 400
    questionnaire = UserQuestionnaire.query.filter_by(
        user_id=current_user.id, completed=False, species=species
    ).order_by(UserQuestionnaire.created_at.desc()).first()
    return jsonify({
        'species': species,
        'questions': QUESTION_SETS[species],
        'current_answers': questionnaire.answers if questionnaire else {},
    })


@app.route('/results')
@login_required
def results():
    """Display the saved breed match for the completed questionnaire."""
    # Get the most recent completed questionnaire
    questionnaire = UserQuestionnaire.query.filter_by(
        user_id=current_user.id, completed=True
    ).order_by(UserQuestionnaire.created_at.desc()).first()
    
    if not questionnaire:
        flash('Please complete the questionnaire first.', 'warning')
        return redirect(url_for('questionnaire'))
    if not questionnaire.matched_breed_id:
        flash('No matched breed is available for this questionnaire.', 'warning')
        return redirect(url_for('questionnaire'))
    
    # Get the matched breed
    breed = db.session.get(Breed, questionnaire.matched_breed_id)
    if not breed or breed.species != questionnaire.species:
        flash('The saved breed match is missing or has the wrong species.', 'error')
        return redirect(url_for('questionnaire'))

    return render_template('results.html', breed_scores=[breed], species=questionnaire.species)

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

            # Check if unified breeds table exists and has cat data
            if 'breeds' in tables:
                breed_count = Breed.query.filter_by(species='cat').count()
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
        
        # Existing breed IDs must stay stable for saved results
        logger.debug("Checking cat breed data...")
        try:
            # Keep saved users and results; fetch only for an empty breed table.
            if Breed.query.filter_by(species='cat').count() == 0 and CAT_API_KEY:
                fetch_cat_breeds()
            if Breed.query.filter_by(species='dog').count() == 0 and DOG_API_KEY:
                fetch_dog_breeds()
            
            # Verify breeds were fetched
            breed_count = Breed.query.filter_by(species='cat').count()
            logger.info(f"Cat breeds available: {breed_count}")
            
            if breed_count == 0:
                logger.warning("No breeds are available yet; run breed initialization after setting CAT_API_KEY")
            logger.info("Dog breeds available: %s", Breed.query.filter_by(species='dog').count())
                
        except Exception as e:
            logger.error(f"Failed to initialize breeds: {str(e)}")
            raise
        
        logger.info("Database initialization completed successfully")

def fetch_cat_breeds():
    """Fetch cat breeds through the shared, non-destructive importer."""
    from fetch_breeds import fetch_cat_breeds as fetch
    return fetch()

def fetch_dog_breeds():
    """Fetch dog breeds through the non-destructive importer."""
    from fetch_breeds import fetch_dog_breeds as fetch
    return fetch()

def check_cat_breeds():
    """Check the number and details of cat breeds in the database"""
    try:
        with app.app_context():
            # Get total count of cat breeds
            breed_count = Breed.query.filter_by(species='cat').count()
            logger.debug(f"Total number of cat breeds in database: {breed_count}")
            
            # Get all cat breeds
            breeds = Breed.query.filter_by(species='cat').all()
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
    app.run(port=PORT, host='0.0.0.0')
