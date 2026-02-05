# 💰 Expenses Dashboard

A web-based expenses dashboard for parsing and tracking Millennium BCP bank statements.

## Features

- 📄 **PDF Upload**: Drag & drop Millennium BCP PDF statements
- 💾 **Database Storage**: SQLite database for persistent storage
- 🔍 **Smart Parsing**: Automatic transaction extraction from PDFs
- 📊 **Financial Summaries**: Monthly and yearly income/expense tracking
- 🏷️ **Categorization**: Automatic transaction categorization
- 🔎 **Filtering**: Filter expenses by date, category, amount, and search
- 📥 **CSV Export**: Export filtered transactions to CSV
- 🎨 **Clean UI**: Simple, responsive web interface

## Tech Stack

- **Backend**: Python Flask
- **Database**: SQLite
- **PDF Processing**: pdftotext
- **Frontend**: HTML/CSS/JavaScript (vanilla)

## Project Structure

```
expenses-dashboard/
├── app/
│   ├── __init__.py       # Flask app factory
│   ├── models.py         # Database models
│   ├── parser.py         # PDF parsing logic
│   ├── routes.py         # Flask routes
│   └── utils.py          # Utility functions
├── static/
│   ├── css/
│   │   └── style.css     # Styles
│   └── js/
│       └── app.js        # Frontend utilities
├── templates/
│   ├── base.html         # Base template
│   ├── index.html        # Dashboard
│   ├── upload.html       # Upload page
│   └── expenses.html    # Expenses list
├── tests/
│   ├── __init__.py
│   ├── test_models.py    # Model tests
│   ├── test_parser.py    # Parser tests
│   └── test_routes.py    # Route tests
├── uploads/              # PDF storage
├── .env                  # Environment config
├── .gitignore
├── requirements.txt      # Dependencies
├── app.py               # Entry point
└── README.md
```

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/expenses-dashboard.git
cd expenses-dashboard

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install pdftotext (required)
# Ubuntu/Debian:
sudo apt-get install poppler-utils

# macOS:
brew install poppler

# Run the application
python app.py
```

## Usage

1. Open http://localhost:5000
2. Click "Upload" to upload a Millennium BCP PDF statement
3. View the dashboard for summaries
4. Browse and filter transactions on the "Expenses" page

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/expenses` | Get transactions with filters |
| GET | `/api/summary` | Get financial summary |
| GET | `/api/statements` | Get uploaded statements |
| GET | `/api/categories` | Get all categories |
| POST | `/api/upload` | Upload PDF statement |
| DELETE | `/api/statements/<id>` | Delete statement |

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html
```

## License

MIT
