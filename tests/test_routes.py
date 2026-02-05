"""
Tests for Flask routes.
"""

import pytest
import os
import tempfile
from io import BytesIO
from flask import json
from app import create_app
from app.models import Database


@pytest.fixture
def app():
    """Create application for testing."""
    # Use a temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    app = create_app({
        'TESTING': True,
        'DATABASE_PATH': db_path
    })
    
    # Initialize database with test data
    database = Database(db_path)
    statement_id = database.add_statement(
        filename="test.pdf",
        total_income=3000,
        total_expenses=1500
    )
    transactions = [
        {'date': '1.03', 'description': 'Auchan Groceries', 'amount': -78.10, 'category': 'Groceries'},
        {'date': '1.07', 'description': 'Netflix', 'amount': -15.99, 'category': 'Subscriptions'},
        {'date': '1.10', 'description': 'Uber', 'amount': -12.50, 'category': 'Transport'},
        {'date': '1.15', 'description': 'Salary', 'amount': 2000.00, 'category': 'Income'},
    ]
    database.add_transactions_bulk(statement_id, transactions)
    
    yield app
    
    # Cleanup
    os.unlink(db_path)


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


class TestPages:
    """Tests for page routes."""

    def test_index_page(self, client):
        """Test index page loads."""
        response = client.get('/')
        assert response.status_code == 200

    def test_upload_page(self, client):
        """Test upload page loads."""
        response = client.get('/upload')
        assert response.status_code == 200

    def test_expenses_page(self, client):
        """Test expenses page loads."""
        response = client.get('/expenses')
        assert response.status_code == 200


class TestAPIExpenses:
    """Tests for expenses API."""

    def test_get_expenses_basic(self, client):
        """Test basic expenses retrieval."""
        response = client.get('/api/expenses')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'transactions' in data
        assert 'pagination' in data
        assert len(data['transactions']) >= 1

    def test_get_expenses_with_category_filter(self, client):
        """Test filtering by category."""
        response = client.get('/api/expenses?category=Groceries')
        assert response.status_code == 200
        data = json.loads(response.data)
        for t in data['transactions']:
            assert t['category'] == 'Groceries'

    def test_get_expenses_with_search(self, client):
        """Test filtering by search term."""
        response = client.get('/api/expenses?search=Auchan')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['transactions']) >= 1

    def test_get_expenses_pagination(self, client):
        """Test pagination parameters."""
        response = client.get('/api/expenses?page=1&per_page=2')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['transactions']) <= 2
        assert data['pagination']['page'] == 1
        assert data['pagination']['per_page'] == 2


class TestAPISummary:
    """Tests for summary API."""

    def test_get_summary(self, client):
        """Test summary retrieval."""
        response = client.get('/api/summary')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'income' in data
        assert 'expenses' in data
        assert 'net' in data
        assert 'savings_rate' in data


class TestAPIStatements:
    """Tests for statements API."""

    def test_get_statements(self, client):
        """Test statements retrieval."""
        response = client.get('/api/statements')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'statements' in data
        assert len(data['statements']) >= 1


class TestAPICategories:
    """Tests for categories API."""

    def test_get_categories(self, client):
        """Test categories retrieval."""
        response = client.get('/api/categories')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'categories' in data
        assert 'Groceries' in data['categories']


class TestAPIUpload:
    """Tests for upload API."""

    def test_upload_no_file(self, client):
        """Test upload with no file."""
        response = client.post('/api/upload')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_upload_invalid_type(self, client):
        """Test upload with invalid file type."""
        data = {
            'file': (BytesIO(b'test content'), 'test.txt')
        }
        response = client.post(
            '/api/upload',
            data=data,
            content_type='multipart/form-data'
        )
        assert response.status_code == 400

    def test_upload_missing_filename(self, client):
        """Test upload with empty filename."""
        data = {
            'file': (BytesIO(b'test content'), '')
        }
        response = client.post(
            '/api/upload',
            data=data,
            content_type='multipart/form-data'
        )
        assert response.status_code == 400
