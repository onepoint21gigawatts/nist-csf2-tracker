#!/usr/bin/env python3
"""
Database initialization script for NIST CSF Tracker.
Run this script once to set up the database with sample data.
"""

import csv
import sqlite3
import os

DATABASE = os.path.join(os.path.dirname(__file__), 'nist_csf.db')

def init_db():
    """Initialize the database schema."""
    conn = sqlite3.connect(DATABASE)
    db = conn.cursor()

    # Create Functions table
    db.execute('''
        CREATE TABLE IF NOT EXISTS functions (
            id INTEGER PRIMARY KEY,
            code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            description TEXT,
            sort_order INTEGER DEFAULT 0
        )
    ''')

    # Create Categories table
    db.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY,
            function_id INTEGER NOT NULL,
            code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            description TEXT,
            sort_order INTEGER DEFAULT 0,
            FOREIGN KEY (function_id) REFERENCES functions(id)
        )
    ''')

    # Create Subcategories table
    db.execute('''
        CREATE TABLE IF NOT EXISTS subcategories (
            id INTEGER PRIMARY KEY,
            category_id INTEGER NOT NULL,
            code TEXT NOT NULL UNIQUE,
            description TEXT NOT NULL,
            implementation_examples TEXT,
            informative_references TEXT,
            sort_order INTEGER DEFAULT 0,
            FOREIGN KEY (category_id) REFERENCES categories(id)
        )
    ''')

    # Create Scores table
    db.execute('''
        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY,
            subcategory_id INTEGER NOT NULL,
            prior_year_score REAL,
            prior_year_locked INTEGER DEFAULT 0,
            current_score REAL,
            current_year_goal REAL,
            next_year_goal REAL,
            notes TEXT,
            project_improvements TEXT,
            score_impact TEXT,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_by TEXT DEFAULT 'system',
            FOREIGN KEY (subcategory_id) REFERENCES subcategories(id),
            UNIQUE(subcategory_id)
        )
    ''')

    # Create Override Audit Log table
    db.execute('''
        CREATE TABLE IF NOT EXISTS override_log (
            id INTEGER PRIMARY KEY,
            subcategory_id INTEGER NOT NULL,
            field_name TEXT NOT NULL,
            old_value TEXT,
            new_value TEXT,
            reason TEXT,
            overridden_by TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (subcategory_id) REFERENCES subcategories(id)
        )
    ''')

    # Create Settings table for year configuration
    db.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    return conn

def load_csv_data(conn, csv_path):
    """Load NIST CSF data from CSV file."""
    db = conn.cursor()

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader)  # Skip header

        current_function = None
        current_function_id = None
        current_category = None
        current_category_id = None
        function_order = 0
        category_order = 0
        subcategory_order = 0

        for row in reader:
            if len(row) < 3:
                continue

            function_val = row[0].strip() if row[0] else ''
            category_val = row[1].strip() if row[1] else ''
            subcategory_val = row[2].strip() if row[2] else ''

            # Parse Function
            if function_val and '(' in function_val:
                function_order += 1
                code_match = function_val.split('(')
                name = code_match[0].strip()
                code = code_match[1].replace(')', '').strip() if len(code_match) > 1 else ''

                # Insert or get function
                db.execute('SELECT id FROM functions WHERE code = ?', (code,))
                result = db.fetchone()
                if not result:
                    db.execute(
                        '''INSERT INTO functions (code, name, sort_order)
                           VALUES (?, ?, ?)''',
                        (code, name, function_order)
                    )
                    current_function_id = db.lastrowid
                else:
                    current_function_id = result[0]
                current_function = function_val

            # Parse Category
            if category_val and '(' in category_val:
                category_order += 1
                # Parse category code like "GV.OC"
                code_match = category_val.split('(')
                name_part = code_match[0].strip()
                cat_code = code_match[1].replace(')', '').strip() if len(code_match) > 1 else ''

                # Extract description from name
                if ':' in name_part:
                    cat_name = name_part.split(':')[0].strip()
                    cat_desc = name_part.split(':', 1)[1].strip() if len(name_part.split(':', 1)) > 1 else ''
                else:
                    cat_name = name_part
                    cat_desc = ''

                # Insert or get category
                db.execute('SELECT id FROM categories WHERE code = ?', (cat_code,))
                result = db.fetchone()
                if not result:
                    db.execute(
                        '''INSERT INTO categories (function_id, code, name, description, sort_order)
                           VALUES (?, ?, ?, ?, ?)''',
                        (current_function_id, cat_code, cat_name, cat_desc, category_order)
                    )
                    current_category_id = db.lastrowid
                else:
                    current_category_id = result[0]
                current_category = category_val

            # Parse Subcategory
            if subcategory_val and ':' in subcategory_val:
                subcategory_order += 1
                # Parse subcategory code like "GV.OC-01"
                parts = subcategory_val.split(':', 1)
                sub_code = parts[0].strip()
                sub_desc = parts[1].strip() if len(parts) > 1 else ''

                # Get scores from CSV
                prior_year = row[3] if len(row) > 3 else None
                current = row[4] if len(row) > 4 else None
                current_goal = row[5] if len(row) > 5 else None
                next_goal = row[6] if len(row) > 6 else None
                project = row[8] if len(row) > 8 else ''
                impact = row[9] if len(row) > 9 else ''
                notes = row[10] if len(row) > 10 else ''
                examples = row[11] if len(row) > 11 else ''
                references = row[12] if len(row) > 12 else ''

                # Insert or get subcategory
                db.execute('SELECT id FROM subcategories WHERE code = ?', (sub_code,))
                result = db.fetchone()
                if not result:
                    db.execute(
                        '''INSERT INTO subcategories
                           (category_id, code, description, implementation_examples,
                            informative_references, sort_order)
                           VALUES (?, ?, ?, ?, ?, ?)''',
                        (current_category_id, sub_code, sub_desc, examples, references, subcategory_order)
                    )
                    subcategory_id = db.lastrowid
                else:
                    subcategory_id = result[0]
                    # Update if needed
                    db.execute(
                        '''UPDATE subcategories SET description = ?, implementation_examples = ?,
                           informative_references = ? WHERE id = ?''',
                        (sub_desc, examples, references, subcategory_id)
                    )

                # Insert or update scores
                def parse_score(val):
                    try:
                        return float(val) if val and val.strip() else None
                    except:
                        return None

                db.execute('SELECT id FROM scores WHERE subcategory_id = ?', (subcategory_id,))
                score_result = db.fetchone()

                if not score_result:
                    db.execute(
                        '''INSERT INTO scores
                           (subcategory_id, prior_year_score, current_score,
                            current_year_goal, next_year_goal, notes,
                            project_improvements, score_impact)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                        (subcategory_id, parse_score(prior_year), parse_score(current),
                         parse_score(current_goal), parse_score(next_goal), notes,
                         project, impact)
                    )

    conn.commit()

def main():
    """Main initialization function."""
    print("Initializing NIST CSF Tracker database...")

    # Initialize database
    conn = init_db()
    print("Database schema created.")

    # Load data from CSV
    csv_path = os.path.join(os.path.dirname(__file__), 'nist_csf_core.csv')
    if os.path.exists(csv_path):
        load_csv_data(conn, csv_path)
        print(f"Data loaded from {csv_path}")
    else:
        print(f"CSV file not found: {csv_path}")
        print("Please copy nist_csf_core.csv to the data directory.")

    # Set default year settings
    db = conn.cursor()
    db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('prior_year', '2024')")
    db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('current_year', '2025')")
    conn.commit()

    # Print summary
    db.execute("SELECT COUNT(*) FROM functions")
    func_count = db.fetchone()[0]
    db.execute("SELECT COUNT(*) FROM categories")
    cat_count = db.fetchone()[0]
    db.execute("SELECT COUNT(*) FROM subcategories")
    sub_count = db.fetchone()[0]
    db.execute("SELECT COUNT(*) FROM scores WHERE prior_year_score IS NOT NULL")
    score_count = db.fetchone()[0]

    print(f"\nDatabase Summary:")
    print(f"  Functions: {func_count}")
    print(f"  Categories: {cat_count}")
    print(f"  Subcategories: {sub_count}")
    print(f"  Scores: {score_count}")

    conn.close()
    print("\nDatabase initialization complete!")

if __name__ == '__main__':
    main()
