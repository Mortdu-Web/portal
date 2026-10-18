"""Point d'entrée de production : gunicorn wsgi:app"""
from hub_web import create_app

app = create_app()
