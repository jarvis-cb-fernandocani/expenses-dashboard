"""
PDF parser for Millennium BCP statements.
Extracts transactions from PDF and returns structured data.
"""

import re
from typing import List, Dict, Any
from collections import defaultdict


def parse_millennium_statement(filepath: str) -> List[Dict[str, Any]]:
    """
    Parse a Millennium BCP statement PDF and extract transactions.
    
    Args:
        filepath: Path to the PDF file
        
    Returns:
        List of transaction dictionaries with keys:
        - date: Transaction date (D)
        -format: M.D description: Transaction description
        - amount: Positive for income, negative for expenses
        - category: Transaction category
    """
    import pdftotext
    
    with open(filepath, 'rb') as f:
        pdf = pdftotext.PDF(f)
    
    all_transactions = []
    
    for page_num, page in enumerate(pdf, start=1):
        transactions = parse_page(page, page_num)
        all_transactions.extend(transactions)
    
    return all_transactions


def parse_page(page_text: str, page_num: int) -> List[Dict[str, Any]]:
    """Parse a single page of the statement."""
    transactions = []
    lines = page_text.split('\n')
    
    for line in lines:
        # Skip short lines (not transaction lines)
        if len(line) < 150:
            continue
        
        # Skip APPARTE account transactions
        if "CONTA APPARTE" in line or "APPARTE" in line:
            continue
        
        # Find first date (LANC. position)
        first_date_match = re.search(r'(\d{1,2})\.(\d{1,2})', line)
        if not first_date_match:
            continue
        
        first_date_pos = first_date_match.start()
        month = int(first_date_match.group(1))
        day = int(first_date_match.group(2))
        date_str = f"{month}.{day:02d}"
        
        # Find second date (VALOR position)
        remaining_after_first = line[first_date_pos + 5:]
        second_date_match = re.search(r'(\d{1,2})\.(\d{1,2})', remaining_after_first)
        if not second_date_match:
            continue
        
        second_date_pos = first_date_pos + 5 + second_date_match.start()
        
        # Find amount position (after second date)
        remaining_after_second = line[second_date_pos + 5:]
        amount_match = re.search(r'(\d{1,3}(?:\s?\d{3})*\.\d{2})', remaining_after_second)
        if not amount_match:
            continue
        
        try:
            amount = float(amount_match.group(1).replace(' ', ''))
        except ValueError:
            continue
        
        # Skip invalid amounts
        if amount < 1 or amount > 50000:
            continue
        
        # Extract description
        description = line[second_date_pos + 5:second_date_pos + 5 + amount_match.start()].strip()
        description = re.sub(r'\s+', ' ', description).strip()
        description = re.sub(r'^COMPRA 1880\s+', '', description)
        
        if not description:
            continue
        
        # Determine transaction type and adjust amount
        is_transfer = "TRF DE" in description or "TRF P/" in description or "TRF. P/O" in description
        is_vencimento = "VENCIMENTO" in description
        
        if is_vencimento:
            amount = abs(amount)  # Income
        elif is_transfer:
            continue  # Skip transfers
        else:
            amount = -abs(amount)  # Expense
        
        # Categorize
        category = categorize_transaction(description)
        
        transactions.append({
            'date': date_str,
            'description': description,
            'amount': amount,
            'category': category
        })
    
    return transactions


def categorize_transaction(description: str) -> str:
    """Categorize a transaction based on its description."""
    desc_lower = description.lower()
    
    categories = {
        'Groceries': [
            'auchan', 'continente', 'pingo doce', 'mercadona', 'lidl', 'aldi',
            'minipreço', 'jumbo', 'el corte ingles', 'frutipicas', 'poder da fruta',
            'lopes e aguiar', 'esmoriz', 'minim'
        ],
        'Rent': [
            'paulo veiga', 'renda', 'hipoteca', 'habitação', 'imobiliária',
            'arrendamento'
        ],
        'Utilities': [
            'vodafone', 'nos', 'meo energia', 'altice', 'edp', 'galp energia', 'meo, sa'
        ],
        'Transport': [
            'uber', 'bolt', 'taxi', 'combustível', 'bp', 'galp', 'repsol',
            'viaverde', 'brisa', 'cp comboios', 'metro', 'mbway', 'uber bv',
            'ubr', 'uber.com'
        ],
        'Dining': [
            'restaurante', 'café', 'coffee', 'bar', 'pizza', 'hamburguer',
            'mcdonalds', 'burger', 'dominos', 'subway', 'oakberry', 'trilho destak',
            'norte burguer', 'amanhecer benfica', 'alfornelos', 'eurest',
            'mundi dep', 'dominos benfica'
        ],
        'Entertainment': [
            'netflix', 'spotify', 'disney', 'hbo', 'cinema', 'nos cinemas',
            'epic games', 'playstation', 'xbox', 'nintendo', 'disneyplus',
            'playstation store'
        ],
        'Subscriptions': [
            'microsoft', 'adobe', 'paypal', 'apple.com bill',
            'help.max.com', 'spotify', 'netflix', 'disneyplus', 'apple.com'
        ],
        'Shopping': [
            'amazon', 'shein', 'zalando', 'worten', 'fnac', 'media markt',
            'aliexpress', 'bcm bricolage', 'kiabi', 'brumalecrim',
            'bricolage', 'amazon.'
        ],
        'Health': [
            'farmacia', 'farmac', 'medicare', 'asisa vida', 'fidelidade',
            'sport lisboa', 'clinica', 'médico', 'time to fitness',
            'sport lisboa e benfica', 'sportmultimedia'
        ],
        'Insurance': [
            'credibom', 'seguro', 'insurance', 'multiseguros'
        ],
        'Fees': [
            'com.man.conta', 'custo de servico', 'imposto selo', 'imposto do selo',
            'comissão', 'man.conta', 'custo de servico internacional'
        ],
        'Income': [
            'vencimento', 'salário', 'salary', 'deposit', 'transferencia'
        ]
    }
    
    for category, keywords in categories.items():
        for keyword in keywords:
            # Use word boundary matching
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, desc_lower):
                return category
    
    return 'Other'


def calculate_summary(transactions: List[Dict[str, Any]]) -> Dict[str, float]:
    """Calculate summary totals from transactions."""
    income = sum(t['amount'] for t in transactions if t['amount'] > 0)
    expenses = sum(abs(t['amount']) for t in transactions if t['amount'] < 0)
    
    return {
        'income': income,
        'expenses': expenses,
        'net': income - expenses,
        'count': len(transactions)
    }
