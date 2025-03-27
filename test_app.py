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
from app import app, db
from models import User, Question, Choice, CatBreed, UserQuestionnaire, UserResponse
from werkzeug.security import generate_password_hash

class TestPurrfectPaws(unittest.TestCase):
    """Test cases for Purrfect Paws application"""
    
    def setUp(self):
        """Set up test database and create test client"""
        # Configure test database
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql:///purrfect_paws_test'
        app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF protection during testing
        self.client = app.test_client()
        
        # Create test database tables
        with app.app_context():
            db.create_all()
            
            # Create test cat breed
            test_breed = CatBreed(
                name='Test Breed',
                attributes='Adaptability: 3/5\nChild Friendly: 4/5\nDog Friendly: 3/5',
                image_url='test_breed'
            )
            db.session.add(test_breed)
            db.session.commit()
    
    def tearDown(self):
        """Clean up after each test"""
        with app.app_context():
            db.session.remove()
            db.drop_all()
    
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
        
        # Verify questionnaire was saved
        with app.app_context():
            questionnaire = UserQuestionnaire.query.filter_by(user_id=1).first()
            self.assertIsNotNone(questionnaire)
            self.assertTrue(questionnaire.completed)
    
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
                answers={'question0': 'Highly energetic (Active)'},
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

