"""
CA Manage — WSGI Entry Point
Named wsgi.py (not app.py) to avoid shadowing the app/ package on Vercel.
Run with: flask run --debug
"""
import os
from dotenv import load_dotenv

# Load environment variables before anything else
load_dotenv()

from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000)),
        debug=os.getenv('FLASK_ENV') == 'development'
    )
