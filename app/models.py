"""
Database models for the expenses dashboard.
Uses SQLite for simplicity and portability.
"""

import sqlite3
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager


class Database:
    """SQLite database manager for expenses tracking."""

    def __init__(self, db_path: str = "expenses.db"):
        self.db_path = db_path
        self.init_db()

    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def init_db(self) -> None:
        """Initialize the database schema."""
        with self.get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS statements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    period_start DATE,
                    period_end DATE,
                    total_income REAL DEFAULT 0,
                    total_expenses REAL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    statement_id INTEGER REFERENCES statements(id),
                    date TEXT NOT NULL,
                    description TEXT,
                    amount REAL NOT NULL,
                    category TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_transactions_date 
                    ON transactions(date);
                CREATE INDEX IF NOT EXISTS idx_transactions_category 
                    ON transactions(category);
                CREATE INDEX IF NOT EXISTS idx_transactions_statement 
                    ON transactions(statement_id);
            """)

    def add_statement(
        self,
        filename: str,
        period_start: Optional[str] = None,
        period_end: Optional[str] = None,
        total_income: float = 0,
        total_expenses: float = 0
    ) -> int:
        """Add a new statement record and return its ID."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO statements 
                (filename, period_start, period_end, total_income, total_expenses)
                VALUES (?, ?, ?, ?, ?)
                """,
                (filename, period_start, period_end, total_income, total_expenses)
            )
            conn.commit()
            return cursor.lastrowid

    def add_transaction(
        self,
        statement_id: int,
        date: str,
        description: str,
        amount: float,
        category: str
    ) -> int:
        """Add a single transaction."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO transactions 
                (statement_id, date, description, amount, category)
                VALUES (?, ?, ?, ?, ?)
                """,
                (statement_id, date, description, amount, category)
            )
            conn.commit()
            return cursor.lastrowid

    def add_transactions_bulk(
        self,
        statement_id: int,
        transactions: List[Dict[str, Any]]
    ) -> int:
        """Add multiple transactions efficiently."""
        with self.get_connection() as conn:
            cursor = conn.executemany(
                """
                INSERT INTO transactions 
                (statement_id, date, description, amount, category)
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (
                        statement_id,
                        t['date'],
                        t['description'],
                        t['amount'],
                        t['category']
                    )
                    for t in transactions
                ]
            )
            conn.commit()
            return len(transactions)

    def get_statement(self, statement_id: int) -> Optional[Dict[str, Any]]:
        """Get a statement by ID."""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM statements WHERE id = ?",
                (statement_id,)
            ).fetchone()
            return dict(row) if row else None

    def get_all_statements(self) -> List[Dict[str, Any]]:
        """Get all uploaded statements."""
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM statements ORDER BY uploaded_at DESC"
            ).fetchall()
            return [dict(row) for row in rows]

    def get_transactions(
        self,
        statement_id: Optional[int] = None,
        category: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None,
        search: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get transactions with optional filters."""
        query = "SELECT * FROM transactions WHERE 1=1"
        params = []

        if statement_id:
            query += " AND statement_id = ?"
            params.append(statement_id)
        
        if category:
            query += " AND category = ?"
            params.append(category)
        
        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)
        
        if min_amount is not None:
            query += " AND amount <= ?"
            params.append(min_amount)
        
        if max_amount is not None:
            query += " AND amount >= ?"
            params.append(max_amount)
        
        if search:
            query += " AND description LIKE ?"
            params.append(f"%{search}%")

        query += " ORDER BY date DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self.get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    def get_summary(
        self,
        year: Optional[int] = None,
        month: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get income/expense summary for a period."""
        query = """
            SELECT 
                SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as income,
                SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as expenses
            FROM transactions
            WHERE 1=1
        """
        params = []

        if year:
            query += " AND substr(date, 1, 2) = ?"
            params.append(f"{year % 100:02d}")
        
        if month:
            query += " AND substr(date, 4, 2) = ?"
            params.append(f"{month:02d}")

        with self.get_connection() as conn:
            row = conn.execute(query, params).fetchone()
            income = row['income'] or 0
            expenses = row['expenses'] or 0
            return {
                'income': income,
                'expenses': expenses,
                'net': income - expenses,
                'savings_rate': ((income - expenses) / income * 100) if income > 0 else 0
            }

    def get_summary_by_date_range(self, start_date: str, end_date: str) -> Dict[str, float]:
        """Get summary for a specific date range."""
        # Convert date strings (YYYY-MM-DD) to month.day format
        # e.g., "2025-01-01" -> "1.01"
        start_month = int(start_date.split('-')[1])
        start_day = int(start_date.split('-')[2])
        end_month = int(end_date.split('-')[1])
        end_day = int(end_date.split('-')[2])
        
        with self.get_connection() as conn:
            # For same month
            if start_month == end_month:
                row = conn.execute(
                    """
                    SELECT 
                        SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as income,
                        SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as expenses
                    FROM transactions
                    WHERE substr(date, 1, 2) = ? AND CAST(substr(date, 4, 2) AS INTEGER) BETWEEN ? AND ?
                    """,
                    (f"{start_month:02d}", start_day, end_day)
                ).fetchone()
            else:
                # Cross month - get all transactions in range
                row = conn.execute(
                    """
                    SELECT 
                        SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as income,
                        SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as expenses
                    FROM transactions
                    WHERE (substr(date, 1, 2) = ? AND CAST(substr(date, 4, 2) AS INTEGER) >= ?)
                       OR (substr(date, 1, 2) = ? AND CAST(substr(date, 4, 2) AS INTEGER) <= ?)
                       OR (CAST(substr(date, 1, 2) AS INTEGER) > ? AND CAST(substr(date, 1, 2) AS INTEGER) < ?)
                    """,
                    (f"{start_month:02d}", start_day, f"{end_month:02d}", end_day, start_month, end_month)
                ).fetchone()
            
            income = row['income'] or 0
            expenses = row['expenses'] or 0
            return {
                'income': income,
                'expenses': expenses,
                'net': income - expenses,
                'savings_rate': ((income - expenses) / income * 100) if income > 0 else 0
            }

    def get_transactions_count(
        self,
        statement_id: Optional[int] = None,
        category: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        search: Optional[str] = None
    ) -> int:
        """Get total count of filtered transactions."""
        query = "SELECT COUNT(*) as count FROM transactions WHERE 1=1"
        params = []

        if statement_id:
            query += " AND statement_id = ?"
            params.append(statement_id)
        
        if category:
            query += " AND category = ?"
            params.append(category)
        
        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)
        
        if search:
            query += " AND description LIKE ?"
            params.append(f"%{search}%")

        with self.get_connection() as conn:
            row = conn.execute(query, params).fetchone()
            return row['count']

    def get_categories(self) -> List[str]:
        """Get all unique categories."""
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT DISTINCT category FROM transactions ORDER BY category"
            ).fetchall()
            return [row['category'] for row in rows]

    def delete_statement(self, statement_id: int) -> bool:
        """Delete a statement and its transactions."""
        with self.get_connection() as conn:
            conn.execute(
                "DELETE FROM transactions WHERE statement_id = ?",
                (statement_id,)
            )
            result = conn.execute(
                "DELETE FROM statements WHERE id = ?",
                (statement_id,)
            )
            conn.commit()
            return result.rowcount > 0

    # === Budget Methods ===

    def create_budgets_table(self) -> None:
        """Create the budgets table if it doesn't exist."""
        with self.get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS budgets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL UNIQUE,
                    monthly_limit REAL NOT NULL DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_budgets_category ON budgets(category);
            """)

    def set_budget(self, category: str, monthly_limit: float) -> int:
        """Set or update a budget for a category."""
        self.create_budgets_table()
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO budgets (category, monthly_limit)
                VALUES (?, ?)
                ON CONFLICT(category) DO UPDATE SET
                    monthly_limit = excluded.monthly_limit,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (category, monthly_limit)
            )
            conn.commit()
            return cursor.lastrowid

    def get_budget(self, category: str) -> Optional[Dict[str, Any]]:
        """Get budget for a specific category."""
        self.create_budgets_table()
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM budgets WHERE category = ?",
                (category,)
            ).fetchone()
            return dict(row) if row else None

    def get_all_budgets(self) -> List[Dict[str, Any]]:
        """Get all budgets."""
        self.create_budgets_table()
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM budgets ORDER BY category"
            ).fetchall()
            return [dict(row) for row in rows]

    def delete_budget(self, category: str) -> bool:
        """Delete a budget."""
        self.create_budgets_table()
        with self.get_connection() as conn:
            result = conn.execute(
                "DELETE FROM budgets WHERE category = ?",
                (category,)
            )
            conn.commit()
            return result.rowcount > 0

    def get_spent_by_category_month(self, category: str, month: int, year: int) -> float:
        """Get total spent for a category in a specific month."""
        with self.get_connection() as conn:
            row = conn.execute(
                """
                SELECT SUM(ABS(amount)) as total
                FROM transactions
                WHERE category = ? AND amount < 0
                AND substr(date, 1, 2) = ?
                """,
                (category, f"{month:02d}")
            ).fetchone()
            return row['total'] or 0

    def get_monthly_spending_by_category(self, month: int, year: int) -> Dict[str, float]:
        """Get spending by category for a specific month."""
        with self.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT category, SUM(ABS(amount)) as total
                FROM transactions
                WHERE amount < 0 AND substr(date, 1, 2) = ?
                GROUP BY category
                """,
                (f"{month:02d}",)
            ).fetchall()
            return {row['category']: row['total'] for row in rows}

    def get_monthly_totals(self, year: int) -> List[Dict[str, Any]]:
        """Get income and expenses by month for the year."""
        with self.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT 
                    substr(date, 1, 2) as month,
                    SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as income,
                    SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as expenses
                FROM transactions
                WHERE substr(date, 1, 2) IN ('01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12')
                GROUP BY month
                ORDER BY month
                """,
            ).fetchall()
            return [
                {
                    'month': int(row['month']),
                    'income': row['income'] or 0,
                    'expenses': row['expenses'] or 0
                }
                for row in rows
            ]
