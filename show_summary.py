#!/usr/bin/env python3
"""Display NIST CSF Score Summary"""
import sqlite3
import sys

db_path = '/Users/mgriffin/nist-csf-tracker/data/nist_csf.db'
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

# Get overall averages
overall = conn.execute('''
    SELECT
        AVG(prior_year_score) as avg_prior,
        AVG(current_score) as avg_current,
        AVG(current_year_goal) as avg_current_goal,
        AVG(next_year_goal) as avg_next_goal
    FROM scores
''').fetchone()

# Get function-level averages
functions = conn.execute('''
    SELECT
        f.code, f.name,
        AVG(sc.prior_year_score) as avg_prior,
        AVG(sc.current_score) as avg_current,
        AVG(sc.current_year_goal) as avg_current_goal,
        AVG(sc.next_year_goal) as avg_next_goal
    FROM functions f
    JOIN categories c ON f.id = c.function_id
    JOIN subcategories s ON c.id = s.category_id
    JOIN scores sc ON s.id = sc.subcategory_id
    GROUP BY f.id
    ORDER BY f.sort_order
''').fetchall()

print("=" * 70)
print("           NIST CSF 2.0 MATURITY SCORE SUMMARY")
print("=" * 70)
print()
print("OVERALL SCORES:")
print(f"  Prior Year Average:     {overall['avg_prior']:.2f}")
print(f"  Current Score Average:  {overall['avg_current']:.2f}")
print(f"  Current Year Goal:      {overall['avg_current_goal']:.2f}")
print(f"  Next Year Goal:         {overall['avg_next_goal']:.2f}")
print()
print("BY FUNCTION:")
print("-" * 70)
print(f"{'Function':<20} {'Prior':>10} {'Current':>10} {'Goal':>10} {'Next':>10}")
print("-" * 70)
for f in functions:
    name = f"{f['code']} - {f['name'][:12]}"
    print(f"{name:<20} {f['avg_prior']:>10.2f} {f['avg_current']:>10.2f} {f['avg_current_goal']:>10.2f} {f['avg_next_goal']:>10.2f}")
print("-" * 70)
print()
print("SCORING GUIDE:")
print("  0.0-1.0 = Initial (Ad-hoc)")
print("  1.1-2.0 = Developing")
print("  2.1-3.0 = Defined")
print("  3.1-4.0 = Managed")
print("  4.1-5.0 = Optimized")
print()
conn.close()
