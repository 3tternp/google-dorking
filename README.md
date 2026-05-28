# Google Dorking Security Tool

A comprehensive web-based Python application for automated Google dorking (security reconnaissance) that takes a domain or URL from the user and executes reconnaissance queries in the background.

## Features

✨ **Key Capabilities:**
- Web-based user interface with real-time progress tracking
- 200+ pre-built dorking queries organized by category
- Background task execution using Celery and Redis
- Real-time scan progress monitoring
- Export results in JSON and CSV formats
- Support for custom category selection
- Mobile-responsive design
- Comprehensive documentation and help guides

## Supported Scanning Categories

1. **Subdomain Enumeration** - Find subdomains of target domain
2. **Exposed FTP** - Discover publicly accessible FTP services
3. **Exposed Documents** - PDF, Word, Excel, and other files
4. **Exposed Git** - Git repositories and configuration files
5. **Directory Listings** - Exposed directories and sensitive files
6. **Code Leaks** - Code found on external sharing platforms
7. **Cloud Storage** - Exposed S3 buckets, Azure blobs, etc.
8. **API Documentation** - API endpoints and documentation
9. **Web Servers** - Apache, Nginx, and other server types
10. **CMS Detection** - WordPress, Drupal, Joomla, Magento, etc.
11. **Configuration Files** - Database configs, secrets, etc.
12. **Vulnerable Parameters** - XSS, SQLI, SSRF, LFI, RCE parameters
13. **And many more...**

## Technology Stack

- **Backend**: Python Flask
- **Frontend**: HTML5, CSS3, Bootstrap 5, JavaScript
- **Background Tasks**: Celery + Redis
- **Search Engine**: Google Custom Search API (Selenium for parsing)
- **Database**: Redis (for task queues and caching)

## Prerequisites

- Python 3.8+
- Redis server
- pip or poetry for package management
- Google Chrome/Chromium (for Selenium, optional)

## Installation & Setup

### 1. Clone/Download the Project

```bash
cd /home/prem/google-dorking
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your configuration
nano .env  # or use your preferred editor
```

**Important environment variables:**
```
FLASK_DEBUG=True
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
SECRET_KEY=your-secret-key
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### 5. Install and Start Redis

```bash
# On Ubuntu/Debian:
sudo apt-get install redis-server
sudo service redis-server start

# On macOS:
brew install redis
brew services start redis

# Or run Redis in Docker:
docker run -d -p 6379:6379 redis:latest
```

### 6. Start the Application

**Terminal 1 - Flask Development Server:**
```bash
python run.py
```

The application will start at `http://localhost:5000`

**Terminal 2 - Celery Worker (for background tasks):**
```bash
python worker.py
```

Or start it with more verbosity:
```bash
celery -A app.tasks worker --loglevel=info
```

## Usage

### Via Web Interface

1. **Open the Application**: Navigate to `http://localhost:5000` in your browser
2. **Enter Target Domain**: Input the domain you want to scan (e.g., `example.com`, `site.example.co.uk`)
3. **Select Categories** (Optional): Choose specific scanning categories or leave blank for all
4. **Start Scan**: Click "Start Scan" button
5. **Monitor Progress**: Watch real-time progress as queries execute
6. **View Results**: Review categorized results with success rates
7. **Export Results**: Download results as JSON or CSV

### Via API

#### Start a Scan
```bash
curl -X POST http://localhost:5000/api/start-scan \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "example.com",
    "categories": ["wordpress", "phpmyadmin"]
  }'

# Response:
# {
#   "status": "started",
#   "task_id": "abc123def456",
#   "message": "Dorking scan started for example.com"
# }
```

#### Check Scan Status
```bash
curl http://localhost:5000/api/scan-status/abc123def456

# Response shows progress, current query, and final results
```

#### Get Full Results
```bash
curl http://localhost:5000/api/scan-results/abc123def456
```

#### Export Results
```bash
# JSON format
curl http://localhost:5000/api/export-results/abc123def456?format=json

# CSV format
curl http://localhost:5000/api/export-results/abc123def456?format=csv
```

#### Health Check
```bash
curl http://localhost:5000/api/health
```

## Project Structure

```
google-dorking/
├── app/
│   ├── __init__.py              # Flask app factory
│   ├── dorking_queries.py       # Dorking queries database
│   ├── search_engine.py         # Google search implementation
│   ├── tasks.py                 # Celery background tasks
│   ├── routes.py                # Flask routes and API endpoints
│   ├── templates/
│   │   ├── index.html           # Main page
│   │   ├── results.html         # Results viewing page
│   │   └── help.html            # Help and documentation
│   └── static/
│       ├── css/
│       │   └── style.css        # Custom styles
│       └── js/
│           └── main.js          # JavaScript utilities
├── run.py                       # Flask development server entry point
├── worker.py                    # Celery worker entry point
├── config.py                    # Configuration management
├── requirements.txt             # Python dependencies
├── .env.example                 # Example environment variables
└── README.md                    # This file
```

## Configuration Details

### Adjusting Scan Parameters

Edit `app/search_engine.py` to modify:
- `delay`: Time between requests (default: 1.5 seconds)
- `max_results`: Maximum results per query (default: 10)

### Adding Custom Dorking Queries

Edit `app/dorking_queries.py` to add new categories:

```python
DORKING_QUERIES = {
    "my_category": [
        'site:{domain} custom query 1',
        'site:{domain} custom query 2',
    ],
    # ... more categories
}
```

### Enabling Google Custom Search API

1. Get API credentials from Google Cloud Console
2. Add to `.env`:
   ```
   GOOGLE_API_KEY=your-api-key
   GOOGLE_SEARCH_ENGINE_ID=your-search-engine-id
   ```
3. Update `search_engine.py` to use the API instead of web scraping

## Important Security Notes

⚠️ **This tool is for authorized security testing only!**

- **Authorization**: Always obtain proper written authorization before scanning any domain
- **Responsible Use**: Use ethically and according to all applicable laws
- **Rate Limiting**: Google may rate-limit your searches
- **Robot.txt**: Respect website owner's robots.txt policies
- **Terms of Service**: Comply with Google's Terms of Service
- **Legal Implications**: Unauthorized access to systems is illegal
- **Privacy**: Respect user privacy and data protection laws (GDPR, CCPA, etc.)

## Troubleshooting

### Redis Connection Error
```
Error: Connection refused
```
**Solution**: Ensure Redis is running
```bash
redis-cli ping  # Should return "PONG"
```

### Celery Worker Not Processing Tasks
```
Tasks stuck in PENDING state
```
**Solution**: Restart the Celery worker and check Redis connection

### Google Rate Limiting
If you see connection errors:
- Increase the `REQUEST_DELAY_SECONDS` in `.env`
- Use Google Custom Search API instead of web scraping
- Consider using a VPN or rotating IPs (advanced)

### Port Already in Use
```bash
# Find and kill process using port 5000
lsof -i :5000
kill -9 <PID>

# Or use a different port
FLASK_PORT=8000 python run.py
```

## Performance Optimization

For large-scale scanning:

1. **Increase Celery Workers**:
   ```bash
   celery -A app.tasks worker --concurrency=8
   ```

2. **Use Process Pool**:
   ```bash
   celery -A app.tasks worker --pool=prefork
   ```

3. **Redis Configuration**: Ensure Redis has sufficient memory and is optimized

## API Response Examples

### Successful Scan Completion
```json
{
  "status": "completed",
  "data": {
    "domain": "example.com",
    "scan_date": "2024-05-28T10:30:00",
    "total_queries": 256,
    "categories_scanned": ["wordpress", "phpmyadmin"],
    "results_by_category": {
      "wordpress": [
        {
          "status": "success",
          "query": "site:example.com inurl:/wp-admin/",
          "results": [...]
        }
      ]
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

## Advanced Usage

### Scheduling Regular Scans

Use cron jobs to schedule periodic scans:

```bash
# Run a scan every Monday at 2 AM
0 2 * * 1 curl -X POST http://localhost:5000/api/start-scan \
  -H "Content-Type: application/json" \
  -d '{"domain": "example.com"}'
```

### Batch Processing

Process multiple domains:

```python
import requests
import json

domains = ["example.com", "test.com", "sample.org"]
task_ids = []

for domain in domains:
    response = requests.post(
        'http://localhost:5000/api/start-scan',
        headers={'Content-Type': 'application/json'},
        data=json.dumps({'domain': domain})
    )
    task_ids.append(response.json()['task_id'])

# Monitor all tasks
for task_id in task_ids:
    # Check status with /api/scan-status/{task_id}
    pass
```

## Production Deployment

For production use:

1. **Use a Production WSGI Server**:
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 run:app
   ```

2. **Use SSL/TLS**:
   - Set up HTTPS with Let's Encrypt
   - Update `FLASK_HOST` and `FLASK_PORT`

3. **Use a Process Manager**:
   - Supervisor
   - systemd services
   - Docker containers

4. **Secure Configuration**:
   - Change `SECRET_KEY` to a strong random string
   - Use environment variables for all secrets
   - Restrict API access with authentication

5. **Monitor**:
   - Set up logging to files
   - Monitor Redis and Celery health
   - Set up alerts for failures

## Contributing

To contribute:

1. Test your changes thoroughly
2. Follow PEP 8 style guidelines
3. Add documentation for new features
4. Ensure backward compatibility

## License

This tool is provided for authorized security testing only. Users are responsible for ensuring proper authorization and legal compliance.

## Support & Documentation

- **Help & Guide**: Visit `/help` page in the web interface
- **API Documentation**: Check `/api/health` and source code
- **Common Issues**: See Troubleshooting section

## Disclaimer

This tool is intended for authorized security professionals conducting authorized penetration testing and security research. Unauthorized access to computer systems is illegal. Users of this tool are solely responsible for ensuring they have proper authorization before using it against any target. The authors assume no liability for misuse or damage caused by this tool.

---

**Stay secure and test responsibly! 🛡️**
