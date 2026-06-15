#!/usr/bin/env python3
"""
NIST CSF 2.0 Tracker Application
A database-driven application for tracking NIST Cybersecurity Framework maturity scores.
"""

import sqlite3
import json
import os
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, jsonify, g, redirect, url_for, flash
from flask_compress import Compress

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(32).hex())
Compress(app)

DATABASE = os.path.join(os.path.dirname(__file__), 'data', 'nist_csf.db')

# Year colors for charts (Sonatype Brand Colors)
YEAR_COLORS = {
    'prior_year': '#ECEEF2',      # Code Grey
    'current_score': '#2D36EC',    # Electric Blue
    'current_year_goal': '#FE572A', # Alert Orange
    'next_year_goal': '#DAFF02'    # Highlighter Yellow
}


def get_db():
    """Get database connection."""
    db = getattr(g, '_database', None)
    if db is None:
        os.makedirs(os.path.dirname(DATABASE), exist_ok=True)
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys = ON')
    return db


@app.teardown_appcontext
def close_connection(exception):
    """Close database connection."""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


# ============================================================================
# WEB PAGES
# ============================================================================

@app.route('/')
def index():
    """Main dashboard page."""
    db = get_db()

    # Calculate years dynamically based on current date
    current_year_val = str(datetime.now().year)
    prior_year_val = str(datetime.now().year - 1)

    # Get year settings (allow override)
    prior_year_setting = db.execute(
        "SELECT value FROM settings WHERE key = 'prior_year'"
    ).fetchone()
    current_year_setting = db.execute(
        "SELECT value FROM settings WHERE key = 'current_year'"
    ).fetchone()

    # Use settings if they exist, otherwise use calculated values
    if current_year_setting:
        current_year_val = current_year_setting['value']
        # If current year is set, prior year should be current - 1 unless explicitly set
        if not prior_year_setting:
            prior_year_val = str(int(current_year_val) - 1)
    if prior_year_setting:
        prior_year_val = prior_year_setting['value']

    # Get summary statistics
    summary = db.execute('''
        SELECT
            f.code as function_code,
            f.name as function_name,
            COUNT(s.id) as total_subcategories,
            AVG(sc.prior_year_score) as avg_prior,
            AVG(sc.current_score) as avg_current,
            AVG(sc.current_year_goal) as avg_current_goal,
            AVG(sc.next_year_goal) as avg_next_goal
        FROM functions f
        JOIN categories c ON f.id = c.function_id
        JOIN subcategories s ON c.id = s.category_id
        LEFT JOIN scores sc ON s.id = sc.subcategory_id
        GROUP BY f.id
        ORDER BY f.sort_order
    ''').fetchall()

    # Calculate overall averages
    overall = db.execute('''
        SELECT
            AVG(prior_year_score) as avg_prior,
            AVG(current_score) as avg_current,
            AVG(current_year_goal) as avg_current_goal,
            AVG(next_year_goal) as avg_next_goal
        FROM scores
        WHERE prior_year_score IS NOT NULL
           OR current_score IS NOT NULL
    ''').fetchone()

    return render_template('index.html',
                         summary=summary,
                         overall=overall,
                         prior_year=prior_year_val,
                         current_year=current_year_val,
                         year_colors=YEAR_COLORS)


@app.route('/function/<function_code>')
def function_detail(function_code):
    """Detail page for a specific function."""
    db = get_db()

    func = db.execute(
        'SELECT * FROM functions WHERE code = ?', (function_code,)
    ).fetchone()

    if not func:
        flash('Function not found', 'error')
        return redirect(url_for('index'))

    # Calculate years dynamically based on current date
    current_year_val = str(datetime.now().year)
    prior_year_val = str(datetime.now().year - 1)

    # Get year settings (allow override)
    prior_year_setting = db.execute(
        "SELECT value FROM settings WHERE key = 'prior_year'"
    ).fetchone()
    current_year_setting = db.execute(
        "SELECT value FROM settings WHERE key = 'current_year'"
    ).fetchone()

    if current_year_setting:
        current_year_val = current_year_setting['value']
        if not prior_year_setting:
            prior_year_val = str(int(current_year_val) - 1)
    if prior_year_setting:
        prior_year_val = prior_year_setting['value']

    # Get all categories and subcategories with scores
    categories = db.execute('''
        SELECT
            c.id, c.code, c.name, c.description,
            COUNT(s.id) as subcategory_count
        FROM categories c
        LEFT JOIN subcategories s ON c.id = s.category_id
        WHERE c.function_id = ?
        GROUP BY c.id
        ORDER BY c.sort_order
    ''', (func['id'],)).fetchall()

    # Get subcategories with scores for each category
    category_data = []
    for cat in categories:
        subcategories = db.execute('''
            SELECT
                s.id, s.code, s.description, s.implementation_examples,
                sc.id as score_id, sc.prior_year_score, sc.current_score,
                sc.current_year_goal, sc.next_year_goal, sc.notes,
                sc.project_improvements, sc.score_impact, sc.prior_year_locked
            FROM subcategories s
            LEFT JOIN scores sc ON s.id = sc.subcategory_id
            WHERE s.category_id = ?
            ORDER BY s.sort_order
        ''', (cat['id'],)).fetchall()

        # Calculate averages for this category
        avg_prior = sum(s['prior_year_score'] or 0 for s in subcategories) / len(subcategories) if subcategories else 0
        avg_current = sum(s['current_score'] or 0 for s in subcategories) / len(subcategories) if subcategories else 0
        avg_goal = sum(s['current_year_goal'] or 0 for s in subcategories) / len(subcategories) if subcategories else 0
        avg_next = sum(s['next_year_goal'] or 0 for s in subcategories) / len(subcategories) if subcategories else 0

        category_data.append({
            'category': cat,
            'subcategories': subcategories,
            'averages': {
                'prior_year': round(avg_prior, 1),
                'current_score': round(avg_current, 1),
                'current_goal': round(avg_goal, 1),
                'next_goal': round(avg_next, 1)
            }
        })

    return render_template('function_detail.html',
                         function=func,
                         category_data=category_data,
                         current_year=current_year_val,
                         year_colors=YEAR_COLORS)


# ============================================================================
# API ENDPOINTS - SCORES
# ============================================================================

@app.route('/api/scores', methods=['GET'])
def api_get_all_scores():
    """
    Get all scores for all subcategories.

    Returns:
        JSON array of all subcategories with their scores
    """
    db = get_db()

    results = db.execute('''
        SELECT
            s.id as subcategory_id,
            s.code as subcategory_code,
            s.description,
            c.code as category_code,
            c.name as category_name,
            f.code as function_code,
            f.name as function_name,
            sc.prior_year_score,
            sc.current_score,
            sc.current_year_goal,
            sc.next_year_goal,
            sc.notes,
            sc.project_improvements,
            sc.score_impact,
            sc.prior_year_locked,
            sc.last_updated
        FROM subcategories s
        JOIN categories c ON s.category_id = c.id
        JOIN functions f ON c.function_id = f.id
        LEFT JOIN scores sc ON s.id = sc.subcategory_id
        ORDER BY f.sort_order, c.sort_order, s.sort_order
    ''').fetchall()

    return jsonify([dict(row) for row in results])


@app.route('/api/scores/<subcategory_code>', methods=['GET'])
def api_get_score(subcategory_code):
    """
    Get score for a specific subcategory by code (e.g., 'GV.OC-01').

    Args:
        subcategory_code: The subcategory code (e.g., 'GV.OC-01')

    Returns:
        JSON object with subcategory details and scores
    """
    db = get_db()

    result = db.execute('''
        SELECT
            s.id as subcategory_id,
            s.code as subcategory_code,
            s.description,
            s.implementation_examples,
            s.informative_references,
            c.code as category_code,
            c.name as category_name,
            f.code as function_code,
            f.name as function_name,
            sc.prior_year_score,
            sc.current_score,
            sc.current_year_goal,
            sc.next_year_goal,
            sc.notes,
            sc.project_improvements,
            sc.score_impact,
            sc.prior_year_locked,
            sc.last_updated
        FROM subcategories s
        JOIN categories c ON s.category_id = c.id
        JOIN functions f ON c.function_id = f.id
        LEFT JOIN scores sc ON s.id = sc.subcategory_id
        WHERE s.code = ?
    ''', (subcategory_code,)).fetchone()

    if not result:
        return jsonify({'error': 'Subcategory not found', 'code': subcategory_code}), 404

    return jsonify(dict(result))


@app.route('/api/scores/<subcategory_code>', methods=['PUT'])
def api_update_score(subcategory_code):
    """
    Update scores for a specific subcategory.

    Args:
        subcategory_code: The subcategory code (e.g., 'GV.OC-01')

    Request Body (JSON):
        {
            "prior_year_score": 2.5,
            "current_score": 3.0,
            "current_year_goal": 3.5,
            "next_year_goal": 4.0,
            "notes": "Optional notes",
            "project_improvements": "Optional improvement notes",
            "score_impact": "Optional impact notes",
            "override_reason": "Required if updating locked prior_year_score"
        }

    Returns:
        JSON object with success status and updated values
    """
    db = get_db()
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400

    # Get subcategory
    subcategory = db.execute(
        'SELECT id FROM subcategories WHERE code = ?', (subcategory_code,)
    ).fetchone()

    if not subcategory:
        return jsonify({'error': 'Subcategory not found', 'code': subcategory_code}), 404

    subcategory_id = subcategory['id']

    # Check current score record
    score = db.execute(
        'SELECT * FROM scores WHERE subcategory_id = ?', (subcategory_id,)
    ).fetchone()

    # Handle prior_year_score locking
    if 'prior_year_score' in data and score and score['prior_year_locked']:
        override_reason = data.get('override_reason')
        if not override_reason:
            return jsonify({
                'error': 'Prior year score is locked. Provide override_reason to update.',
                'locked': True
            }), 403

        # Log the override
        db.execute('''
            INSERT INTO override_log
            (subcategory_id, field_name, old_value, new_value, reason, overridden_by)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (subcategory_id, 'prior_year_score', score['prior_year_score'],
              data['prior_year_score'], override_reason, 'api_user'))

    # Build update query
    allowed_fields = [
        'prior_year_score', 'current_score', 'current_year_goal',
        'next_year_goal', 'notes', 'project_improvements', 'score_impact'
    ]

    updates = []
    params = []

    for field in allowed_fields:
        if field in data:
            updates.append(f'{field} = ?')
            params.append(data[field])

    if updates:
        updates.append('last_updated = CURRENT_TIMESTAMP')
        params.append(subcategory_id)

        db.execute(
            f"UPDATE scores SET {', '.join(updates)} WHERE subcategory_id = ?",
            params
        )
        db.commit()

    # Return updated record
    return api_get_score(subcategory_code)


@app.route('/api/scores/bulk', methods=['PUT'])
def api_bulk_update_scores():
    """
    Bulk update scores for multiple subcategories.

    Request Body (JSON):
        {
            "updates": [
                {
                    "subcategory_code": "GV.OC-01",
                    "prior_year_score": 2.5,
                    "current_score": 3.0,
                    ...
                },
                ...
            ]
        }

    Returns:
        JSON object with count of successful updates and any errors
    """
    db = get_db()
    data = request.get_json()

    if not data or 'updates' not in data:
        return jsonify({'error': 'No updates array provided'}), 400

    success_count = 0
    errors = []

    for update in data['updates']:
        subcategory_code = update.get('subcategory_code')
        if not subcategory_code:
            errors.append({'error': 'Missing subcategory_code', 'update': update})
            continue

        # Get subcategory
        subcategory = db.execute(
            'SELECT id FROM subcategories WHERE code = ?', (subcategory_code,)
        ).fetchone()

        if not subcategory:
            errors.append({'error': 'Subcategory not found', 'code': subcategory_code})
            continue

        subcategory_id = subcategory['id']

        # Check lock
        score = db.execute(
            'SELECT prior_year_locked FROM scores WHERE subcategory_id = ?', (subcategory_id,)
        ).fetchone()

        if 'prior_year_score' in update and score and score['prior_year_locked']:
            if not update.get('override_reason'):
                errors.append({
                    'error': 'Prior year score locked',
                    'code': subcategory_code,
                    'locked': True
                })
                continue

        # Update fields
        allowed_fields = [
            'prior_year_score', 'current_score', 'current_year_goal',
            'next_year_goal', 'notes', 'project_improvements', 'score_impact'
        ]

        updates = []
        params = []

        for field in allowed_fields:
            if field in update:
                updates.append(f'{field} = ?')
                params.append(update[field])

        if updates:
            updates.append('last_updated = CURRENT_TIMESTAMP')
            params.append(subcategory_id)

            db.execute(
                f"UPDATE scores SET {', '.join(updates)} WHERE subcategory_id = ?",
                params
            )
            success_count += 1

    db.commit()

    return jsonify({
        'success': True,
        'updated_count': success_count,
        'errors': errors if errors else None
    })


@app.route('/api/scores/<subcategory_code>/lock', methods=['POST'])
def api_toggle_lock(subcategory_code):
    """
    Lock or unlock the prior year score for a subcategory.

    Args:
        subcategory_code: The subcategory code

    Request Body (JSON):
        {
            "locked": true,  // true to lock, false to unlock
            "reason": "Optional reason for the action"
        }

    Returns:
        JSON object with new lock status
    """
    db = get_db()
    data = request.get_json() or {}

    # Get subcategory
    subcategory = db.execute(
        'SELECT id FROM subcategories WHERE code = ?', (subcategory_code,)
    ).fetchone()

    if not subcategory:
        return jsonify({'error': 'Subcategory not found'}), 404

    locked = data.get('locked', True)

    db.execute('''
        UPDATE scores SET prior_year_locked = ? WHERE subcategory_id = ?
    ''', (1 if locked else 0, subcategory['id']))

    # Log the action
    action = 'locked' if locked else 'unlocked'
    reason = data.get('reason', f'Prior year score {action} via API')

    db.execute('''
        INSERT INTO override_log
        (subcategory_id, field_name, old_value, new_value, reason, overridden_by)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (subcategory['id'], 'prior_year_locked', not locked, locked, reason, 'api_user'))

    db.commit()

    return jsonify({
        'success': True,
        'subcategory_code': subcategory_code,
        'locked': locked
    })


# ============================================================================
# API ENDPOINTS - AVERAGES & STATISTICS
# ============================================================================

@app.route('/api/averages', methods=['GET'])
def api_get_averages():
    """
    Get average scores by function and category.

    Query Parameters:
        function: Filter by function code (optional)
        category: Filter by category code (optional)

    Returns:
        JSON object with averages by function, category, and overall
    """
    db = get_db()

    function_filter = request.args.get('function')
    category_filter = request.args.get('category')

    # Overall averages
    overall_query = '''
        SELECT
            COUNT(*) as total,
            AVG(prior_year_score) as avg_prior,
            AVG(current_score) as avg_current,
            AVG(current_year_goal) as avg_goal,
            AVG(next_year_goal) as avg_next
        FROM scores
    '''
    overall = db.execute(overall_query).fetchone()

    # By Function
    function_query = '''
        SELECT
            f.code,
            f.name,
            COUNT(s.id) as subcategory_count,
            AVG(sc.prior_year_score) as avg_prior,
            AVG(sc.current_score) as avg_current,
            AVG(sc.current_year_goal) as avg_goal,
            AVG(sc.next_year_goal) as avg_next
        FROM functions f
        JOIN categories c ON f.id = c.function_id
        JOIN subcategories s ON c.id = s.category_id
        LEFT JOIN scores sc ON s.id = sc.subcategory_id
    '''

    if function_filter:
        function_query += ' WHERE f.code = ?'
        functions = db.execute(function_query + ' GROUP BY f.id ORDER BY f.sort_order',
                              (function_filter,)).fetchall()
    else:
        functions = db.execute(function_query + ' GROUP BY f.id ORDER BY f.sort_order').fetchall()

    # By Category
    category_query = '''
        SELECT
            f.code as function_code,
            c.code as category_code,
            c.name as category_name,
            COUNT(s.id) as subcategory_count,
            AVG(sc.prior_year_score) as avg_prior,
            AVG(sc.current_score) as avg_current,
            AVG(sc.current_year_goal) as avg_goal,
            AVG(sc.next_year_goal) as avg_next
        FROM categories c
        JOIN functions f ON c.function_id = f.id
        JOIN subcategories s ON c.id = s.category_id
        LEFT JOIN scores sc ON s.id = sc.subcategory_id
    '''

    if category_filter:
        category_query += ' WHERE c.code = ?'
        categories = db.execute(category_query + ' GROUP BY c.id ORDER BY f.sort_order, c.sort_order',
                               (category_filter,)).fetchall()
    elif function_filter:
        category_query += ' WHERE f.code = ?'
        categories = db.execute(category_query + ' GROUP BY c.id ORDER BY f.sort_order, c.sort_order',
                               (function_filter,)).fetchall()
    else:
        categories = db.execute(category_query + ' GROUP BY c.id ORDER BY f.sort_order, c.sort_order').fetchall()

    def safe_float(val):
        return round(val, 2) if val is not None else None

    return jsonify({
        'overall': {
            'total_subcategories': overall['total'],
            'avg_prior': safe_float(overall['avg_prior']),
            'avg_current': safe_float(overall['avg_current']),
            'avg_goal': safe_float(overall['avg_goal']),
            'avg_next': safe_float(overall['avg_next'])
        },
        'by_function': [dict(f) for f in functions],
        'by_category': [dict(c) for c in categories]
    })


@app.route('/api/chart-data', methods=['GET'])
def api_chart_data():
    """
    Get data formatted for chart rendering.

    Returns:
        JSON object with labels and data arrays for each score type
    """
    db = get_db()

    data = db.execute('''
        SELECT
            f.code as function_code,
            f.name as function_name,
            AVG(sc.prior_year_score) as prior_year,
            AVG(sc.current_score) as current_score,
            AVG(sc.current_year_goal) as current_goal,
            AVG(sc.next_year_goal) as next_goal
        FROM functions f
        JOIN categories c ON f.id = c.function_id
        JOIN subcategories s ON c.id = s.category_id
        LEFT JOIN scores sc ON s.id = sc.subcategory_id
        GROUP BY f.id
        ORDER BY f.sort_order
    ''').fetchall()

    overall = db.execute('''
        SELECT
            AVG(prior_year_score) as prior_year,
            AVG(current_score) as current_score,
            AVG(current_year_goal) as current_goal,
            AVG(next_year_goal) as next_goal
        FROM scores
    ''').fetchone()

    def safe_round(val):
        return round(val, 2) if val else 0

    return jsonify({
        'labels': [row['function_code'] for row in data],
        'full_labels': [row['function_name'] for row in data],
        'prior_year': [safe_round(row['prior_year']) for row in data],
        'current_score': [safe_round(row['current_score']) for row in data],
        'current_goal': [safe_round(row['current_goal']) for row in data],
        'next_goal': [safe_round(row['next_goal']) for row in data],
        'overall': {
            'prior_year': safe_round(overall['prior_year']),
            'current_score': safe_round(overall['current_score']),
            'current_goal': safe_round(overall['current_goal']),
            'next_goal': safe_round(overall['next_goal'])
        },
        'colors': YEAR_COLORS
    })


# ============================================================================
# API ENDPOINTS - FRAMEWORK STRUCTURE
# ============================================================================

@app.route('/api/functions', methods=['GET'])
def api_get_functions():
    """Get all NIST CSF functions."""
    db = get_db()

    functions = db.execute('''
        SELECT
            f.*,
            COUNT(DISTINCT c.id) as category_count,
            COUNT(DISTINCT s.id) as subcategory_count
        FROM functions f
        LEFT JOIN categories c ON f.id = c.function_id
        LEFT JOIN subcategories s ON c.id = s.category_id
        GROUP BY f.id
        ORDER BY f.sort_order
    ''').fetchall()

    return jsonify([dict(f) for f in functions])


@app.route('/api/categories', methods=['GET'])
def api_get_categories():
    """
    Get all categories, optionally filtered by function.

    Query Parameters:
        function: Filter by function code
    """
    db = get_db()

    function_filter = request.args.get('function')

    query = '''
        SELECT
            c.*,
            f.code as function_code,
            f.name as function_name,
            COUNT(s.id) as subcategory_count
        FROM categories c
        JOIN functions f ON c.function_id = f.id
        LEFT JOIN subcategories s ON c.id = s.category_id
    '''

    if function_filter:
        query += ' WHERE f.code = ?'
        results = db.execute(query + ' GROUP BY c.id ORDER BY c.sort_order', (function_filter,)).fetchall()
    else:
        results = db.execute(query + ' GROUP BY c.id ORDER BY f.sort_order, c.sort_order').fetchall()

    return jsonify([dict(r) for r in results])


@app.route('/api/subcategories', methods=['GET'])
def api_get_subcategories():
    """
    Get all subcategories, optionally filtered.

    Query Parameters:
        function: Filter by function code
        category: Filter by category code
    """
    db = get_db()

    function_filter = request.args.get('function')
    category_filter = request.args.get('category')

    query = '''
        SELECT
            s.id,
            s.code,
            s.description,
            s.implementation_examples,
            s.informative_references,
            c.code as category_code,
            c.name as category_name,
            f.code as function_code,
            f.name as function_name
        FROM subcategories s
        JOIN categories c ON s.category_id = c.id
        JOIN functions f ON c.function_id = f.id
    '''

    conditions = []
    params = []

    if function_filter:
        conditions.append('f.code = ?')
        params.append(function_filter)
    if category_filter:
        conditions.append('c.code = ?')
        params.append(category_filter)

    if conditions:
        query += ' WHERE ' + ' AND '.join(conditions)

    query += ' ORDER BY f.sort_order, c.sort_order, s.sort_order'

    results = db.execute(query, params).fetchall()

    return jsonify([dict(r) for r in results])


@app.route('/api/export', methods=['GET'])
def api_export_data():
    """Export all data as JSON."""
    db = get_db()

    results = db.execute('''
        SELECT
            f.code as function_code, f.name as function_name,
            c.code as category_code, c.name as category_name,
            s.code as subcategory_code, s.description,
            sc.prior_year_score, sc.current_score,
            sc.current_year_goal, sc.next_year_goal,
            sc.notes, sc.project_improvements, sc.score_impact, sc.prior_year_locked
        FROM functions f
        JOIN categories c ON f.id = c.function_id
        JOIN subcategories s ON c.id = s.category_id
        LEFT JOIN scores sc ON s.id = sc.subcategory_id
        ORDER BY f.sort_order, c.sort_order, s.sort_order
    ''').fetchall()

    return jsonify({
        'exported_at': datetime.utcnow().isoformat(),
        'total_records': len(results),
        'data': [dict(row) for row in results]
    })


@app.route('/api/export/csv', methods=['GET'])
def api_export_csv():
    """Export all data as CSV."""
    import csv
    import io
    from flask import Response

    db = get_db()

    results = db.execute('''
        SELECT
            f.code as function_code, f.name as function_name,
            c.code as category_code, c.name as category_name,
            s.code as subcategory_code, s.description,
            sc.prior_year_score, sc.current_score,
            sc.current_year_goal, sc.next_year_goal,
            sc.notes, sc.project_improvements, sc.score_impact
        FROM functions f
        JOIN categories c ON f.id = c.function_id
        JOIN subcategories s ON c.id = s.category_id
        LEFT JOIN scores sc ON s.id = sc.subcategory_id
        ORDER BY f.sort_order, c.sort_order, s.sort_order
    ''').fetchall()

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow([
        'subcategory_code', 'function_code', 'function_name',
        'category_code', 'category_name', 'description',
        'prior_year_score', 'current_score',
        'current_year_goal', 'next_year_goal',
        'notes', 'project_improvements', 'score_impact'
    ])

    # Write data rows
    for row in results:
        writer.writerow([
            row['subcategory_code'],
            row['function_code'],
            row['function_name'],
            row['category_code'],
            row['category_name'],
            row['description'],
            row['prior_year_score'] if row['prior_year_score'] is not None else '',
            row['current_score'] if row['current_score'] is not None else '',
            row['current_year_goal'] if row['current_year_goal'] is not None else '',
            row['next_year_goal'] if row['next_year_goal'] is not None else '',
            row['notes'] or '',
            row['project_improvements'] or '',
            row['score_impact'] or ''
        ])

    output.seek(0)

    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename=nist_csf_scores_{datetime.utcnow().strftime("%Y%m%d")}.csv'
        }
    )


@app.route('/api/export/excel', methods=['GET'])
def api_export_excel():
    """Export all data as Excel-compatible CSV (can be opened directly in Excel)."""
    import csv
    import io
    from flask import Response

    db = get_db()

    # Get year settings for headers
    prior_year = db.execute("SELECT value FROM settings WHERE key = 'prior_year'").fetchone()
    current_year = db.execute("SELECT value FROM settings WHERE key = 'current_year'").fetchone()

    prior_year_val = prior_year['value'] if prior_year else '2024'
    current_year_val = current_year['value'] if current_year else '2025'

    results = db.execute('''
        SELECT
            f.code as function_code, f.name as function_name,
            c.code as category_code, c.name as category_name,
            s.code as subcategory_code, s.description,
            sc.prior_year_score, sc.current_score,
            sc.current_year_goal, sc.next_year_goal,
            sc.notes, sc.project_improvements, sc.score_impact
        FROM functions f
        JOIN categories c ON f.id = c.function_id
        JOIN subcategories s ON c.id = s.category_id
        LEFT JOIN scores sc ON s.id = sc.subcategory_id
        ORDER BY f.sort_order, c.sort_order, s.sort_order
    ''').fetchall()

    # Create CSV in memory with BOM for Excel compatibility
    output = io.StringIO()
    # Write UTF-8 BOM for Excel
    output.write('﻿')
    writer = csv.writer(output)

    # Write header with year labels
    writer.writerow([
        'Subcategory Code',
        'Function Code',
        'Function Name',
        'Category Code',
        'Category Name',
        'Description',
        f'Prior Year Score ({prior_year_val})',
        'Current Score',
        f'Current Year Goal ({current_year_val})',
        'Next Year Goal',
        'Notes',
        'Project/Improvements',
        'Score Impact'
    ])

    # Write data rows
    for row in results:
        writer.writerow([
            row['subcategory_code'],
            row['function_code'],
            row['function_name'],
            row['category_code'],
            row['category_name'],
            row['description'],
            row['prior_year_score'] if row['prior_year_score'] is not None else '',
            row['current_score'] if row['current_score'] is not None else '',
            row['current_year_goal'] if row['current_year_goal'] is not None else '',
            row['next_year_goal'] if row['next_year_goal'] is not None else '',
            row['notes'] or '',
            row['project_improvements'] or '',
            row['score_impact'] or ''
        ])

    output.seek(0)

    return Response(
        output.getvalue(),
        mimetype='text/csv;charset=utf-8',
        headers={
            'Content-Disposition': f'attachment; filename=nist_csf_scores_{datetime.utcnow().strftime("%Y%m%d")}_excel.csv'
        }
    )


@app.route('/api/import', methods=['POST'])
def api_import_data():
    """
    Import scores from JSON.

    Request Body (JSON):
        {
            "data": [
                {
                    "subcategory_code": "GV.OC-01",
                    "prior_year_score": 2.5,
                    ...
                }
            ]
        }
    """
    db = get_db()
    data = request.get_json()

    if not data or 'data' not in data:
        return jsonify({'error': 'No data array provided'}), 400

    imported = 0
    errors = []

    for item in data['data']:
        code = item.get('subcategory_code')
        if not code:
            continue

        subcategory = db.execute(
            'SELECT id FROM subcategories WHERE code = ?', (code,)
        ).fetchone()

        if not subcategory:
            errors.append({'code': code, 'error': 'Not found'})
            continue

        # Update scores
        fields = ['prior_year_score', 'current_score', 'current_year_goal',
                  'next_year_goal', 'notes', 'project_improvements', 'score_impact']

        updates = []
        params = []

        for field in fields:
            if field in item:
                updates.append(f'{field} = ?')
                params.append(item[field])

        if updates:
            params.append(subcategory['id'])
            db.execute(
                f"UPDATE scores SET {', '.join(updates)} WHERE subcategory_id = ?",
                params
            )
            imported += 1

    db.commit()

    return jsonify({
        'success': True,
        'imported': imported,
        'errors': errors if errors else None
    })


@app.route('/api/import/csv', methods=['POST'])
def api_import_csv():
    """
    Import scores from CSV format (JSON body with parsed CSV data).

    Request Body (JSON):
        {
            "data": [
                {
                    "subcategory_code": "GV.OC-01",
                    "prior_year_score": 2.5,
                    ...
                }
            ]
        }

    Accepts flexible column names:
        - subcategory_code or Subcategory Code or Subcategory_Code
        - prior_year_score or Prior Year Score or Prior_Year_Score
        - current_score or Current Score
        - etc.
    """
    db = get_db()
    data = request.get_json()

    if not data or 'data' not in data:
        return jsonify({'error': 'No data array provided'}), 400

    imported = 0
    errors = []

    # Column name mapping (normalized to lowercase, stripped)
    column_map = {
        'subcategory_code': 'subcategory_code',
        'subcategory code': 'subcategory_code',
        'code': 'subcategory_code',
        'prior_year_score': 'prior_year_score',
        'prior year score': 'prior_year_score',
        'prior_year': 'prior_year_score',
        'prior year': 'prior_year_score',
        'current_score': 'current_score',
        'current score': 'current_score',
        'current': 'current_score',
        'current_year_goal': 'current_year_goal',
        'current year goal': 'current_year_goal',
        'current year goal': 'current_year_goal',
        'current_goal': 'current_year_goal',
        'next_year_goal': 'next_year_goal',
        'next year goal': 'next_year_goal',
        'next year': 'next_year_goal',
        'next_goal': 'next_year_goal',
        'notes': 'notes',
        'note': 'notes',
        'project_improvements': 'project_improvements',
        'project improvements': 'project_improvements',
        'project': 'project_improvements',
        'improvements': 'project_improvements',
        'score_impact': 'score_impact',
        'score impact': 'score_impact',
        'impact': 'score_impact'
    }

    for item in data['data']:
        # Normalize keys
        normalized_item = {}
        for key, value in item.items():
            normalized_key = key.lower().strip().replace('_', ' ')
            if normalized_key in column_map:
                field_name = column_map[normalized_key]
                normalized_item[field_name] = value

        code = normalized_item.get('subcategory_code')
        if not code:
            continue

        subcategory = db.execute(
            'SELECT id FROM subcategories WHERE code = ?', (code,)
        ).fetchone()

        if not subcategory:
            errors.append({'code': code, 'error': 'Subcategory not found'})
            continue

        # Update scores
        fields = ['prior_year_score', 'current_score', 'current_year_goal',
                  'next_year_goal', 'notes', 'project_improvements', 'score_impact']

        updates = []
        params = []

        for field in fields:
            if field in normalized_item and normalized_item[field] is not None:
                updates.append(f'{field} = ?')
                # Convert numeric strings to floats for score fields
                if field in ['prior_year_score', 'current_score', 'current_year_goal', 'next_year_goal']:
                    try:
                        params.append(float(normalized_item[field]) if normalized_item[field] else None)
                    except (ValueError, TypeError):
                        params.append(None)
                else:
                    params.append(normalized_item[field])

        if updates:
            updates.append('last_updated = CURRENT_TIMESTAMP')
            params.append(subcategory['id'])
            db.execute(
                f"UPDATE scores SET {', '.join(updates)} WHERE subcategory_id = ?",
                params
            )
            imported += 1

    db.commit()

    return jsonify({
        'success': True,
        'imported': imported,
        'errors': errors if errors else None
    })


# ============================================================================
# API ENDPOINTS - SETTINGS
# ============================================================================

@app.route('/api/settings', methods=['GET'])
def api_get_settings():
    """Get application settings."""
    db = get_db()

    results = db.execute('SELECT key, value FROM settings').fetchall()

    return jsonify({row['key']: row['value'] for row in results})


@app.route('/api/settings', methods=['PUT'])
def api_update_settings():
    """
    Update application settings.

    Request Body (JSON):
        {
            "prior_year": "2024",
            "current_year": "2025"
        }
    """
    db = get_db()
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    for key, value in data.items():
        db.execute('''
            INSERT OR REPLACE INTO settings (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        ''', (key, str(value)))

    db.commit()

    return jsonify({'success': True, 'updated': list(data.keys())})


# ============================================================================
# API ENDPOINTS - AUDIT LOG
# ============================================================================

@app.route('/api/audit-log', methods=['GET'])
def api_get_audit_log():
    """
    Get override audit log entries.

    Query Parameters:
        subcategory_code: Filter by subcategory code
        limit: Maximum number of entries (default 100)
    """
    db = get_db()

    subcategory_code = request.args.get('subcategory_code')
    limit = request.args.get('limit', 100)

    query = '''
        SELECT
            ol.*,
            s.code as subcategory_code
        FROM override_log ol
        JOIN subcategories s ON ol.subcategory_id = s.id
    '''

    if subcategory_code:
        query += ' WHERE s.code = ?'
        results = db.execute(query + ' ORDER BY ol.timestamp DESC LIMIT ?',
                            (subcategory_code, limit)).fetchall()
    else:
        results = db.execute(query + ' ORDER BY ol.timestamp DESC LIMIT ?',
                            (limit,)).fetchall()

    return jsonify([dict(r) for r in results])


if __name__ == '__main__':
    app.run(debug=True, port=5001)
