"""
Unit Tests for Purrfect Paws Application

This test file contains basic unit tests for the core functionality of the Purrfect Paws application.
It tests:
1. User registration and login
2. Questionnaire submission
3. Cat breed matching
4. Basic route accessibility

Note: These tests use a test database to avoid affecting the production database.
"""

import unittest
import os
import tempfile
from unittest.mock import patch

# Choose an isolated database before Flask-SQLAlchemy is initialized.
_test_directory = tempfile.TemporaryDirectory()
os.environ['DATABASE_URL'] = 'sqlite:///' + os.path.join(_test_directory.name, 'test.sqlite3')
os.environ['SECRET_KEY'] = 'test-only-secret'
os.environ['SESSION_COOKIE_SECURE'] = '0'
from app import app, db, init_db
from models import User, Question, Choice, Breed, UserQuestionnaire, UserResponse, QuizResult
from werkzeug.security import generate_password_hash
from sqlalchemy.exc import IntegrityError

class TestPurrfectPaws(unittest.TestCase):
    """Test cases for Purrfect Paws application"""
    
    def setUp(self):
        """Set up test database and create test client"""
        # Configure test database
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF protection during testing
        self.client = app.test_client()
        
        # Create test database tables
        with app.app_context():
            db.create_all()
            
            # Create test cat breed
            test_breed = Breed(
                name='Test Breed',
                attributes='Adaptability: 3/5\nChild Friendly: 4/5\nDog Friendly: 3/5',
                species='cat', api_breed_id='test_breed', image_url='https://example.com/cat.jpg'
            )
            db.session.add(test_breed)
            db.session.commit()
    
    def tearDown(self):
        """Clean up after each test"""
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def login_test_user(self):
        with app.app_context():
            user = User(username='testuser', email='test@example.com')
            user.set_password('testpass123')
            db.session.add(user)
            db.session.commit()
            user_id = user.id
        self.client.post('/login', data={'email': 'test@example.com', 'password': 'testpass123'})
        return user_id

    def test_breed_constraints(self):
        with app.app_context():
            db.session.add(Breed(name='Duplicate', attributes='test', species='cat', api_breed_id='test_breed'))
            with self.assertRaises(IntegrityError):
                db.session.commit()
            db.session.rollback()
            db.session.add(Breed(name='Dog', attributes='test', species='dog', api_breed_id='test_breed'))
            db.session.commit()
            db.session.add(Breed(name='Invalid', attributes='test', species='bird', api_breed_id='bird'))
            with self.assertRaises(IntegrityError):
                db.session.commit()
            db.session.rollback()

    def test_matching_ignores_dog_breed(self):
        user_id = self.login_test_user()
        with app.app_context():
            db.session.add(Breed(name='Dog', attributes='energetic', species='dog', api_breed_id='dog1'))
            db.session.commit()
        response = self.client.post('/questionnaire', json={'answers': {'q1': 'energetic'}})
        self.assertEqual(response.status_code, 200)
        with app.app_context():
            saved = UserQuestionnaire.query.filter_by(user_id=user_id).first()
            self.assertEqual(saved.species, 'cat')
            self.assertEqual(saved.breed.species, 'cat')

    def test_results_reject_species_mismatch(self):
        user_id = self.login_test_user()
        with app.app_context():
            dog = Breed(name='Dog', attributes='test', species='dog', api_breed_id='dog1')
            db.session.add(dog)
            db.session.flush()
            db.session.add(UserQuestionnaire(user_id=user_id, species='cat', answers={'q1': 'test'}, completed=True, matched_breed_id=dog.id))
            db.session.commit()
        response = self.client.get('/results', follow_redirects=True)
        self.assertIn(b'wrong species', response.data)

    def test_missing_cat_breeds_and_match(self):
        user_id = self.login_test_user()
        with app.app_context():
            Breed.query.delete()
            db.session.commit()
        response = self.client.post('/questionnaire', json={'answers': {'q1': 'test'}})
        self.assertEqual(response.status_code, 503)
        self.assertIn(b'No cat breeds', response.data)
        with app.app_context():
            db.session.add(UserQuestionnaire(user_id=user_id, species='cat', answers={'q1': 'test'}, completed=True))
            db.session.commit()
        response = self.client.get('/results', follow_redirects=True)
        self.assertIn(b'No matched breed', response.data)

    def test_questionnaire_api_identifies_cat(self):
        self.login_test_user()
        response = self.client.get('/api/questionnaire')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['species'], 'cat')
        self.assertEqual(len(response.json['questions']), 10)

    def test_import_upserts_by_species_and_api_id(self):
        from fetch_breeds import fetch_cat_breeds
        with app.app_context():
            original = Breed.query.filter_by(species='cat', api_breed_id='test_breed').one()
            original_id = original.id
            db.session.add(Breed(name='Existing Dog', attributes='Loyal', species='dog', api_breed_id='dog1'))
            db.session.commit()
            api_records = [
                {'id': 'test_breed', 'name': 'Renamed Cat', 'description': 'Friendly',
                 'image': {'url': 'https://example.com/new-cat.jpg'}},
                {'id': 'dog1', 'name': 'Cat With Shared ID', 'description': 'Calm'},
                {'id': 'bad', 'description': 'Missing name'},
            ]
            with patch.dict(os.environ, {'CAT_API_KEY': 'test-key'}), patch('fetch_breeds.requests.get') as get:
                get.return_value.json.return_value = api_records
                fetch_cat_breeds()
                fetch_cat_breeds()
            self.assertEqual(Breed.query.filter_by(species='cat').count(), 2)
            updated = Breed.query.filter_by(species='cat', api_breed_id='test_breed').one()
            self.assertEqual(updated.id, original_id)
            self.assertEqual(updated.name, 'Renamed Cat')
            self.assertEqual(updated.image_url, 'https://example.com/new-cat.jpg')
            self.assertEqual(Breed.query.filter_by(species='dog', api_breed_id='dog1').one().name, 'Existing Dog')
    
    def test_home_page(self):
        """Test if home page is accessible"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Purrfect Paws', response.data)
    
    def test_user_registration(self):
        """Test user registration functionality"""
        response = self.client.post('/register', data={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'testpass123',
            'confirm_password': 'testpass123'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        
        # Verify user was created in database
        with app.app_context():
            user = User.query.filter_by(username='testuser').first()
            self.assertIsNotNone(user)
            self.assertEqual(user.email, 'test@example.com')
    
    def test_user_login(self):
        """Test user login functionality"""
        # Create test user
        with app.app_context():
            test_user = User(
                username='testuser',
                email='test@example.com',
                password_hash=generate_password_hash('testpass123')
            )
            db.session.add(test_user)
            db.session.commit()
        
        # Test login
        response = self.client.post('/login', data={
            'email': 'test@example.com',
            'password': 'testpass123'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
    
    def test_questionnaire_access(self):
        """Test if questionnaire page is accessible when logged in"""
        # Create and login test user
        with app.app_context():
            test_user = User(
                username='testuser',
                email='test@example.com',
                password_hash=generate_password_hash('testpass123')
            )
            db.session.add(test_user)
            db.session.commit()
        
        self.client.post('/login', data={
            'email': 'test@example.com',
            'password': 'testpass123'
        }, follow_redirects=True)
        
        # Test questionnaire access
        response = self.client.get('/questionnaire')
        self.assertEqual(response.status_code, 200)
    
    def test_questionnaire_submission(self):
        """Test questionnaire submission and breed matching"""
        # Create and login test user
        with app.app_context():
            test_user = User(
                username='testuser',
                email='test@example.com',
                password_hash=generate_password_hash('testpass123')
            )
            db.session.add(test_user)
            db.session.commit()
        
        self.client.post('/login', data={
            'email': 'test@example.com',
            'password': 'testpass123'
        }, follow_redirects=True)
        
        # Submit questionnaire
        test_answers = {
            'answers': {
                'question0': 'Highly energetic (Active)',
                'question1': 'House',
                'question2': '1-3 hours',
                'question3': 'Independent cat',
                'question4': 'Weekly brush',
                'question5': 'No, live alone',
                'question6': 'Yes, love chatty cats',
                'question7': 'Some experience',
                'question8': 'Often travel',
                'question9': 'No preference'
            }
        }
        
        response = self.client.post('/questionnaire', json=test_answers, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json['success'])
        
        # Verify questionnaire was saved
        with app.app_context():
            questionnaire = UserQuestionnaire.query.filter_by(user_id=1).first()
            self.assertIsNotNone(questionnaire)
            self.assertTrue(questionnaire.completed)
            self.assertEqual(questionnaire.species, 'cat')
            self.assertIsNotNone(questionnaire.matched_breed_id)
    
    def test_results_page(self):
        """Test results page accessibility and content"""
        # Create and login test user
        with app.app_context():
            test_user = User(
                username='testuser',
                email='test@example.com',
                password_hash=generate_password_hash('testpass123')
            )
            db.session.add(test_user)
            
            # Create test questionnaire
            test_questionnaire = UserQuestionnaire(
                user_id=1,
                species='cat', answers={'question0': 'Highly energetic (Active)'},
                completed=True,
                matched_breed_id=1
            )
            db.session.add(test_questionnaire)
            db.session.commit()
        
        self.client.post('/login', data={
            'email': 'test@example.com',
            'password': 'testpass123'
        }, follow_redirects=True)
        
        # Test results page access
        response = self.client.get('/results')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Your Perfect Cat Breed Match', response.data)
    
    def test_initialization_preserves_existing_data(self):
        """Starting again must retain saved accounts, matches, and breed IDs."""
        with app.app_context():
            breed = Breed.query.first()
            user = User(username='saved', email='saved@example.com')
            user.set_password('testpass123')
            db.session.add(user)
            db.session.flush()
            questionnaire = UserQuestionnaire(
                user_id=user.id, species='cat', answers={'q1': 'Apartment'}, completed=True,
                matched_breed_id=breed.id)
            result = QuizResult(user_id=user.id, breed_id=breed.id)
            db.session.add_all([questionnaire, result])
            db.session.commit()
            ids = (breed.id, user.id, questionnaire.id, result.id)

            with patch('app.fetch_cat_breeds') as fetch:
                init_db()
                fetch.assert_not_called()
            self.assertIsNotNone(Breed.query.get(ids[0]))
            self.assertIsNotNone(User.query.get(ids[1]))
            self.assertIsNotNone(UserQuestionnaire.query.get(ids[2]))
            self.assertIsNotNone(QuizResult.query.get(ids[3]))

    def test_logout(self):
        """Test user logout functionality"""
        # Create and login test user
        with app.app_context():
            test_user = User(
                username='testuser',
                email='test@example.com',
                password_hash=generate_password_hash('testpass123')
            )
            db.session.add(test_user)
            db.session.commit()
        
        self.client.post('/login', data={
            'email': 'test@example.com',
            'password': 'testpass123'
        }, follow_redirects=True)
        
        # Test logout
        response = self.client.get('/logout', follow_redirects=True)
        self.assertEqual(response.status_code, 200)

if __name__ == '__main__':
    unittest.main()
