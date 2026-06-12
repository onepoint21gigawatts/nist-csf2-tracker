# NIST CSF 2.0 Tracker

A web-based application for tracking and managing NIST Cybersecurity Framework (CSF) 2.0 maturity scores across your organization.

## Overview

This application helps organizations assess, track, and visualize their cybersecurity maturity across all six NIST CSF 2.0 functions:

- **GV** - Govern
- **ID** - Identify
- **PR** - Protect
- **DE** - Detect
- **RS** - Respond
- **RC** - Recover

### Features

- **Interactive Dashboard** - Visual overview of maturity scores with charts and statistics
- **Modern Dark Mode UI** - Beautiful glassmorphism design with smooth transitions
- **Score Tracking** - Track prior year, current, and goal scores for each subcategory
- **Category Detail Views** - Drill down into specific functions and categories
- **REST API** - Full API for programmatic access and integration
- **Data Import/Export** - Import scores from JSON or export for backup/reporting
- **Audit Logging** - Track changes to locked prior year scores
- **Score Locking** - Lock prior year scores to prevent accidental changes
- **Security Hardened** - Environment-based secret keys, no hardcoded credentials

## Screenshots

The dashboard displays:
- Overall maturity score averages
- Score breakdown by CSF function
- Comparison charts showing progress and goals
- Detailed subcategory views with notes and improvement tracking

## Requirements

- Python 3.8+
- Flask
- Flask-Compress

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/onepoint21gigawatts/nist-csf-tracker.git
cd nist-csf-tracker
```

### 2. Run the Startup Script

The easiest way to start the application:

```bash
./run.sh
```

This script will:
- Create a Python virtual environment (if not exists)
- Install required dependencies
- Start the web server

### 3. Access the Application

Open your browser and navigate to:

```
http://localhost:5001
```

## Manual Installation

If you prefer to set up manually:

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install flask flask-compress

# Run the application
python app.py
```

## Project Structure

```
nist-csf-tracker/
├── app.py                 # Main Flask application
├── run.sh                 # Startup script
├── show_summary.py        # CLI summary utility
├── API.md                 # API documentation
├── data/
│   ├── nist_csf.db        # SQLite database
│   ├── nist_csf_core.csv  # NIST CSF 2.0 framework data
│   ├── init_db.py         # Database initialization
│   ├── import_excel.py    # Excel import utility
│   └── import_scores.py   # Score import utility
├── templates/
│   ├── index.html         # Dashboard page
│   └── function_detail.html # Detail view
└── static/
    └── css/
        └── styles.css     # Application styles
```

## Usage

### Web Interface

1. **Dashboard** (`/`) - View overall maturity scores and charts
2. **Function Details** (`/function/<code>`) - View all subcategories within a function

### Command Line

View a summary of scores in the terminal:

```bash
source venv/bin/activate
python show_summary.py
```

### API Endpoints

The application provides a full REST API for programmatic access:

#### Scores

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/scores` | Get all scores |
| GET | `/api/scores/{code}` | Get score for a subcategory |
| PUT | `/api/scores/{code}` | Update a subcategory score |
| PUT | `/api/scores/bulk` | Bulk update scores |
| POST | `/api/scores/{code}/lock` | Lock/unlock prior year score |

#### Statistics

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/averages` | Get average scores by function/category |
| GET | `/api/chart-data` | Get data formatted for charts |

#### Framework Structure

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/functions` | Get all CSF functions |
| GET | `/api/categories` | Get all categories |
| GET | `/api/subcategories` | Get all subcategories |

#### Data Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/export` | Export all data as JSON |
| POST | `/api/import` | Import scores from JSON |
| GET | `/api/settings` | Get application settings |
| PUT | `/api/settings` | Update settings |
| GET | `/api/audit-log` | Get override audit log |

For detailed API documentation, see [API.md](API.md).

## Scoring Guide

Maturity is measured on a 0-5 scale:

| Score Range | Level | Description |
|-------------|-------|-------------|
| 0.0 - 1.0 | Initial | Ad-hoc, no formal process |
| 1.1 - 2.0 | Developing | Process is being developed |
| 2.1 - 3.0 | Defined | Process is documented and established |
| 3.1 - 4.0 | Managed | Process is measured and controlled |
| 4.1 - 5.0 | Optimized | Continuous improvement is in place |

## Data Import

### From Excel

Use the `import_excel.py` script to import scores from an Excel file:

```bash
python data/import_excel.py your_scores.xlsx
```

### From JSON

Use the API to import JSON data:

```bash
curl -X POST http://localhost:5001/api/import \
  -H "Content-Type: application/json" \
  -d '{"data": [{"subcategory_code": "GV.OC-01", "current_score": 3.0}]}'
```

## Database

The application uses SQLite for data storage. The database is located at `data/nist_csf.db` and includes:

- **functions** - CSF 2.0 functions (GV, ID, PR, DE, RS, RC)
- **categories** - Categories within each function
- **subcategories** - Subcategories with descriptions and examples
- **scores** - Maturity scores and notes for each subcategory
- **settings** - Application configuration
- **override_log** - Audit trail for locked score changes

To reinitialize the database:

```bash
python data/init_db.py
```

## Customization

### Year Settings

Update the current and prior year labels via API:

```bash
curl -X PUT http://localhost:5001/api/settings \
  -H "Content-Type: application/json" \
  -d '{"prior_year": "2024", "current_year": "2025"}'
```

### Styling

The application uses a custom color scheme. Colors are defined in `app.py`:

```python
YEAR_COLORS = {
    'prior_year': '#ECEEF2',      # Light gray
    'current_score': '#2D36EC',   # Blue
    'current_year_goal': '#FE572A', # Orange/red
    'next_year_goal': '#DAFF02'   # Lime green
}
```

Modify `static/css/styles.css` for additional styling changes.

## Development

### Running in Debug Mode

The application runs in debug mode by default, which enables:
- Auto-reload on code changes
- Detailed error messages
- Flask debugger

### Adding New Features

1. Extend `app.py` for new routes and API endpoints
2. Add templates in `templates/`
3. Add static assets in `static/`
4. Update `API.md` for new API endpoints

## Security Considerations

- The application uses a hardcoded secret key for sessions. **Change this in production.**
- No authentication is implemented. Add authentication before exposing publicly.
- The database has no encryption. Consider encryption for sensitive data.
- Prior year scores can be locked to prevent accidental changes.

## Security

### Best Practices

- **Secret Keys**: The application uses environment-based secret keys for session management. Never commit hardcoded secret keys to version control.
  ```bash
  # Recommended: Set a secure secret key
  export SECRET_KEY="your-secure-random-string-here"
  ```

- **Production Deployment**: For production use:
  1. Always set a strong `SECRET_KEY` environment variable
  2. Use HTTPS
  3. Enable proper authentication/authorization
  4. Use a production-grade WSGI server (gunicorn, uWSGI)
  5. Set appropriate database permissions

- **Data Privacy**: The database may contain sensitive organizational data. Ensure proper access controls and encryption at rest for production deployments.

### Security Features

- Default secret key generation using cryptographically secure random values
- No hardcoded passwords or API keys
- Environment variable based configuration
- .gitignore prevents accidental commit of sensitive files

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit changes (`git commit -am 'Add my feature'`)
4. Push to the branch (`git push origin feature/my-feature`)
5. Create a Pull Request

## License

This project is provided as-is for educational and internal business use.

## References

- [NIST Cybersecurity Framework 2.0](https://www.nist.gov/cyberframework)
- [NIST CSF 2.0 Reference](https://csrc.nist.gov/pubs/csfp/20/final)

## Support

For issues or feature requests, please use the [GitHub Issues](https://github.com/onepoint21gigawatts/nist-csf-tracker/issues) page.
