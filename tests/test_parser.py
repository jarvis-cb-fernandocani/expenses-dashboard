"""
Tests for the PDF parser module.
"""

import pytest
from app.parser import categorize_transaction, calculate_summary


class TestCategorizeTransaction:
    """Tests for transaction categorization."""

    def test_groceries_auchan(self):
        """Test Auchan categorization."""
        assert categorize_transaction('AUCHAN AMADORA CONTACTLESS') == 'Groceries'
        assert categorize_transaction('AUCHAN SEDE PACO DE ARC') == 'Groceries'
        assert categorize_transaction('Continente Bom Dia Lisboa') == 'Groceries'

    def test_groceries_continente(self):
        """Test Continente categorization."""
        assert categorize_transaction('CONTINENTE BOM DIA LISB CONTACTLESS') == 'Groceries'

    def test_transport_uber(self):
        """Test Uber categorization."""
        assert categorize_transaction('UBR PENDING.UBER.COM AMSTERDAM') == 'Transport'
        assert categorize_transaction('BOLT.EU O 2501031320 Tallinn') == 'Transport'

    def test_transport_bolt(self):
        """Test Bolt categorization."""
        assert categorize_transaction('BOLT.EU O 2501031320 Tallinn') == 'Transport'

    def test_dining_mcdonalds(self):
        """Test McDonald's categorization."""
        assert categorize_transaction('MCDONALDS PACO ARCOS CONTACTLESS') == 'Dining'

    def test_dining_restaurant(self):
        """Test restaurant categorization."""
        assert categorize_transaction('DOMINOS BENFICA LISBOA') == 'Dining'
        assert categorize_transaction('OAKBERRY CHIADO LISBOA') == 'Dining'

    def test_entertainment_netflix(self):
        """Test Netflix categorization."""
        assert categorize_transaction('NETFLIX.COM') == 'Entertainment'

    def test_entertainment_epic_games(self):
        """Test Epic Games categorization."""
        assert categorize_transaction('PAYPAL EPIC GAMES') == 'Entertainment'

    def test_shopping_amazon(self):
        """Test Amazon categorization."""
        assert categorize_transaction('WWW.AMAZON. K90C55N55') == 'Shopping'

    def test_subscriptions_apple(self):
        """Test Apple subscription categorization."""
        assert categorize_transaction('APPLE.COM BILL ITUNES.COM') == 'Subscriptions'

    def test_subscriptions_paypal(self):
        """Test PayPal categorization."""
        assert categorize_transaction('PAYPAL PMNTSBVEATS 4029357733') == 'Subscriptions'

    def test_utilities_meo(self):
        """Test MEO categorization."""
        assert categorize_transaction('DD PT19101245 MEO, SA') == 'Utilities'

    def test_health_farmacia(self):
        """Test pharmacy categorization."""
        assert categorize_transaction('Farmacia Simoes Lisboa') == 'Health'

    def test_income_vencimento(self):
        """Test salary/vencimento categorization."""
        assert categorize_transaction('TRANSFERENCIA - VENCIMENTO') == 'Income'

    def test_fees_man_conta(self):
        """Test account maintenance fee categorization."""
        assert categorize_transaction('COM.MAN.CONTA PACOTE CLIENTE') == 'Fees'

    def test_other_unknown(self):
        """Test unknown transactions fall back to Other."""
        assert categorize_transaction('UNKNOWN MERCHANT XYZ123') == 'Other'

    def test_case_insensitive(self):
        """Test categorization is case insensitive."""
        assert categorize_transaction('AUCHAN') == 'Groceries'
        assert categorize_transaction('auchan') == 'Groceries'
        assert categorize_transaction('Uber') == 'Transport'


class TestCalculateSummary:
    """Tests for summary calculations."""

    def test_empty_transactions(self):
        """Test summary with empty list."""
        result = calculate_summary([])
        assert result['income'] == 0
        assert result['expenses'] == 0
        assert result['net'] == 0
        assert result['count'] == 0

    def test_only_income(self):
        """Test summary with only income."""
        transactions = [
            {'date': '1.01', 'description': 'Salary', 'amount': 2000, 'category': 'Income'}
        ]
        result = calculate_summary(transactions)
        assert result['income'] == 2000
        assert result['expenses'] == 0
        assert result['net'] == 2000
        assert result['count'] == 1

    def test_only_expenses(self):
        """Test summary with only expenses."""
        transactions = [
            {'date': '1.01', 'description': 'Groceries', 'amount': -50, 'category': 'Groceries'}
        ]
        result = calculate_summary(transactions)
        assert result['income'] == 0
        assert result['expenses'] == 50
        assert result['net'] == -50

    def test_mixed_transactions(self):
        """Test summary with mixed income and expenses."""
        transactions = [
            {'date': '1.01', 'description': 'Salary', 'amount': 3000, 'category': 'Income'},
            {'date': '1.02', 'description': 'Groceries', 'amount': -100, 'category': 'Groceries'},
            {'date': '1.03', 'description': 'Rent', 'amount': -800, 'category': 'Rent'},
            {'date': '1.04', 'description': 'Utilities', 'amount': -150, 'category': 'Utilities'},
        ]
        result = calculate_summary(transactions)
        assert result['income'] == 3000
        assert result['expenses'] == 1050
        assert result['net'] == 1950
        assert result['count'] == 4

    def test_multiple_transactions(self):
        """Test with many transactions."""
        transactions = [
            {'date': f'1.{i:02d}', 'description': f'Transaction {i}', 
             'amount': (-1)**i * (i * 10), 'category': 'Other'}
            for i in range(1, 31)
        ]
        result = calculate_summary(transactions)
        assert result['count'] == 30
        assert result['income'] > 0
        assert result['expenses'] > 0


class TestParseEdgeCases:
    """Tests for edge cases in parsing."""

    def test_special_characters_in_description(self):
        """Test handling of special characters."""
        result = categorize_transaction("Café & Restaurant - Lisboa")
        assert result == 'Dining'

    def test_accented_characters(self):
        """Test handling of accented characters."""
        assert categorize_transaction("葡萄牙餐廳") == 'Other'
        assert categorize_transaction("Restaurante Português") == 'Dining'

    def test_numeric_description(self):
        """Test handling of numeric-only descriptions."""
        result = categorize_transaction("354527798 -505 AMADORA")
        assert result == 'Other'
