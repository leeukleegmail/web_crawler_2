# Deployment Guide – Online Web Crawler

## Prerequisites

- **macOS/Linux**: zsh or bash shell
- **Docker**: Version 20.10+ (includes Docker Desktop on macOS)
- **Python**: 3.8+ (for local development)
- **Port availability**: 5000 (local dev), 5001 (Docker container)

## Phase 1: Local Development

### 1.1 Environment Setup

```bash
cd /Users/lee/PycharmProjects/new_web

# Create virtual environment (if not exists)
python3 -m venv .venv

# Activate
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 1.2 Run Locally

```bash
# Start Flask development server
python app.py
```

Expected output:
```
 * Serving Flask app 'app'
 * Debug mode: off
 * Running on http://127.0.0.1:5000
```

Visit `http://localhost:5000` to test the UI.

### 1.3 Verify Core Features

- ✅ Add a person to the list (verifies write to `people.py`)
- ✅ Remove a person (verifies file updates)
- ✅ Click "Start Check" button (verifies background threading & polling)
- ✅ Check browser console for no JavaScript errors

**Common local issues:**

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: No module named 'flask'` | Run `pip install -r requirements.txt` |
| `Address already in use` on port 5000 | Change port: `python app.py` then edit app.py to use different port or kill existing process: `lsof -i :5000 \| grep LISTEN \| awk '{print $2}' \| xargs kill -9` |
| `people.py` not found | Create empty file: `touch people.py` |

---

## Phase 2: Docker Containerization

### 2.1 Pre-Docker Checklist

Before building the Docker image, ensure:

1. `requirements.txt` is up-to-date with all dependencies
2. `people.py` exists (can be empty)
3. No hardcoded absolute paths in code (use relative paths or environment variables)
4. Test locally with `python app.py` first

### 2.2 Build & Run Container

```bash
# Navigate to project root
cd /Users/lee/PycharmProjects/new_web

# Run the automated build/deploy script
bash docker.sh
```

**What docker.sh does:**
1. Stops & removes existing "web_crawler" container (if running)
2. Removes stale image
3. Builds new image with tag "web_crawler"
4. Runs container on port 5001 with:
   - Volume mount: `$(pwd)/:/$CONTAINER_NAME` (live code updates)
   - Auto-restart: `unless-stopped`
   - Background: `-d` (detached mode)

### 2.3 Verify Docker Container

```bash
# Check container status
docker ps | grep web_crawler

# View logs
docker logs -f web_crawler

# Test container
curl http://localhost:5001/
```

Expected: HTML response from index.html

### 2.4 Common Docker Issues

| Issue | Solution |
|-------|----------|
| `docker: command not found` | Install Docker Desktop for macOS |
| `port 5001 already in use` | Change port in docker.sh: `CONTAINER_PORT="5002"` and rebuild |
| `ModuleNotFoundError` in container logs | Rebuild image: `bash docker.sh` (invalidates cache) |
| Volume mount not updating code | Restart container: `docker restart web_crawler` |
| Container exits immediately | Check logs: `docker logs web_crawler` |

---

## Phase 3: Production Deployment

### 3.1 Environment Variables

Create `.env` file (never commit to git):

```bash
# .env (local reference, do NOT commit)
FLASK_ENV=production
FLASK_DEBUG=0
LOG_LEVEL=INFO
CONTAINER_PORT=5001
```

Update `docker.sh` to load variables:

```bash
#!/bin/bash
source .env || true  # Load vars, don't fail if missing

CONTAINER_NAME="${CONTAINER_NAME:-web_crawler}"
CONTAINER_PORT="${CONTAINER_PORT:-5001}"
... rest of script
```

Update `app.py` to respect environment:

```python
import os
import logging

LOG_LEVEL = os.getenv('LOG_LEVEL', 'DEBUG')
logging.basicConfig(level=getattr(logging, LOG_LEVEL))

# In production, disable debug
app.run(
    debug=os.getenv('FLASK_DEBUG', 'False') == 'True',
    host='0.0.0.0'  # Listen on all interfaces
)
```

### 3.2 Production Build

**Build for production environment:**

```bash
# Build image with metadata
docker build \
  --tag web_crawler:latest \
  --tag web_crawler:$(date +%Y%m%d_%H%M%S) \
  --build-arg container_name=web_crawler \
  .

# Run with production settings
docker run -d \
  -p 5001:5001 \
  --name web_crawler_prod \
  --restart unless-stopped \
  --env FLASK_ENV=production \
  --env FLASK_DEBUG=False \
  -v $(pwd)/people.py:/web_crawler/people.py \
  -v $(pwd)/logs/:/web_crawler/logs/ \
  --health-cmd='curl -f http://localhost:5001/ || exit 1' \
  --health-interval=30s \
  --health-timeout=10s \
  web_crawler:latest
```

### 3.3 Data Persistence

**Mount `people.py` as named volume instead of bind mount:**

```bash
# Create named volume
docker volume create web_crawler_data

# Run with volume
docker run -d \
  --name web_crawler_prod \
  -v web_crawler_data:/web_crawler/people.py \
  web_crawler:latest
```

**Or use bind mount for backups:**

```bash
# Backup before deployment
cp people.py people.py.backup.$(date +%Y%m%d_%H%M%S)

# Mount specific file
docker run -d \
  --name web_crawler_prod \
  -v $(pwd)/people.py:/web_crawler/people.py \
  web_crawler:latest
```

### 3.4 Logging & Monitoring

**Enable logging to file:**

Update `app.py`:

```python
import logging
import os

log_dir = os.getenv('LOG_DIR', './logs')
os.makedirs(log_dir, exist_ok=True)

handler = logging.FileHandler(f'{log_dir}/app.log')
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

logger = logging.getLogger()
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)
```

**Run with log volume:**

```bash
docker run -d \
  --name web_crawler_prod \
  -v $(pwd)/logs/:/web_crawler/logs/ \
  web_crawler:latest

# View logs
tail -f logs/app.log
```

### 3.5 Health Checks

**Add health check endpoint in `app.py`:**

```python
@app.route('/health')
def health():
    # Check file access
    try:
        with open("people.py") as f:
            f.read()
        return jsonify({'status': 'healthy', 'timestamp': datetime.now(tz).isoformat()}), 200
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500
```

**Docker health check:**

```bash
docker run -d \
  --name web_crawler_prod \
  --health-cmd='curl -f http://localhost:5001/health || exit 1' \
  --health-interval=30s \
  --health-timeout=10s \
  --health-retries=3 \
  web_crawler:latest

# Check status
docker inspect --format='{{.State.Health.Status}}' web_crawler_prod
```

---

## Phase 4: Reverse Proxy Setup (Optional)

For production, use nginx or Apache to:
- Serve on port 80/443 (HTTPS)
- Load balance (if multiple containers)
- Cache static assets
- Add security headers

### Basic nginx.conf:

```nginx
upstream flask_app {
    server localhost:5001;
}

server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://flask_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /app/static/;
        expires 1d;
        add_header Cache-Control "public, immutable";
    }
}
```

---

## Phase 5: Deployment Workflows

### 5.1 Fresh Deployment

```bash
# 1. Clone/upload code
cd /Users/lee/PycharmProjects/new_web

# 2. Create .env with production settings
echo "FLASK_ENV=production" > .env

# 3. Backup existing data
cp people.py people.py.backup.$(date +%Y%m%d_%H%M%S)

# 4. Deploy
bash docker.sh

# 5. Verify
curl http://localhost:5001/health
docker logs web_crawler
```

### 5.2 Rolling Update (Zero Downtime)

```bash
# 1. New container on different port (e.g., 5002)
CONTAINER_PORT=5002 bash docker.sh

# 2. Test new container
curl http://localhost:5002/

# 3. Switch traffic (via nginx/reverse proxy config)
# Update upstream server to 5002

# 4. Stop old container
docker stop web_crawler

# 5. Cleanup
docker rm web_crawler
```

### 5.3 Rollback Procedure

```bash
# 1. Restore people.py from backup
cp people.py.backup.20260329_120000 people.py

# 2. Restore previous image version (if tagged)
docker run -d \
  --name web_crawler \
  web_crawler:20260329_100000

# 3. Verify
curl http://localhost:5001/health

# 4. Check data
docker exec web_crawler cat /web_crawler/people.py
```

---

## Phase 6: Monitoring & Maintenance

### 6.1 Container Management

```bash
# View all containers
docker ps -a

# View resource usage
docker stats web_crawler

# View detailed info
docker inspect web_crawler

# Prune unused resources
docker system prune -a
```

### 6.2 Database Backups

```bash
# Daily backup script (cron job)
#!/bin/bash
BACKUP_DIR="/backups/web_crawler"
mkdir -p $BACKUP_DIR
cp people.py "$BACKUP_DIR/people.py.$(date +%Y%m%d_%H%M%S)"

# Keep only last 7 days
find $BACKUP_DIR -mtime +7 -delete
```

### 6.3 Performance Monitoring

**Watch for:**
- High CPU usage in long-running task (monitor with `docker stats`)
- Memory leaks from polling (use `docker logs --since 1h`)
- File size growth (check periodically: `wc -l people.py`)
- Request latency (add timing logs in `long_running_task()`)

### 6.4 Scaling Considerations

For multiple deployments:
1. Use shared volume or database for `people.py` (currently file-based)
2. Use Redis/queue system for background tasks (currently in-memory `task_results`)
3. Add load balancer (nginx) in front of multiple containers
4. Consider Kubernetes if scaling to many instances

---

## Troubleshooting Checklist

- [ ] Local test passes (`python app.py` works on http://localhost:5000)
- [ ] Docker image builds without errors (`docker build`)
- [ ] Container starts (`docker run`) and stays running
- [ ] Health check passes (`curl http://localhost:5001/health`)
- [ ] Data persists across restarts (add item, restart container, verify)
- [ ] Logs are accessible (`docker logs web_crawler`)
- [ ] Background task runs correctly (click "Start Check", verify results)
- [ ] File limits permit concurrent access (check `ulimit -n`)

---

## Emergency Procedures

### Container Won't Start

```bash
# 1. Check logs
docker logs web_crawler

# 2. Run in foreground to see errors
docker run -it web_crawler:latest python app.py

# 3. If permissions issue
docker run -it --user root web_crawler:latest /bin/sh
```

### Data Corrupted

```bash
# 1. Restore from backup
cp people.py.backup people.py

# 2. Restart container
docker restart web_crawler

# 3. Verify
curl http://localhost:5001/
```

### Port Conflict

```bash
# Find process using port 5001
lsof -i :5001

# Kill it
kill -9 <PID>

# Or use different port
docker run -p 5002:5001 web_crawler:latest
```

---

## Security Notes

⚠️ **Before production deployment:**

1. Remove hardcoded URLs from `config.py` (use environment variables)
2. Add authentication if exposed to internet
3. Use HTTPS (nginx reverse proxy + Let's Encrypt cert)
4. Validate/sanitize user input (add_item, remove_item)
5. Restrict container by using `--cap-drop=ALL` and adding only required capabilities
6. Use `.dockerignore` to exclude sensitive files
7. Run as non-root user in Dockerfile (add `USER app` before CMD)
8. Set resource limits: `--memory=512m --cpus=1.0`

---

## Support & References

- **Flask docs**: https://flask.palletsprojects.com/
- **Docker docs**: https://docs.docker.com/
- **pytz timezone guide**: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
- **nginx reverse proxy**: https://docs.nginx.com/nginx/admin-guide/web-server/reverse-proxy/
