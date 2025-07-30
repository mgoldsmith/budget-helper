# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Environment Setup
- Python virtual environment is at `./venv/`
- Activate: `source venv/bin/activate`
- Install dependencies: `pip install matplotlib numpy` (main dependencies are matplotlib for visualization and numpy for calculations)

### Running the Application
- Run analysis: `python expense_analyzer.py`
- The script will automatically read all CSV files from the `statements/` folder
- Supports account multipliers: prefix CSV filenames with multiplier (e.g., `0.5x_joint.csv` for 50/50 shared account)
- Generates `expense_breakdown.png` chart and prints categorized expense summary

### Dependencies
- matplotlib: For creating pie charts and visualizations
- numpy: For numerical calculations (via matplotlib dependency)
- Built-in Python modules: csv, os, re, collections, decimal

## Architecture

This is a single-file Python application (`expense_analyzer.py`) that analyzes German bank statement CSV files.

### Core Components

**ExpenseAnalyzer Class**: Main analyzer with these key methods:
- `read_csv_files()`: Reads CSV files from statements folder with multiple encoding support (utf-8, iso-8859-1, cp1252, latin1) and parses filename multipliers
- `categorize_transactions()`: Classifies transactions using keyword matching
- `create_expense_chart()`: Generates pie chart visualization using matplotlib
- `print_summary()`: Console output of categorized expenses

### Data Flow
1. CSV files read from `statements/` folder (German bank format with semicolon delimiters)
2. Filename multipliers parsed (e.g., `0.5x_` prefix indicates 50% shared account)
3. Transactions parsed and stored with fields: date, description, beneficiary, amount, currency, transaction_type, multiplier
4. Keyword-based categorization into predefined categories (groceries, eating_out, rent, utilities, etc.)
5. Expense totals calculated (negative amounts only) with multiplier applied for shared accounts
6. Visualization created and summary printed

### CSV Format Expected
German bank statement format with semicolon delimiters:
- `Buchungstag`: Transaction date
- `Verwendungszweck`: Description/purpose
- `Beguenstigter/Zahlungspflichtiger`: Beneficiary/payer
- `Betrag`: Amount (German format with comma as decimal separator)
- `Waehrung`: Currency

### Filename Multipliers
For shared accounts, prefix the CSV filename with a multiplier:
- `0.5x_joint_account.csv`: 50% of expenses counted (50/50 shared account)
- `0.33x_shared.csv`: 33% of expenses counted (1/3 responsibility)
- `account.csv`: 100% of expenses counted (personal account)

### Category System
Predefined categories with German/English keywords for automatic classification:
- groceries, eating_out, pharmacy_health, rent, utilities, internet_phone, transport, insurance, shopping, pet_care, entertainment, bank_fees, income

Uncategorized transactions are reported separately for manual review.