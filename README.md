# Budget Helper

A Python tool for analyzing German bank statement CSV files and categorizing expenses with visualization.

## What it does

- Reads CSV bank statements from the `statements/` folder
- Supports shared account calculations with filename multipliers (e.g., `0.5x_account.csv` for 50/50 shared accounts)
- Automatically categorizes transactions (groceries, rent, utilities, eating out, etc.)
- Generates a pie chart showing expense breakdown
- Prints a summary of spending by category

## How to run

1. Activate the virtual environment:
   ```bash
   source venv/bin/activate
   ```

2. Place your CSV bank statement files in the `statements/` folder
   - For shared accounts, prefix the filename with the multiplier (e.g., `0.5x_joint_account.csv` for a 50/50 shared account)
   - Regular accounts use standard filenames (e.g., `personal_account.csv`)

3. Run the analyzer:
   ```bash
   python expense_analyzer.py
   ```

The program will generate an `expense_breakdown.png` chart and display a summary in the terminal.

## Requirements

- Python 3.12+
- matplotlib
- numpy