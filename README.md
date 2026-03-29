# Online Web Crawler

A Flask web application that monitors the online status of people by scraping a target website. Provides a web interface to manage a list of usernames with descriptions and track when they were last seen online.

## Features

- ✅ **Web UI** – Manage people (add/remove) with descriptions
- ✅ **Batch Monitoring** – Trigger background checks to see who's online
- ✅ **Last Seen Tracking** – Records timestamp when each person was last found online
- ✅ **Thread-Safe** – Handles concurrent add/remove requests safely
- ✅ **JSON Storage** – People stored as JSON with extensible fields
- ✅ **Docker Ready** – Pre-configured for containerized deployment
- ✅ **Atomic Writes** – Prevents data corruption even during crashes

## Quick Start

### Local Development

**Prerequisites:**
- Python 3.8+
- `pip` (comes with Python)

**Setup:**
```bash
cd /Users/lee/PycharmProjects/new_web

# Create virtual environment (if not exists)
python3 -m venv .venv

# Activate it
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

**Run:**
```bash
python3 app.py
```

Visit `http://localhost:5000` in your browser.

### Docker Deployment

**One command:**
```bash
bash docker.sh
```

This:
1. Stops/removes old "web_crawler" container
2. Builds fresh image
3. Runs on `http://localhost:5001`

**Manual Docker:**
```bash
docker build --tag web_crawler .
docker run -d -p 5001:5001 --name web_crawler web_crawler:latest
```

## Usage

### Web Interface

**Left Column – Manage People:**
1. Enter name (required) and optional description
2. Click "Add" to add a person
3. Enter a name in "Remove" field and click to remove

**Right Column – Check Status:**
1. Click "Start Check" button
2. App monitors all people for online status
3. Results appear when complete
4. Timestamp shows when check ran

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Render web UI with current list and results |
| `/add` | POST | Add person (form data: `add_item`, `description`) |
| `/remove` | POST | Remove person (form data: `remove_item`) |
| `/start_task` | POST | Start background monitoring task |
| `/task_status` | GET | Poll task status and results (JSON) |

**Example – Add person via curl:**
```bash
curl -X POST http://localhost:5000/add \
  -d "add_item=testuser" \
  -d "description=A test user"
```

**Example – Check task status:**
```bash
curl http://localhost:5000/task_status
```

Response:
```json
{
  "running": false,
  "results": [
    "https://example.com/testuser/",
    "Last run at 14:32:45"
  ]
}
```

## Data Format

### people.py (JSON)

Each person is an object with:
- `name` – username/identifier (required)
- `description` – custom notes/metadata (optional, string)
- `last_seen` – ISO timestamp when last found online (null if never seen)

**Example:**
```json
[
  {
    "name": "john_doe",
    "description": "Friend from school",
    "last_seen": "2026-03-29T14:32:45+01:00"
  },
  {
    "name": "jane_smith",
    "description": "Work colleague",
    "last_seen": null
  }
]
```

## Configuration

### config.py

Edit to change:
- `headers` – User-Agent string for HTTP requests
- `base_url` – Target website URL template (uses `{person}` placeholder)

**Example:**
```python
headers = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
base_url = 'https://example.com/{}/'
```

## Project Structure

```
.
├── app.py                 # Flask application (routes, logic)
├── config.py              # Configuration (headers, base URL)
├── people.py              # JSON data file
├── requirements.txt       # Python dependencies
├── Dockerfile             # Docker image definition
├── docker.sh              # Docker build & run script
├── DEPLOYMENT.md          # Deployment guide (local, Docker, production)
├── test_concurrency.py    # Concurrency stress tests
├── .github/
│   └── copilot-instructions.md  # AI assistant instructions
├── templates/
│   └── index.html         # Web UI template
└── static/
    ├── script.js          # Frontend JavaScript (events, polling)
    └── style.css          # Frontend styling
```

## Development

### Running Tests

**Concurrency test** (while app is running):
```bash
# Terminal 1
python3 app.py

# Terminal 2
python3 test_concurrency.py
```

Tests concurrent add/remove operations to verify thread-safety.

### Debugging

**Enable verbose logging:**
The app logs at DEBUG level by default. Check terminal output for:
- Item add/remove events
- Task start/completion
- HTTP request errors
- File I/O issues

**Check app logs:** 
```bash
# If running in Docker
docker logs -f web_crawler
```

### Code Style

- **Python**: Use `logging` module, context managers for file I/O, `jsonify()` for JSON responses
- **JavaScript**: Vanilla JS (no frameworks), Fetch API for requests
- **Threading**: Always use `global` keyword when modifying shared state

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` |
| `Address already in use` on port 5000 | Change Flask port in `app.py` or kill process: `lsof -i :5000 \| awk 'NR==2 {print $2}' \| xargs kill -9` |
| `people.py` not found | Create: `touch people.py` and add: `[]` |
| Docker container exits | Run `docker logs web_crawler` to see error |
| Data corruption after crash | Already handled! Uses atomic writes |
| Concurrent requests cause data loss | Already fixed! Uses file locking |

## Known Limitations

1. **File-based storage** – Not suitable for distributed systems (use database for scaling)
2. **In-memory results** – Task results lost on restart (use Redis/queue for persistence)
3. **Single-threaded requests** – Consider connection pooling for many concurrent adds/removes
4. **No authentication** – Don't expose to internet without adding auth layer

## Next Steps

- [✓] **Local Setup** – Run `python3 app.py`
- [✓] **Add People** – Use web UI or API
- [✓] **Run Checks** – Click "Start Check" button
- [⚠️] **Production Deploy** – See `DEPLOYMENT.md` for production setup
- [⚠️] **Scale** – Consider database (PostgreSQL/MongoDB) for data storage

## Production Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for:
- Environment variables
- Health checks
- Logging to file
- Data backups
- Reverse proxy setup (nginx)
- Rolling updates & rollback
- Monitoring & maintenance

## Dependencies

See [requirements.txt](requirements.txt):
- `Flask` – Web framework
- `requests` – HTTP client
- `pytz` – Timezone support
- `Flask-Cors` – CORS handling

## License

MIT

## Support

For issues or questions:
1. Check [DEPLOYMENT.md](DEPLOYMENT.md) for production issues
2. Check troubleshooting table above
3. Review logs: `docker logs web_crawler`
4. Run concurrency tests: `python3 test_concurrency.py`
