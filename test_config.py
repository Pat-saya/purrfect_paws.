"""
Test Configuration for Purrfect Paws

This file contains configuration settings for running tests.
It ensures that tests use a separate test database and don't affect the production database.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Test database configuration
TEST_DATABASE_URL = 'postgresql:///purrfect_paws_test'

# Test configuration
TEST_CONFIG = {
    'TESTING': True,
    'SQLALCHEMY_DATABASE_URI': TEST_DATABASE_URL,
    'WTF_CSRF_ENABLED': False,
    'SECRET_KEY': 'test-secret-key-xyz123'
} 