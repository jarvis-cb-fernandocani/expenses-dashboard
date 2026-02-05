"""
Main application entry point for the expenses dashboard.
"""

import os
from app import create_app
from app.models import Database


# Initialize database
db = Database(os.environ.get('DATABASE_PATH', 'expenses.db'))


app = create_app()


if __name__ == '__main__':
    app.run(
        host=os.environ.get('HOST', '0.0.0.0'),
        port=int(os.environ.get('PORT', 5000)),
        debug=os.environ.get('DEBUG', 'true').lower() == 'true'
    )
