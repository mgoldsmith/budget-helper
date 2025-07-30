#!/usr/bin/env python3
"""
Bank Statement Expense Analyzer
Reads CSV bank statements and categorizes expenses with visualization
"""

import argparse
import csv
import os
import re
from collections import defaultdict
from decimal import Decimal
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.patheffects as path_effects

def transaction_text(transaction):
    """Combine description, beneficiary, and type for keyword matching"""
    return transaction['description'].lower() + ' ' + transaction['beneficiary'].lower() + ' ' + transaction['transaction_type'].lower()

class ExpenseAnalyzer:
    def __init__(self, statements_folder="statements"):
        self.statements_folder = statements_folder
        self.transactions = []
        self.categories = defaultdict(list)
        self.uncategorized = []
        self.monthly_transactions = defaultdict(list)

        # Keywords for end of month transactions. If they're detected in the first 7 days of a month, they'll be moved to the 25th of the previous month.
        self.end_of_month_keywords = ["sev petten"]
        
        # Category mapping based on keywords in German/English
        self.category_keywords = {
            "groceries": [
                "edeka", "rewe", "netto", "lidl", "aldi", "kaufland", "penny",
                "supermarket", "grocery", "lebensmittel", "go asia", "hoffman", "trinkgut", "koro",
            ],
            "eating_out": [
                "restaurant", "pizza", "burger", "wolt", "lieferando", "deliveroo",
                "mcdonalds", "kfc", "subway", "doner", "döner", "cafe",
                "bar", "pub", "borgor", "brgrs", "salami social", "nguyen", "nihat dincoglu", "harcourt centre",
                "saigon com nieu", "asiagourmet", "panem garage", "koempul restau", "teegeback",
            ],
            "household_items": [
                "dm drogerie", "rossmann"
            ],
            "pharmacy_health": [
                "apotheke", "pharmacy", "arzt", "doctor",
                "kranken", "health", "medical", "blanka leeker", "techniker krankenkasse",
                "treatwell", "mikko karhulah", "buycycle",
            ],
            "rent_and_utilities": [
                "miete", "rent", "wohnung", "apartment", "sev petten",
                "vattenfall", "strom", "gas", "water", "wasser", "heating", "heizung",
                "electricity", "energie",
                "telekom", "vodafone", "o2", "internet", "telefon", "phone", "mobile",
                "1+1 telecom", "schufa", "squarespace",
            ],
            "transport": [
                "bvg", "deutsche bahn", "db", "taxi", "uber", "lyft", "benzin",
                "petrol", "gas station", "tankstelle", "mvg", "transport"
            ],
            "pet_care": [
                "fressnapf", "tierarzt", "veterinary", "pet", "dog", "cat",
                "hundesteuer", "tierbedarf", "drobeck", "getsafe", "tierarztpraxis",
            ],
            "entertainment": [
                "kino", "cinema", "spotify", "netflix", "concert", "ticket",
                "resident advisor", "club", "bar", "entertainment", "else event",
            ],
            "bank_fees": [
                "entgeltabschluss", "gebühr", "fee", "bank charge", "commission", "balance of settlement",
            ],
            "shopping": [
                "amazon", "zalando", "otto", "shop", "store", "online",
                "aliexpress",
            ],
        }

    def read_csv_files(self):
        """Read all CSV files in the statements folder"""
        csv_files = [f for f in os.listdir(self.statements_folder) if f.endswith('.CSV') or f.endswith('.csv')]
        
        for filename in csv_files:
            filepath = os.path.join(self.statements_folder, filename)
            print(f"Reading {filename}...")
            
            # Try different encodings
            encodings = ['utf-8', 'iso-8859-1', 'cp1252', 'latin1']
            content = None
            
            for encoding in encodings:
                try:
                    with open(filepath, 'r', encoding=encoding) as file:
                        content = file.read()
                        # Skip BOM if present
                        if content.startswith('\ufeff'):
                            content = content[1:]
                        break
                except UnicodeDecodeError:
                    continue
            
            if content is None:
                print(f"Could not decode file {filename}")
                continue
            
            # Skip lines until we find the header row
            lines = content.splitlines()
            header_line_idx = 0
            
            for i, line in enumerate(lines):
                # Look for Deutsche Bank format header
                if 'Booking date' in line and 'Transaction Type' in line:
                    header_line_idx = i
                    break
                # Look for CAMT V8 format header
                elif 'Buchungstag' in line:
                    header_line_idx = i
                    break
            
            # Parse CSV with semicolon delimiter starting from header
            csv_lines = lines[header_line_idx:]
            reader = csv.DictReader(csv_lines, delimiter=';')
            
            for row in reader:
                transaction = None
                
                # Detect format and extract accordingly
                if 'Booking date' in row:
                    # Deutsche Bank format
                    transaction = self._parse_deutsche_bank_row(row)
                elif 'Buchungstag' in row:
                    # CAMT V8 format
                    transaction = self._parse_camt_v8_row(row)
                
                if transaction and transaction['amount'] < 0:  # Skip zero and positive amounts
                    self.transactions.append(transaction)

    def _parse_camt_v8_row(self, row):
        """Parse row in CAMT V8 CSV format"""
        return {
            'date': row.get('Buchungstag', ''),
            'description': row.get('Verwendungszweck', ''),
            'beneficiary': row.get('Beguenstigter/Zahlungspflichtiger', ''),
            'amount': self.parse_amount(row.get('Betrag', '0')),
            'currency': row.get('Waehrung', 'EUR'),
            'transaction_type': row.get('Buchungstext', ''),
            'raw_row': row
        }

    def _parse_deutsche_bank_row(self, row):
        """Parse row in Deutsche Bank CSV format"""
        # Deutsche Bank uses separate Debit/Credit columns
        debit = (row.get('Debit') or '').strip()
        credit = (row.get('Credit') or '').strip()
        
        # Determine amount (negative for debits, positive for credits)
        amount = Decimal('0')
        if debit:
            amount = self.parse_amount(debit)  # Deutsche Bank CSV already has negative values in debit
        elif credit:
            amount = self.parse_amount(credit)
        
        return {
            'date': self._convert_deutsche_bank_date(row.get('Booking date', '')),
            'description': row.get('Payment Details', ''),
            'beneficiary': row.get('Beneficiary / Originator', ''),
            'amount': amount,
            'currency': row.get('Currency', 'EUR'),
            'transaction_type': row.get('Transaction Type', ''),
            'raw_row': row
        }

    def _convert_deutsche_bank_date(self, date_str):
        """Convert Deutsche Bank date format (MM/DD/YYYY) to German format (DD.MM.YY)"""
        if not date_str:
            return ''
        
        try:
            # Parse MM/DD/YYYY format
            date_obj = datetime.strptime(date_str, '%m/%d/%Y')
            # Convert to DD.MM.YY format to match existing code
            return date_obj.strftime('%d.%m.%y')
        except:
            return date_str  # Return as-is if parsing fails

    def parse_amount(self, amount_str):
        """Parse German-style amount string to decimal"""
        if not amount_str:
            return Decimal('0')
        
        # Replace comma with dot for decimal parsing
        amount_str = amount_str.replace(',', '.')
        try:
            return Decimal(amount_str)
        except:
            return Decimal('0')

    def parse_date(self, date_str):
        """Parse German date format DD.MM.YY to datetime and return YYYY-MM format"""
        try:
            # Parse DD.MM.YY format
            date_obj = datetime.strptime(date_str, '%d.%m.%y')
            return date_obj.strftime('%Y-%m')
        except:
            return None

    def adjust_date_if_necessary(self, transaction):
        """Adjust date to 25th of previous month if transaction is unique by month"""
        needs_adjustment = False
        for keyword in self.end_of_month_keywords:
            if keyword.lower() in transaction_text(transaction):
                needs_adjustment = True
                break
        if not needs_adjustment:
            return

        date = datetime.strptime(transaction['date'], '%d.%m.%y')
        if date is None:
            raise ValueError(f"No valid date found in transaction: {transaction}")
        
        # Check if transaction is in the first 7 days of the month
        if date.day <= 7:
            newdate = None
            if date.month == 1:
                newdate = date.replace(day=25, month=12, year=date.year - 1)
            else:
                newdate = date.replace(day=25, month=date.month - 1)
            transaction['date'] = newdate.strftime('%d.%m.%y')

    def group_transactions_by_month(self):
        """Group transactions by year-month"""
        for transaction in self.transactions:
            self.adjust_date_if_necessary(transaction)
            month_key = self.parse_date(transaction['date'])
            if month_key == None:
                raise ValueError(f"No valid date found in transaction: {transaction}")
            self.monthly_transactions[month_key].append(transaction)

    def categorize_transactions(self):
        """Categorize transactions based on keywords"""
        for transaction in self.transactions:
            category = self.classify_transaction(transaction)
            
            if category:
                self.categories[category].append(transaction)
            else:
                self.uncategorized.append(transaction)

    def categorize_monthly_transactions(self, transactions):
        """Categorize a specific list of transactions"""
        monthly_categories = defaultdict(list)
        monthly_uncategorized = []
        
        for transaction in transactions:
            category = self.classify_transaction(transaction)
            
            if category:
                monthly_categories[category].append(transaction)
            else:
                monthly_uncategorized.append(transaction)
        
        return monthly_categories, monthly_uncategorized

    def classify_transaction(self, transaction):
        """Classify a single transaction into a category"""
        # Combine description and beneficiary for keyword matching
        text_to_check = transaction_text(transaction)
        
        # Check each category
        for category, keywords in self.category_keywords.items():
            for keyword in keywords:
                if keyword.lower() in text_to_check:
                    return category
        
        return None

    def calculate_category_totals(self):
        """Calculate total spending by category (negative amounts only)"""
        category_totals = {}
        
        for category, transactions in self.categories.items():
            total = sum(t['amount'] for t in transactions if t['amount'] < 0)
            if total < 0:  # Only include categories with expenses
                category_totals[category] = float(abs(total))
        
        return category_totals

    def calculate_monthly_category_totals(self, monthly_categories):
        """Calculate category totals for a specific month's data"""
        category_totals = {}
        
        for category, transactions in monthly_categories.items():
            total = sum(t['amount'] for t in transactions if t['amount'] < 0)
            if total < 0:  # Only include categories with expenses
                category_totals[category] = float(abs(total))
        
        return category_totals

    def create_expense_chart(self, category_totals, month=None):
        """Create a pie chart of expense categories"""
        if not category_totals:
            print("No expenses to chart")
            return
        
        # Sort categories by amount (descending)
        sorted_categories = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)
        
        categories = [cat.replace('_', ' ').title() for cat, _ in sorted_categories]
        amounts = [amount for _, amount in sorted_categories]
        total_expenses = sum(amounts)
        
        # Create pie chart with legend instead of labels to avoid overlap
        plt.figure(figsize=(14, 8))
        colors = plt.cm.Set3(range(len(categories)))
        
        # Custom autopct function that only shows percentages for slices > 3%
        def make_autopct(values):
            def my_autopct(pct):
                if pct >= 3.0:  # Only show text for slices >= 3%
                    absolute = int(pct/100.*sum(values))
                    return f'€{absolute}\n({pct:.1f}%)'
                return ''
            return my_autopct
        
        wedges, texts, autotexts = plt.pie(
            amounts, 
            labels=None,  # Remove direct labels to avoid crowding
            autopct=make_autopct(amounts),
            startangle=90,
            colors=colors,
            pctdistance=0.85  # Move percentage text closer to center
        )
        
        # Improve text readability for displayed percentages
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontsize(10)
            autotext.set_weight('bold')
            autotext.set_ha('center')
            # Add black outline for better visibility on light backgrounds
            autotext.set_path_effects([
                path_effects.withStroke(linewidth=3, foreground='black')
            ])
        
        # Create legend with amounts and percentages
        legend_labels = []
        for cat, amount in zip(categories, amounts):
            percentage = (amount / total_expenses) * 100
            legend_labels.append(f'{cat}: €{amount:.0f} ({percentage:.1f}%)')
        
        plt.legend(wedges, legend_labels, 
                  title="Categories", 
                  loc="center left", 
                  bbox_to_anchor=(1, 0, 0.5, 1),
                  fontsize=10)
        
        title = f'Expense Breakdown by Category - {month}' if month else 'Expense Breakdown by Category'
        plt.title(title, fontsize=16, fontweight='bold', pad=20)
        plt.axis('equal')
        
        # Add total at bottom
        plt.figtext(0.5, 0.02, f'Total Expenses: €{total_expenses:.2f}', 
                   ha='center', fontsize=12, fontweight='bold')
        
        plt.tight_layout()
        filename = f'expense_breakdown_{month}.png' if month else 'expense_breakdown.png'
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.show()
        print(f"Chart saved as {filename}")

    def print_summary(self, category_totals, month=None):
        """Print summary of expenses by category"""
        title = f"EXPENSE SUMMARY BY CATEGORY - {month}" if month else "EXPENSE SUMMARY BY CATEGORY"
        print("\n" + "="*50)
        print(title)
        print("="*50)
        
        total_expenses = sum(category_totals.values())
        
        for category, amount in sorted(category_totals.items(), key=lambda x: x[1], reverse=True):
            percentage = (amount / total_expenses) * 100 if total_expenses > 0 else 0
            print(f"{category.replace('_', ' ').title():<20}: €{amount:>8.2f} ({percentage:5.1f}%)")
        
        print("-" * 50)
        print(f"{'Total Expenses':<20}: €{total_expenses:>8.2f}")

    def print_uncategorized(self):
        """Print transactions that couldn't be categorized"""
        if not self.uncategorized:
            print("\nAll transactions were successfully categorized!")
            return
        
        print("\n" + "="*80)
        print("UNCATEGORIZED TRANSACTIONS")
        print("="*80)
        print("These transactions couldn't be confidently categorized:")
        print()
        
        # Only show expenses (negative amounts)
        uncategorized_expenses = [t for t in self.uncategorized if t['amount'] < 0]
        
        for transaction in uncategorized_expenses:
            print(f"Date: {transaction['date']}")
            print(f"Amount: €{transaction['amount']}")
            print(f"Description: {transaction['description']}")
            print(f"Beneficiary: {transaction['beneficiary']}")
            print(f"Type: {transaction['transaction_type']}")
            print("-" * 80)

    def print_monthly_uncategorized(self, uncategorized_transactions, month):
        """Print uncategorized transactions for a specific month"""
        print(f"\n{'='*50}")
        print(f"UNCATEGORIZED TRANSACTIONS - {month}")
        print(f"{'='*50}")
        print(f"These transactions couldn't be confidently categorized:")
        print()
        
        # Only show expenses (negative amounts)
        uncategorized_expenses = [t for t in uncategorized_transactions if t['amount'] < 0]
        
        for transaction in uncategorized_expenses:
            print(f"Date: {transaction['date']}")
            print(f"Amount: €{transaction['amount']}")
            print(f"Description: {transaction['description']}")
            print(f"Beneficiary: {transaction['beneficiary']}")
            print(f"Type: {transaction['transaction_type']}")
            print("-" * 50)

    def run_analysis(self):
        """Run the complete expense analysis by month"""
        print("Starting bank statement analysis...")
        
        # Read CSV files
        self.read_csv_files()
        print(f"Loaded {len(self.transactions)} transactions")
        
        # Group transactions by month
        self.group_transactions_by_month()
        print(f"Found data for {len(self.monthly_transactions)} months")
        
        # Process each month separately
        for month in sorted(self.monthly_transactions.keys()):
            print(f"\n{'='*60}")
            print(f"Processing {month}")
            print(f"{'='*60}")
            
            month_transactions = self.monthly_transactions[month]
            print(f"Transactions for {month}: {len(month_transactions)}")
            
            # Categorize monthly transactions
            monthly_categories, monthly_uncategorized = self.categorize_monthly_transactions(month_transactions)
            
            # Calculate monthly totals
            monthly_category_totals = self.calculate_monthly_category_totals(monthly_categories)
            
            # Print monthly summary
            if monthly_category_totals:
                self.print_summary(monthly_category_totals, month)
                
                # Create monthly chart
                self.create_expense_chart(monthly_category_totals, month)
            else:
                print(f"No expenses found for {month}")
            
            # Print uncategorized for this month
            if monthly_uncategorized:
                self.print_monthly_uncategorized(monthly_uncategorized, month)

    def audit_categories(self):
        """Print all categories with their transactions for auditing"""
        print("Starting bank statement analysis...")
        
        # Read CSV files
        self.read_csv_files()
        print(f"Loaded {len(self.transactions)} transactions")
        
        # Categorize transactions
        self.categorize_transactions()
        
        print("\n" + "="*80)
        print("CATEGORY AUDIT")
        print("="*80)
        
        # Print each category with its transactions
        for category, transactions in sorted(self.categories.items()):
            print(f"\n{category.replace('_', ' ').upper()}:")
            print("-" * 40)
            
            total = sum(abs(t['amount']) for t in transactions if t['amount'] < 0)
            print(f"Total: €{total:.2f} ({len(transactions)} transactions)")
            print()
            
            for transaction in transactions:
                if transaction['amount'] < 0:  # Only show expenses
                    print(f"  {transaction['date']} | €{abs(transaction['amount']):>7.2f} | {transaction['beneficiary'][:30]:<30} | {transaction['description'][:40]}")
        
        # Print uncategorized
        if self.uncategorized:
            print(f"\nUNCATEGORIZED:")
            print("-" * 40)
            uncategorized_expenses = [t for t in self.uncategorized if t['amount'] < 0]
            total = sum(abs(t['amount']) for t in uncategorized_expenses)
            print(f"Total: €{total:.2f} ({len(uncategorized_expenses)} transactions)")
            print()
            
            for transaction in uncategorized_expenses:
                print(f"  {transaction['date']} | €{abs(transaction['amount']):>7.2f} | {transaction['beneficiary'][:30]:<30} | {transaction['description'][:40]}")


def main():
    parser = argparse.ArgumentParser(description='Analyze bank statement expenses')
    parser.add_argument('--audit-categories', action='store_true', 
                        help='Print categories and their contents instead of creating pie chart')
    
    args = parser.parse_args()
    
    analyzer = ExpenseAnalyzer()
    
    if args.audit_categories:
        analyzer.audit_categories()
    else:
        analyzer.run_analysis()


if __name__ == "__main__":
    main()