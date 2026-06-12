#!/usr/bin/env python3
"""
Import scores from the original CSV file with actual score data.
"""
import sqlite3
import csv
import os

CSV_PATH = '/Users/mgriffin/Documents/NIST CSF/source/nist_csf_core.csv'
DB_PATH = '/Users/mgriffin/nist-csf-tracker/data/nist_csf.db'

def import_scores():
    """Import scores from CSV into database."""
    conn = sqlite3.connect(DB_PATH)
    db = conn.cursor()

    print(f"Importing scores from: {CSV_PATH}")

    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader)  # Skip header

        updated_count = 0
        missing_count = 0

        for row in reader:
            if len(row) < 7:
                continue

            subcategory_val = row[2].strip() if len(row) > 2 else ''
            if not subcategory_val or ':' not in subcategory_val:
                continue

            # Parse subcategory code like "GV.OC-01"
            parts = subcategory_val.split(':', 1)
            sub_code = parts[0].strip()

            # Get scores from columns
            prior_year = row[3].strip() if len(row) > 3 else ''  # 2025 (prior)
            current = row[4].strip() if len(row) > 4 else ''      # Current
            current_goal = row[5].strip() if len(row) > 5 else '' # 2026 Target
            next_goal = row[6].strip() if len(row) > 6 else ''    # 2027 estimate

            # Get notes and project info
            notes = row[10].strip() if len(row) > 10 else ''
            project = row[8].strip() if len(row) > 8 else ''

            def parse_score(val):
                try:
                    return float(val) if val and val.replace('.', '').replace('-', '').isdigit() else None
                except:
                    return None

            prior_val = parse_score(prior_year)
            current_val = parse_score(current)
            goal_val = parse_score(current_goal)
            next_val = parse_score(next_goal)

            # Check if subcategory exists
            result = db.execute('SELECT id FROM subcategories WHERE code = ?', (sub_code,)).fetchone()

            if result:
                subcategory_id = result[0]

                # Check if score record exists
                score_result = db.execute(
                    'SELECT id FROM scores WHERE subcategory_id = ?', (subcategory_id,)
                ).fetchone()

                if score_result:
                    db.execute('''
                        UPDATE scores SET
                            prior_year_score = COALESCE(?, prior_year_score),
                            current_score = COALESCE(?, current_score),
                            current_year_goal = COALESCE(?, current_year_goal),
                            next_year_goal = COALESCE(?, next_year_goal),
                            notes = COALESCE(NULLIF(?, ''), notes),
                            project_improvements = COALESCE(NULLIF(?, ''), project_improvements)
                        WHERE subcategory_id = ?
                    ''', (prior_val, current_val, goal_val, next_val, notes, project, subcategory_id))
                    updated_count += 1
                else:
                    db.execute('''
                        INSERT INTO scores (subcategory_id, prior_year_score, current_score,
                                          current_year_goal, next_year_goal, notes, project_improvements)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (subcategory_id, prior_val, current_val, goal_val, next_val, notes, project))
                    updated_count += 1
            else:
                missing_count += 1

    conn.commit()

    # Print summary
    print(f"\nScores imported: {updated_count}")
    print(f"Subcategories not found: {missing_count}")

    # Show sample
    sample = db.execute('''
        SELECT s.code, sc.prior_year_score, sc.current_score, sc.current_year_goal, sc.next_year_goal
        FROM subcategories s
        JOIN scores sc ON s.id = sc.subcategory_id
        WHERE sc.prior_year_score IS NOT NULL OR sc.current_score IS NOT NULL
        LIMIT 10
    ''').fetchall()

    print(f"\nSample scores:")
    for row in sample:
        print(f"  {row[0]}: prior={row[1]} current={row[2]} goal={row[3]} next={row[4]}")

    conn.close()
    print("\nDone!")

if __name__ == '__main__':
    import_scores()
