#!/usr/bin/env python3
"""
Bank Statement Expense Analyzer
Reads CSV bank statements and categorizes expenses with visualization
"""

import csv
import os
import re
from collections import defaultdict
from decimal import Decimal
import matplotlib.pyplot as plt
import matplotlib.patheffects as path_effects

class ExpenseAnalyzer:
    def __init__(self, statements_folder="statements"):
        self.statements_folder = statements_folder
        self.transactions = []
        self.categories = defaultdict(list)
        self.uncategorized = []
        
        # Category mapping based on keywords in German/English
        self.category_keywords = {
            "groceries": [
                "edeka", "rewe", "netto", "lidl", "aldi", "kaufland", "penny",
                "supermarket", "grocery", "lebensmittel", "go asia",
            ],
            "eating_out": [
                "restaurant", "pizza", "burger", "wolt", "lieferando", "deliveroo",
                "mcdonalds", "kfc", "subway", "doner", "döner", "cafe",
                "bar", "pub", "borgor", "brgrs", "salami social", "nguyen",
            ],
            "household_items": [
                "dm drogerie", "rossmann"
            ],
            "pharmacy_health": [
                "apotheke", "pharmacy", "arzt", "doctor",
                "kranken", "health", "medical", "blanka leeker", "techniker krankenkasse"
            ],
            "rent_and_utilities": [
                "miete", "rent", "wohnung", "apartment", "sev petten",
                "vattenfall", "strom", "gas", "water", "wasser", "heating", "heizung",
                "electricity", "energie",
                "telekom", "vodafone", "o2", "internet", "telefon", "phone", "mobile",
                "1+1 telecom"
            ],
            "transport": [
                "bvg", "deutsche bahn", "db", "taxi", "uber", "lyft", "benzin",
                "petrol", "gas station", "tankstelle", "mvg", "transport"
            ],
            "pet_care": [
                "fressnapf", "tierarzt", "veterinary", "pet", "dog", "cat",
                "hundesteuer", "tierbedarf", "drobeck", "getsafe",
            ],
            "entertainment": [
                "kino", "cinema", "spotify", "netflix", "concert", "ticket",
                "resident advisor", "club", "bar", "entertainment"
            ],
            "bank_fees": [
                "entgeltabschluss", "gebühr", "fee", "bank charge", "commission"
            ],
            "shopping": [
                "amazon", "zalando", "otto", "shop", "store", "koro", "online"
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
                
            # Parse CSV with semicolon delimiter
            reader = csv.DictReader(content.splitlines(), delimiter=';')
            
            for row in reader:
                # Extract key information
                transaction = {
                    'date': row.get('Buchungstag', ''),
                    'description': row.get('Verwendungszweck', ''),
                    'beneficiary': row.get('Beguenstigter/Zahlungspflichtiger', ''),
                    'amount': self.parse_amount(row.get('Betrag', '0')),
                    'currency': row.get('Waehrung', 'EUR'),
                    'transaction_type': row.get('Buchungstext', ''),
                    'raw_row': row
                }
                
                if transaction['amount'] < 0:  # Skip zero and positive amounts
                    self.transactions.append(transaction)

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

    def categorize_transactions(self):
        """Categorize transactions based on keywords"""
        for transaction in self.transactions:
            category = self.classify_transaction(transaction)
            
            if category:
                self.categories[category].append(transaction)
            else:
                self.uncategorized.append(transaction)

    def classify_transaction(self, transaction):
        """Classify a single transaction into a category"""
        # Combine description and beneficiary for keyword matching
        text_to_check = (
            transaction['description'].lower() + ' ' + 
            transaction['beneficiary'].lower() + ' ' +
            transaction['transaction_type'].lower()
        )
        
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

    def create_expense_chart(self, category_totals):
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
        
        plt.title('Expense Breakdown by Category', fontsize=16, fontweight='bold', pad=20)
        plt.axis('equal')
        
        # Add total at bottom
        plt.figtext(0.5, 0.02, f'Total Expenses: €{total_expenses:.2f}', 
                   ha='center', fontsize=12, fontweight='bold')
        
        plt.tight_layout()
        plt.savefig('expense_breakdown.png', dpi=300, bbox_inches='tight')
        plt.show()

    def print_summary(self, category_totals):
        """Print summary of expenses by category"""
        print("\n" + "="*50)
        print("EXPENSE SUMMARY BY CATEGORY")
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

    def run_analysis(self):
        """Run the complete expense analysis"""
        print("Starting bank statement analysis...")
        
        # Read CSV files
        self.read_csv_files()
        print(f"Loaded {len(self.transactions)} transactions")
        
        # Categorize transactions
        self.categorize_transactions()
        
        # Calculate totals
        category_totals = self.calculate_category_totals()
        
        # Print summary
        self.print_summary(category_totals)
        
        # Create chart
        if category_totals:
            self.create_expense_chart(category_totals)
        
        # Print uncategorized
        self.print_uncategorized()


def main():
    analyzer = ExpenseAnalyzer()
    analyzer.run_analysis()


if __name__ == "__main__":
    main()