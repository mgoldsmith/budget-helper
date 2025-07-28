# Budget Helper

A Python tool for analyzing German bank statement CSV files and categorizing expenses with visualization.

## What it does

- Reads CSV bank statements from the `statements/` folder
- Automatically categorizes transactions (groceries, rent, utilities, eating out, etc.)
- Generates a pie chart showing expense breakdown
- Prints a summary of spending by category

## How to run

1. Activate the virtual environment:
   ```bash
   source venv/bin/activate
   ```

2. Place your CSV bank statement files in the `statements/` folder

3. Run the analyzer:
   ```bash
   python expense_analyzer.py
   ```

The program will generate an `expense_breakdown.png` chart and display a summary in the terminal.

## Requirements

- Python 3.12+
- matplotlib
- numpy