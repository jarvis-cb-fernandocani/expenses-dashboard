"""
Flask routes for the expenses dashboard.
"""

import os
import json
from flask import Blueprint, render_template, request, jsonify, current_app, g
from werkzeug.utils import secure_filename
from app.models import Database
from app.parser import parse_millennium_statement


bp = Blueprint('routes', __name__)

# Allowed file extensions
ALLOWED_EXTENSIONS = {'pdf'}


def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_db() -> Database:
    """Get the database instance for the current app context."""
    if not hasattr(g, 'database'):
        db_path = current_app.config.get('DATABASE_PATH', 'expenses.db')
        g.database = Database(db_path)
    return g.database


@bp.route('/')
def index():
    """Dashboard home page."""
    return render_template('index.html')


@bp.route('/upload')
def upload_page():
    """Upload page."""
    return render_template('upload.html')


@bp.route('/expenses')
def expenses_page():
    """Expenses list page."""
    return render_template('expenses.html')


# API Endpoints


@bp.route('/api/upload', methods=['POST'])
def upload_file():
    """Handle PDF file upload and parsing."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            # Parse the PDF
            transactions = parse_millennium_statement(filepath)
            
            if not transactions:
                return jsonify({
                    'error': 'No transactions found in PDF',
                    'filename': filename
                }), 400
            
            # Calculate totals
            income = sum(t['amount'] for t in transactions if t['amount'] > 0)
            expenses = sum(abs(t['amount']) for t in transactions if t['amount'] < 0)
            
            # Store in database
            database = get_db()
            statement_id = database.add_statement(
                filename=filename,
                total_income=income,
                total_expenses=expenses
            )
            database.add_transactions_bulk(statement_id, transactions)
            
            return jsonify({
                'success': True,
                'message': f'Successfully processed {len(transactions)} transactions',
                'statement_id': statement_id,
                'filename': filename,
                'transactions_count': len(transactions),
                'income': income,
                'expenses': expenses
            })
            
        except Exception as e:
            # Clean up file on error
            if os.path.exists(filepath):
                os.remove(filepath)
            return jsonify({'error': str(e)}), 500
    
    return jsonify({'error': 'Invalid file type. Only PDF files are allowed.'}), 400


@bp.route('/api/expenses', methods=['GET'])
def get_expenses():
    """Get expenses with optional filters."""
    database = get_db()
    
    # Parse query parameters
    statement_id = request.args.get('statement_id', type=int)
    category = request.args.get('category')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    min_amount = request.args.get('min_amount', type=float)
    max_amount = request.args.get('max_amount', type=float)
    search = request.args.get('search')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    offset = (page - 1) * per_page
    
    # Get transactions
    transactions = database.get_transactions(
        statement_id=statement_id,
        category=category,
        start_date=start_date,
        end_date=end_date,
        min_amount=min_amount,
        max_amount=max_amount,
        search=search,
        limit=per_page,
        offset=offset
    )
    
    # Get total count for pagination
    total = database.get_transactions_count(
        statement_id=statement_id,
        category=category,
        start_date=start_date,
        end_date=end_date,
        search=search
    )
    
    return jsonify({
        'transactions': transactions,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total,
            'pages': (total + per_page - 1) // per_page
        }
    })


@bp.route('/api/summary', methods=['GET'])
def get_summary():
    """Get financial summary."""
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)
    
    database = get_db()
    summary = database.get_summary(year=year, month=month)
    
    return jsonify(summary)


@bp.route('/api/statements', methods=['GET'])
def get_statements():
    """Get all uploaded statements."""
    database = get_db()
    statements = database.get_all_statements()
    return jsonify({'statements': statements})


@bp.route('/api/categories', methods=['GET'])
def get_categories():
    """Get all unique categories."""
    database = get_db()
    categories = database.get_categories()
    return jsonify({'categories': categories})


@bp.route('/api/statements/<int:statement_id>', methods=['DELETE'])
def delete_statement(statement_id: int):
    """Delete a statement and its transactions."""
    database = get_db()
    result = database.delete_statement(statement_id)
    
    if result:
        return jsonify({'success': True, 'message': 'Statement deleted'})
    return jsonify({'error': 'Statement not found'}), 404
