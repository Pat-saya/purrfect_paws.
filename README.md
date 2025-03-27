# 🐱 Purrfect Paws - Cat Breed Matcher

[![Python](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/flask-3.0.0-green.svg)](https://flask.palletsprojects.com/)
[![PostgreSQL](https://img.shields.io/badge/postgresql-14-blue.svg)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)

A Flask web application that helps users find their perfect cat breed match through an interactive questionnaire. 🎯

## ✨ Features

- 🔐 User registration and authentication
- 📝 Interactive cat breed matching questionnaire
- 🐈 Detailed cat breed information and images
- 🎯 Personalized breed recommendations
- 📱 Responsive web interface

## 🛠️ Tech Stack

- Python 3.x
- Flask
- PostgreSQL
- SQLAlchemy
- Flask-Login
- Flask-WTF
- Bootstrap 5

## 📋 Prerequisites

- Python 3.x
- PostgreSQL
- pip (Python package manager)

## 🚀 Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/purrfect_paws.git
cd purrfect_paws
```

2. Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Set up environment variables:
   Create a `.env` file in the project root with the following variables:

```
DATABASE_URL=postgresql:///purrfect_paws
SECRET_KEY=your-secret-key
CAT_API_KEY=your-cat-api-key  # Get your API key from https://thecatapi.com/
```

5. Initialize the database:

```bash
python -c "from app import init_db; init_db()"
```

## 🏃‍♂️ Running the Application

1. Start the Flask development server:

```bash
flask run
```

2. Open your browser and navigate to:

```
http://localhost:5000
```

## 🧪 Testing

The application includes unit tests to verify core functionality:

```bash
python -m unittest test_app.py -v
```

## 📁 Project Structure

```
purrfect_paws/
├── app.py              # Main application file
├── models.py           # Database models
├── forms_module.py     # Form definitions
├── test_app.py         # Unit tests
├── requirements.txt    # Project dependencies
├── .env               # Environment variables
└── templates/         # HTML templates
    ├── base.html
    ├── home.html
    ├── login.html
    ├── register.html
    ├── questionnaire.html
    └── results.html
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [The Cat API](https://thecatapi.com/) for providing cat breed data
- [Flask](https://flask.palletsprojects.com/) for the web framework
- [Bootstrap](https://getbootstrap.com/) for the UI components
# purrfect_paws.
# purrfect_paws.
