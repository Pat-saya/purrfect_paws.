from flask_sqlalchemy import SQLAlchemy
import os
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

def connect_db(app):
    """Connect database to Flask app"""
    db.init_app(app)

def init_db():
    """Initialize database and create all tables."""
    db.create_all()

class User(UserMixin, db.Model):
    """User model for authentication and user management."""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    questionnaires = db.relationship('UserQuestionnaire', backref='user', lazy=True)

    def set_password(self, password):
        """Hash and set the user's password."""
        if not password:
            raise ValueError("Password cannot be empty")
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        """Check if the provided password matches the hash."""
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

class Question(db.Model):
    """Model for storing quiz questions."""
    __tablename__ = 'questions'
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(500), nullable=False)
    choices = db.relationship('Choice', backref='question', lazy=True)

class Choice(db.Model):
    """Model for storing answer choices for questions."""
    __tablename__ = 'choices'
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    text = db.Column(db.String(200), nullable=False)
    cat_trait = db.Column(db.String(50), nullable=False)

class CatBreed(db.Model):
    __tablename__ = 'cat_breeds'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    attributes = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(200))

class UserQuestionnaire(db.Model):
    __tablename__ = 'user_questionnaires'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    answers = db.Column(db.JSON, nullable=False)
    completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    matched_breed_id = db.Column(db.Integer, db.ForeignKey('cat_breeds.id'))

class UserResponse(db.Model):
    __tablename__ = 'user_responses'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    choice_id = db.Column(db.Integer, db.ForeignKey('choices.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class QuizResult(db.Model):
    """Stores final breed matches for users""" 
    __tablename__ = 'quiz_results'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete="CASCADE")) #Links to the user who took the quiz
    breed_id = db.Column(db.Integer, db.ForeignKey('cat_breeds.id', ondelete="CASCADE"))#Links to the recommended cat breed

    user = db.relationship("User", backref="quiz_results")
    breed = db.relationship("CatBreed")


