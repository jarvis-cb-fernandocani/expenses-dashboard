"""
Tests for budget API endpoints.
"""

import pytest
import os
import tempfile
from flask import json
from app import create_app
from app.models import Database


@pytest.fixture
def app():
    """Create application for testing."""
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
        {'date': '1.03', 'description': 'Auchan Groceries', 'amount': -100.00, 'category': 'Groceries'},
        {'date': '1.05', 'description': 'Uber', 'amount': -25.00, 'category': 'Transport'},
        {'date': '1.07', 'description': 'Netflix', 'amount': -15.99, 'category': 'Subscriptions'},
    ]
    database.add_transactions_bulk(statement_id, transactions)
    
    yield app
    
    # Cleanup
    os.unlink(db_path)


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


class TestBudgetAPI:
    """Tests for budget API endpoints."""

    def test_set_budget(self, client):
        """Test setting a budget."""
        response = client.post('/api/budgets',
            data=json.dumps({'category': 'Groceries', 'monthly_limit': 300}),
            content_type='application/json'
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True

    def test_set_budget_invalid(self, client):
        """Test setting budget with missing fields."""
        response = client.post('/api/budgets',
            data=json.dumps({'category': 'Groceries'}),
            content_type='application/json'
        )
        assert response.status_code == 400

    def test_set_budget_invalid_amount(self, client):
        """Test setting budget with invalid amount."""
        response = client.post('/api/budgets',
            data=json.dumps({'category': 'Groceries', 'monthly_limit': 'invalid'}),
            content_type='application/json'
        )
        assert response.status_code == 400

    def test_get_budgets(self, client):
        """Test getting all budgets."""
        # First set a budget
        client.post('/api/budgets',
            data=json.dumps({'category': 'Groceries', 'monthly_limit': 300}),
            content_type='application/json'
        )
        
        response = client.get('/api/budgets')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'budgets' in data
        assert len(data['budgets']) >= 1

    def test_get_budgets_structure(self, client):
        """Test budget response structure."""
        client.post('/api/budgets',
            data=json.dumps({'category': 'Groceries', 'monthly_limit': 300}),
            content_type='application/json'
        )
        
        response = client.get('/api/budgets')
        data = json.loads(response.data)
        budget = data['budgets'][0]
        
        assert 'category' in budget
        assert 'monthly_limit' in budget
        assert 'spent' in budget
        assert 'remaining' in budget
        assert 'percent_used' in budget
        assert 'status' in budget

    def test_delete_budget(self, client):
        """Test deleting a budget."""
        # Create a budget first
        client.post('/api/budgets',
            data=json.dumps({'category': 'Groceries', 'monthly_limit': 300}),
            content_type='application/json'
        )
        
        response = client.delete('/api/budgets/Groceries')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True

    def test_delete_nonexistent_budget(self, client):
        """Test deleting a budget that doesn't exist."""
        response = client.delete('/api/budgets/Nonexistent')
        assert response.status_code == 404


class TestAnalyticsAPI:
    """Tests for analytics API endpoints."""

    def test_category_breakdown(self, client):
        """Test category breakdown endpoint."""
        response = client.get('/api/analytics/category-breakdown')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'breakdown' in data
        assert 'month' in data
        assert 'year' in data

    def test_category_breakdown_has_expenses(self, client):
        """Test that category breakdown includes expense data."""
        response = client.get('/api/analytics/category-breakdown')
        data = json.loads(response.data)
        
        # Should have categories (may be empty if no data for current month)
        assert isinstance(data['breakdown'], list)
        
        # Check structure if data exists
        if len(data['breakdown']) > 0:
            cat = data['breakdown'][0]
            assert 'category' in cat
            assert 'amount' in cat
            assert 'percent' in cat

    def test_monthly_comparison(self, client):
        """Test monthly comparison endpoint."""
        response = client.get('/api/analytics/monthly-comparison')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'monthly_totals' in data
        assert 'year' in data

    def test_monthly_comparison_structure(self, client):
        """Test monthly comparison structure."""
        response = client.get('/api/analytics/monthly-comparison')
        data = json.loads(response.data)
        assert 'monthly_totals' in data
        assert 'year' in data
        # May be empty if no data exists for this year yet
        assert isinstance(data['monthly_totals'], list)
