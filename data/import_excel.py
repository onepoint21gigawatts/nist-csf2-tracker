#!/usr/bin/env python3
"""
Import NIST CSF data from the Excel file into the database.
"""
import sqlite3
import pandas as pd
import os

# Paths
EXCEL_PATH = '/Users/mgriffin/Downloads/_NIST CSF.xlsx'
DB_PATH = '/Users/mgriffin/nist-csf-tracker/data/nist_csf.db'

def import_from_excel():
    """Import NIST CSF data from Excel file."""
    print(f"Reading Excel file: {EXCEL_PATH}")

    # Read the Excel file
    df = pd.read_excel(EXCEL_PATH, sheet_name='NIST CSF Core ')
    print(f"Found {len(df)} rows")

    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    db = conn.cursor()

    # Clear existing data
    db.execute("DELETE FROM scores")
    db.execute("DELETE FROM subcategories")
    db.execute("DELETE FROM categories")
    db.execute("DELETE FROM functions")

    current_function = None
    current_function_id = None
    current_category = None
    current_category_id = None
    function_order = 0
    category_order = 0
    subcategory_order = 0

    # Process each row
    for idx, row in df.iterrows():
        function_val = str(row['Function']) if pd.notna(row['Function']) else ''
        category_val = str(row['Category']) if pd.notna(row['Category']) else ''
        subcategory_val = str(row['Subcategory']) if pd.notna(row['Subcategory']) else ''

        # Parse Function (e.g., "GOVERN (GV)")
        if function_val and '(' in function_val:
            function_order += 1
            parts = function_val.split('(')
            name = parts[0].strip()
            code = parts[1].replace(')', '').strip()

            db.execute(
                'INSERT INTO functions (code, name, sort_order) VALUES (?, ?, ?)',
                (code, name, function_order)
            )
            current_function_id = db.lastrowid
            current_function = function_val
            print(f"  Function: {code} - {name}")

        # Parse Category (e.g., "Organizational Context (GV.OC): ...")
        if category_val and '(' in category_val:
            category_order += 1
            # Extract code like "GV.OC"
            code_match = category_val.split('(')
            name_part = code_match[0].strip()
            cat_code = code_match[1].split(')')[0].strip() if len(code_match) > 1 else ''

            # Extract description
            if ':' in category_val:
                cat_name = category_val.split(':')[0].strip()
                # Remove the code from the name
                if '(' in cat_name:
                    cat_name = cat_name.split('(')[0].strip()
                cat_desc = category_val.split(':', 1)[1].strip()
            else:
                cat_name = name_part
                cat_desc = ''

            db.execute(
                'INSERT INTO categories (function_id, code, name, description, sort_order) VALUES (?, ?, ?, ?, ?)',
                (current_function_id, cat_code, cat_name, cat_desc, category_order)
            )
            current_category_id = db.lastrowid
            current_category = category_val

        # Parse Subcategory (e.g., "GV.OC-01: ...")
        if subcategory_val and ':' in subcategory_val:
            subcategory_order += 1
            parts = subcategory_val.split(':', 1)
            sub_code = parts[0].strip()
            sub_desc = parts[1].strip() if len(parts) > 1 else ''

            examples = str(row['Implementation Examples']) if pd.notna(row['Implementation Examples']) else ''
            references = str(row['Informative References']) if pd.notna(row['Informative References']) else ''

            db.execute(
                '''INSERT INTO subcategories
                   (category_id, code, description, implementation_examples, informative_references, sort_order)
                   VALUES (?, ?, ?, ?, ?, ?)''',
                (current_category_id, sub_code, sub_desc, examples, references, subcategory_order)
            )
            subcategory_id = db.lastrowid

            # Create default score record
            db.execute(
                '''INSERT INTO scores (subcategory_id) VALUES (?)''',
                (subcategory_id,)
            )

    conn.commit()

    # Print summary
    db.execute("SELECT COUNT(*) FROM functions")
    func_count = db.fetchone()[0]
    db.execute("SELECT COUNT(*) FROM categories")
    cat_count = db.fetchone()[0]
    db.execute("SELECT COUNT(*) FROM subcategories")
    sub_count = db.fetchone()[0]

    print(f"\nImport complete!")
    print(f"  Functions: {func_count}")
    print(f"  Categories: {cat_count}")
    print(f"  Subcategories: {sub_count}")

    conn.close()

if __name__ == '__main__':
    import_from_excel()
