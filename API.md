# API Documentation

## Overview

The Google Dorking Tool API provides endpoints for starting scans, monitoring progress, and exporting results.

**Base URL**: `http://localhost:5000/api`

## Authentication

Currently, the API does not require authentication. For production, implement authentication tokens or API keys.

## Endpoints

### 1. Get Available Categories

**Endpoint**: `GET /api/categories`

**Description**: Get all available dorking query categories

**Response**:
```json
{
  "status": "success",
  "categories": [
    "subdomain_enumeration",
    "exposed_ftp",
    "exposed_documents",
    ...
  ],
  "total_queries": 256,
  "per_category": {
    "subdomain_enumeration": 3,
    "exposed_ftp": 6,
    ...
  }
}
```

---

### 2. Start a Scan

**Endpoint**: `POST /api/start-scan`

**Description**: Start a new dorking scan for a domain

**Request Body**:
```json
{
  "domain": "example.com",
  "categories": ["wordpress", "phpmyadmin"]  // Optional, null for all
}
```

**Response** (HTTP 202):
```json
{
  "status": "started",
  "task_id": "abc123def456xyz",
  "message": "Dorking scan started for example.com",
  "domain": "example.com",
  "categories": ["wordpress", "phpmyadmin"]
}
```

**Error Response** (HTTP 400):
```json
{
  "status": "error",
  "message": "Domain is required"
}
```

---

### 3. Check Scan Status

**Endpoint**: `GET /api/scan-status/<task_id>`

**Description**: Get current progress and status of a scan

**Query Parameters**: None

**Response**:
```json
{
  "task_id": "abc123def456xyz",
  "status": "PROGRESS",
  "progress": 45,
  "total": 256,
  "message": "Scanning category: wordpress",
  "current_query": "site:example.com inurl:/wp-admin/"
}
```

**Status Values**:
- `PENDING` - Task is waiting to be processed
- `PROGRESS` - Task is currently executing
- `SUCCESS` - Task completed successfully
- `FAILURE` - Task failed

---

### 4. Get Scan Results

**Endpoint**: `GET /api/scan-results/<task_id>`

**Description**: Get full results of a completed scan

**Response** (HTTP 200):
```json
{
  "status": "success",
  "results": {
    "domain": "example.com",
    "scan_date": "2024-05-28T10:30:00.123456",
    "total_queries": 256,
    "categories_scanned": ["wordpress", "phpmyadmin"],
    "results_by_category": {
      "wordpress": [
        {
          "status": "success",
          "query": "site:example.com inurl:/wp-admin/",
          "url": "https://www.google.com/search?q=site:example.com inurl:/wp-admin/",
          "results": [
            {
              "title": "WordPress Admin Login",
              "url": "https://example.com/wp-admin/",
              "description": "Secure login area"
            }
          ]
        }
      ],
      "phpmyadmin": [...]
    },
    "statistics": {
      "total_queries": 256,
      "successful_queries": 245,
      "failed_queries": 11,
      "success_rate": 95.7
    }
  }
}
```

---

### 5. Export Scan Results

**Endpoint**: `GET /api/export-results/<task_id>`

**Description**: Export scan results in different formats

**Query Parameters**:
- `format` (string): `json` or `csv` (default: `json`)

**Response**:
- Returns file download with appropriate MIME type
- Filename format: `dorking_results_{domain}_{timestamp}.{ext}`

**Example**:
```bash
curl http://localhost:5000/api/export-results/abc123def456xyz?format=json \
  -o results.json

curl http://localhost:5000/api/export-results/abc123def456xyz?format=csv \
  -o results.csv
```

---

### 6. Health Check

**Endpoint**: `GET /api/health`

**Description**: Check API health status

**Response**:
```json
{
  "status": "healthy",
  "service": "Google Dorking Tool",
  "timestamp": "2024-05-28T10:30:00.123456"
}
```

---

### 7. Test Celery Connection

**Endpoint**: `GET /api/test-connection`

**Description**: Test if Celery background task queue is working

**Response**:
```json
{
  "status": "ok",
  "message": "Celery connection successful",
  "task_id": "xyz789abc456"
}
```

---

## Error Handling

All error responses follow this format:

```json
{
  "status": "error",
  "message": "Human-readable error message"
}
```

**Common HTTP Status Codes**:
- `200 OK` - Successful request
- `202 Accepted` - Scan started (async operation)
- `400 Bad Request` - Invalid input parameters
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error

---

## Rate Limiting

Currently no rate limiting is implemented, but it's recommended for production:

```python
# Add to config.py for production
RATELIMIT_ENABLED = True
RATELIMIT_STORAGE_URL = "redis://localhost:6379/1"
```

---

## Authentication (Production)

Implement JWT or API key authentication:

```bash
# Add Authorization header
curl -H "Authorization: Bearer YOUR_API_KEY" \
  http://localhost:5000/api/categories
```

---

## Examples

### Complete Workflow Example

```bash
#!/bin/bash

# 1. Get available categories
CATEGORIES=$(curl -s http://localhost:5000/api/categories | jq '.categories')
echo "Available categories: $CATEGORIES"

# 2. Start a scan
RESPONSE=$(curl -s -X POST http://localhost:5000/api/start-scan \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "example.com",
    "categories": ["wordpress", "phpmyadmin"]
  }')

TASK_ID=$(echo $RESPONSE | jq -r '.task_id')
echo "Started scan with task ID: $TASK_ID"

# 3. Monitor progress
while true; do
  STATUS=$(curl -s http://localhost:5000/api/scan-status/$TASK_ID)
  STATE=$(echo $STATUS | jq -r '.status')
  
  if [ "$STATE" == "SUCCESS" ]; then
    echo "Scan completed!"
    break
  elif [ "$STATE" == "FAILURE" ]; then
    echo "Scan failed!"
    exit 1
  else
    PROGRESS=$(echo $STATUS | jq -r '.progress // 0')
    TOTAL=$(echo $STATUS | jq -r '.total // 0')
    echo "Progress: $PROGRESS/$TOTAL"
  fi
  
  sleep 5
done

# 4. Export results
curl http://localhost:5000/api/export-results/$TASK_ID?format=json \
  -o results.json

echo "Results exported to results.json"
```

---

## Batch Operations

```python
import requests
import time
import json

API_BASE = "http://localhost:5000/api"
DOMAINS = ["example.com", "test.com", "sample.org"]
RESULTS = {}

# Start scans for all domains
for domain in DOMAINS:
    response = requests.post(
        f"{API_BASE}/start-scan",
        json={"domain": domain}
    )
    task_id = response.json()["task_id"]
    RESULTS[domain] = task_id
    print(f"Started scan for {domain}: {task_id}")

# Monitor all scans
completed = set()
while len(completed) < len(DOMAINS):
    for domain, task_id in RESULTS.items():
        if domain in completed:
            continue
        
        response = requests.get(f"{API_BASE}/scan-status/{task_id}")
        data = response.json()
        
        if data["status"] == "SUCCESS":
            completed.add(domain)
            print(f"✓ {domain} completed")
        elif data["status"] == "FAILURE":
            completed.add(domain)
            print(f"✗ {domain} failed")
        else:
            progress = data.get("progress", 0)
            total = data.get("total", 0)
            print(f"  {domain}: {progress}/{total}")
    
    time.sleep(5)

print("All scans completed!")
```

---

## Performance Tips

1. **Pagination**: For large result sets, implement pagination
2. **Caching**: Cache category list with Redis
3. **Timeout**: Set reasonable request timeouts
4. **Connection Pooling**: Use requests.Session() for multiple calls
5. **Compression**: Enable gzip compression for responses

---

## Webhook Integration

To receive notifications when scans complete, you can implement webhooks:

```json
POST /api/start-scan
{
  "domain": "example.com",
  "categories": ["wordpress"],
  "webhook_url": "https://yourserver.com/callback"
}
```

The tool would then POST the results to your webhook when complete.

---

## Version

Current API Version: **1.0**

Last Updated: May 28, 2024
