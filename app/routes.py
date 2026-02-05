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


# === Budget API ===

@bp.route('/api/budgets', methods=['GET'])
def get_budgets():
    """Get all budgets with current spending."""
    database = get_db()
    budgets = database.get_all_budgets()
    
    # Get current month spending
    import datetime
    now = datetime.datetime.now()
    month = now.month
    year = now.year
    
    result = []
    for budget in budgets:
        spent = database.get_spent_by_category_month(
            budget['category'], month, year
        )
        remaining = budget['monthly_limit'] - spent
        percent_used = (spent / budget['monthly_limit'] * 100) if budget['monthly_limit'] > 0 else 0
        
        result.append({
            **budget,
            'spent': spent,
            'remaining': remaining,
            'percent_used': round(percent_used, 1),
            'status': 'over' if spent > budget['monthly_limit'] else 'warning' if percent_used > 80 else 'ok'
        })
    
    return jsonify({'budgets': result})


@bp.route('/api/budgets', methods=['POST'])
def set_budget():
    """Set or update a budget for a category."""
    data = request.get_json()
    
    if not data or 'category' not in data or 'monthly_limit' not in data:
        return jsonify({'error': 'category and monthly_limit required'}), 400
    
    try:
        monthly_limit = float(data['monthly_limit'])
    except (TypeError, ValueError):
        return jsonify({'error': 'monthly_limit must be a number'}), 400
    
    database = get_db()
    budget_id = database.set_budget(data['category'], monthly_limit)
    
    return jsonify({
        'success': True,
        'message': f'Budget set for {data["category"]}',
        'budget_id': budget_id
    })


@bp.route('/api/budgets/<category>', methods=['DELETE'])
def delete_budget(category: str):
    """Delete a budget."""
    database = get_db()
    result = database.delete_budget(category)
    
    if result:
        return jsonify({'success': True, 'message': 'Budget deleted'})
    return jsonify({'error': 'Budget not found'}), 404


# === Analytics API ===

@bp.route('/api/analytics/category-breakdown', methods=['GET'])
def category_breakdown():
    """Get spending breakdown by category for current month."""
    import datetime
    now = datetime.datetime.now()
    month = now.month
    year = now.year
    
    database = get_db()
    spending = database.get_monthly_spending_by_category(month, year)
    
    # Add zero-spending categories from budget
    budgets = database.get_all_budgets()
    budget_categories = {b['category'] for b in budgets}
    all_categories = budget_categories.union(spending.keys())
    
    total = sum(spending.values()) if spending else 1
    
    result = []
    for cat in sorted(all_categories):
        amount = spending.get(cat, 0)
        percent = (amount / total * 100) if total > 0 else 0
        result.append({
            'category': cat,
            'amount': amount,
            'percent': round(percent, 1)
        })
    
    return jsonify({
        'breakdown': result,
        'month': month,
        'year': year
    })


@bp.route('/api/analytics/monthly-comparison', methods=['GET'])
def monthly_comparison():
    """Get income vs expenses by month for current year."""
    import datetime
    year = datetime.datetime.now().year
    
    database = get_db()
    monthly_totals = database.get_monthly_totals(year)
    
    return jsonify({
        'monthly_totals': monthly_totals,
        'year': year
    })
