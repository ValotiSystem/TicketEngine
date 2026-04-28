"""
summary:
    Entry point for the Flask CLI and gunicorn.
"""
from app import create_app

app = create_app()
