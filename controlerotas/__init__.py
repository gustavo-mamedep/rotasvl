import os

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

app.secret_key = 'a1f4b29e3c8d7f015a96b3de4c72f981'
app.config['SECRET_KEY'] = 'e9c7a18f4b23d5068fa1b3ce9274dc50'

app.config['SQLALCHEMY_DATABASE_URI'] = (
    os.getenv('DATABASE_URL')
    or os.getenv('SQLALCHEMY_DATABASE_URI')
    or 'postgresql://rotas_user:MAMEDE3276@localhost:5432/rotas_db'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
}

database = SQLAlchemy(app)

from controlerotas import routes
