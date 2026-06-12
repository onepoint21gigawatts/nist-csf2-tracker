# NIST CSF 2.0 Tracker API

Base URL: `http://localhost:5001`

## Scores API

### GET /api/scores
Get all scores for all subcategories.

```bash
curl http://localhost:5001/api/scores
```

**Response:**
```json
[
  {
    "subcategory_code": "GV.OC-01",
    "prior_year_score": 2.5,
    "current_score": 3.0,
    "current_year_goal": 3.5,
    "next_year_goal": 4.0
  }
]
```

### GET /api/scores/{subcategory_code}
Get score for a specific subcategory.

```bash
curl http://localhost:5001/api/scores/GV.OC-01
```

### PUT /api/scores/{subcategory_code}
Update scores for a subcategory.

```bash
curl -X PUT http://localhost:5001/api/scores/GV.OC-01 \
  -H "Content-Type: application/json" \
  -d '{
    "prior_year_score": 2.5,
    "current_score": 3.0,
    "current_year_goal": 3.5,
    "next_year_goal": 4.0,
    "notes": "Optional notes",
    "override_reason": "Required if prior_year_score is locked"
  }'
```

### PUT /api/scores/bulk
Bulk update multiple subcategories.

```bash
curl -X PUT http://localhost:5001/api/scores/bulk \
  -H "Content-Type: application/json" \
  -d '{
    "updates": [
      {"subcategory_code": "GV.OC-01", "current_score": 3.0},
      {"subcategory_code": "GV.OC-02", "current_score": 2.5}
    ]
  }'
```

### POST /api/scores/{subcategory_code}/lock
Lock/unlock prior year score.

```bash
# Lock
curl -X POST http://localhost:5001/api/scores/GV.OC-01/lock \
  -H "Content-Type: application/json" \
  -d '{"locked": true, "reason": "Year end finalized"}'

# Unlock
curl -X POST http://localhost:5001/api/scores/GV.OC-01/lock \
  -H "Content-Type: application/json" \
  -d '{"locked": false}'
```

## Averages API

### GET /api/averages
Get average scores by function and category.

**Query Parameters:**
- `function` - Filter by function code (optional)
- `category` - Filter by category code (optional)

```bash
curl http://localhost:5001/api/averages
curl "http://localhost:5001/api/averages?function=GV"
```

### GET /api/chart-data
Get data formatted for chart rendering.

```bash
curl http://localhost:5001/api/chart-data
```

## Framework Structure API

### GET /api/functions
Get all NIST CSF functions (GV, ID, PR, DE, RS, RC).

```bash
curl http://localhost:5001/api/functions
```

### GET /api/categories
Get all categories.

**Query Parameters:**
- `function` - Filter by function code

```bash
curl http://localhost:5001/api/categories
curl "http://localhost:5001/api/categories?function=GV"
```

### GET /api/subcategories
Get all subcategories.

**Query Parameters:**
- `function` - Filter by function code
- `category` - Filter by category code

```bash
curl http://localhost:5001/api/subcategories
curl "http://localhost:5001/api/subcategories?function=GV&category=GV.OC"
```

## Import/Export API

### GET /api/export
Export all data as JSON.

```bash
curl http://localhost:5001/api/export > nist_csf_export.json
```

**Response:**
```json
{
  "exported_at": "2024-06-12T10:00:00",
  "total_records": 106,
  "data": [
    {
      "subcategory_code": "GV.OC-01",
      "function_code": "GV",
      "function_name": "Govern",
      "category_code": "GV.OC",
      "category_name": "Organizational Context",
      "description": "...",
      "prior_year_score": 2.5,
      "current_score": 3.0,
      "current_year_goal": 3.5,
      "next_year_goal": 4.0,
      "notes": ""
    }
  ]
}
```

### GET /api/export/csv
Export all scores as CSV file.

```bash
curl http://localhost:5001/api/export/csv -o nist_csf_scores.csv
```

**CSV Format:**
```csv
subcategory_code,function_code,function_name,category_code,category_name,description,prior_year_score,current_score,current_year_goal,next_year_goal,notes,project_improvements,score_impact
GV.OC-01,GV,Govern,GV.OC,Organizational Context,...,2.5,3.0,3.5,4.0,Notes here,,
```

### GET /api/export/excel
Export all scores as Excel-compatible CSV (with BOM for proper encoding).

```bash
curl http://localhost:5001/api/export/excel -o nist_csf_scores_excel.csv
```

This format:
- Includes UTF-8 BOM for Excel compatibility
- Uses user-friendly column headers with year labels
- Can be opened directly in Excel without import wizard

### POST /api/import
Import scores from JSON.

```bash
curl -X POST http://localhost:5001/api/import \
  -H "Content-Type: application/json" \
  -d '{
    "data": [
      {
        "subcategory_code": "GV.OC-01",
        "prior_year_score": 2.5,
        "current_score": 3.0,
        "current_year_goal": 3.5,
        "next_year_goal": 4.0,
        "notes": "Optional notes"
      }
    ]
  }'
```

**Response:**
```json
{
  "success": true,
  "imported": 1,
  "errors": null
}
```

### POST /api/import/csv
Import scores from CSV-formatted JSON data.

```bash
curl -X POST http://localhost:5001/api/import/csv \
  -H "Content-Type: application/json" \
  -d '{
    "data": [
      {
        "subcategory_code": "GV.OC-01",
        "Prior Year Score": 2.5,
        "Current Score": 3.0,
        "Current Year Goal": 3.5,
        "Next Year Goal": 4.0
      }
    ]
  }'
```

**Flexible Column Names:**
The CSV import accepts various column name formats:
- `subcategory_code`, `Subcategory Code`, `Code`
- `prior_year_score`, `Prior Year Score`, `Prior Year`
- `current_score`, `Current Score`, `Current`
- `current_year_goal`, `Current Year Goal`, `Current Goal`
- `next_year_goal`, `Next Year Goal`, `Next Year`
- `notes`, `Notes`, `Note`

## Settings API

### GET /api/settings
Get application settings.

```bash
curl http://localhost:5001/api/settings
```

### PUT /api/settings
Update settings.

```bash
curl -X PUT http://localhost:5001/api/settings \
  -H "Content-Type: application/json" \
  -d '{"prior_year": "2024", "current_year": "2025"}'
```

## Audit API

### GET /api/audit-log
Get override audit log entries.

**Query Parameters:**
- `subcategory_code` - Filter by subcategory
- `limit` - Max entries (default: 100)

```bash
curl http://localhost:5001/api/audit-log
curl "http://localhost:5001/api/audit-log?subcategory_code=GV.OC-02"
```

## Theme Support

The application supports three color themes:
- **default** - Sonatype brand colors (default)
- **light** - Light mode with high contrast
- **dark** - Dark mode for reduced eye strain

Theme preference is stored in browser localStorage and persists across sessions.

## Example Workflows

### Export scores for backup
```bash
# Export as JSON (full data)
curl http://localhost:5001/api/export | jq '.' > backup_$(date +%Y%m%d).json

# Export as CSV (for backup or Excel)
curl http://localhost:5001/api/export/csv -o backup_$(date +%Y%m%d).csv
```

### Bulk update scores from CSV
```python
import csv
import json
import requests

# Read CSV file
with open('updated_scores.csv', 'r') as f:
    reader = csv.DictReader(f)
    data = {'data': list(reader)}

# Import to tracker
response = requests.post(
    'http://localhost:5001/api/import/csv',
    json=data
)
print(response.json())
```

### Get scores for a specific function
```bash
curl "http://localhost:5001/api/subcategories?function=GV" | jq '.[] | {code, current_score}'
```
