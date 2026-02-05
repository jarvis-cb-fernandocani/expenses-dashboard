"""
Tests for the database models.
"""

import pytest
import tempfile
import os
from app.models import Database


@pytest.fixture
def db():
    """Create a test database with sample data."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    database = Database(db_path)
    
    # Add a test statement
    statement_id = database.add_statement(
        filename="test_statement.pdf",
        period_start="2025-01-01",
        period_end="2025-01-31",
        total_income=3000,
        total_expenses=1500
    )
    
    # Add test transactions
    transactions = [
        {'date': '1.03', 'description': 'Auchan Groceries', 'amount': -78.10, 'category': 'Groceries'},
        {'date': '1.07', 'description': 'Netflix Subscription', 'amount': -15.99, 'category': 'Subscriptions'},
        {'date': '1.10', 'description': 'Uber Ride', 'amount': -12.50, 'category': 'Transport'},
        {'date': '1.15', 'description': 'Salary Deposit', 'amount': 2000.00, 'category': 'Income'},
        {'date': '1.20', 'description': 'Restaurant Dinner', 'amount': -45.00, 'category': 'Dining'},
    ]
    database.add_transactions_bulk(statement_id, transactions)
    
    yield database
    
    # Cleanup
    os.unlink(db_path)


class TestDatabaseInit:
    """Tests for database initialization."""

    def test_tables_created(self, db):
        """Verify all required tables exist."""
        with db.get_connection() as conn:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            table_names = [t['name'] for t in tables]
            
            assert 'statements' in table_names
            assert 'transactions' in table_names

    def test_indexes_created(self, db):
        """Verify indexes exist."""
        with db.get_connection() as conn:
            indexes = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            ).fetchall()
            index_names = [i['name'] for i in indexes]
            
            assert 'idx_transactions_date' in index_names
            assert 'idx_transactions_category' in index_names


class TestStatements:
    """Tests for statement operations."""

    def test_add_statement(self, db):
        """Test adding a statement."""
        new_id = db.add_statement(
            filename="new_statement.pdf",
            period_start="2025-02-01",
            period_end="2025-02-28"
        )
        assert new_id is not None
        assert new_id > 0

    def test_get_statement(self, db):
        """Test retrieving a statement by ID."""
        statement = db.get_statement(1)
        assert statement is not None
        assert statement['filename'] == 'test_statement.pdf'
        assert statement['total_income'] == 3000

    def test_get_all_statements(self, db):
        """Test retrieving all statements."""
        statements = db.get_all_statements()
        assert len(statements) >= 1
        assert statements[0]['filename'] == 'test_statement.pdf'


class TestTransactions:
    """Tests for transaction operations."""

    def test_add_single_transaction(self, db):
        """Test adding a single transaction."""
        new_id = db.add_transaction(
            statement_id=1,
            date='1.25',
            description='Test Transaction',
            amount=-50.00,
            category='Other'
        )
        assert new_id is not None

    def test_add_transactions_bulk(self, db):
        """Test bulk transaction insertion."""
        new_id = db.add_statement(filename="bulk_test.pdf")
        transactions = [
            {'date': '2.01', 'description': 'Test 1', 'amount': -10, 'category': 'Other'},
            {'date': '2.02', 'description': 'Test 2', 'amount': -20, 'category': 'Groceries'},
        ]
        count = db.add_transactions_bulk(new_id, transactions)
        assert count == 2

    def test_get_transactions_basic(self, db):
        """Test basic transaction retrieval."""
        transactions = db.get_transactions()
        assert len(transactions) >= 5

    def test_get_transactions_by_category(self, db):
        """Test filtering transactions by category."""
        transactions = db.get_transactions(category='Groceries')
        assert len(transactions) >= 1
        for t in transactions:
            assert t['category'] == 'Groceries'

    def test_get_transactions_by_search(self, db):
        """Test filtering transactions by search term."""
        transactions = db.get_transactions(search='Auchan')
        assert len(transactions) >= 1
        assert 'Auchan' in transactions[0]['description']

    def test_get_transactions_pagination(self, db):
        """Test transaction pagination."""
        all_transactions = db.get_transactions(limit=100)
        page1 = db.get_transactions(limit=2, offset=0)
        page2 = db.get_transactions(limit=2, offset=2)
        
        assert len(page1) == 2
        assert len(page2) == 2
        assert page1[0]['id'] != page2[0]['id']


class TestSummary:
    """Tests for summary calculations."""

    def test_get_summary(self, db):
        """Test getting financial summary."""
        summary = db.get_summary()
        assert summary['income'] >= 0
        assert summary['expenses'] >= 0
        assert summary['net'] == summary['income'] - summary['expenses']

    def test_savings_rate_calculation(self, db):
        """Test savings rate is calculated correctly."""
        summary = db.get_summary()
        if summary['income'] > 0:
            expected_rate = ((summary['income'] - summary['expenses']) / summary['income']) * 100
            assert abs(summary['savings_rate'] - expected_rate) < 0.01


class TestCategories:
    """Tests for category operations."""

    def test_get_categories(self, db):
        """Test retrieving unique categories."""
        categories = db.get_categories()
        assert 'Groceries' in categories
        assert 'Transport' in categories
        assert 'Dining' in categories


class TestDelete:
    """Tests for deletion operations."""

    def test_delete_statement(self, db):
        """Test deleting a statement and its transactions."""
        # Get count before
        before = db.get_transactions_count()
        
        # Delete
        result = db.delete_statement(1)
        assert result is True
        
        # Verify cascade delete
        after = db.get_transactions_count()
        assert after < before
