# Copilot Instructions – Online Web Crawler

## Project Overview

**Online Web Crawler** is a Flask web application that monitors online status of people by scraping a target website. It provides a web interface to manage a list of usernames and trigger batch monitoring tasks.

- **Type**: Flask web app + frontend (HTML/CSS/JS)
- **Python version**: 3.x (Alpine container)
- **Main dependencies**: Flask, requests, pytz, Flask-Cors
- **Data storage**: File-based JSON (`people.py`)
- **Deployment**: Docker containerized

## Quick Start & Build Commands

### Local Development
```bash
# Activate venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run Flask app (default: http://localhost:5000)
python3 app.py
```

### Docker Deployment
```bash
bash docker.sh
```
- Stops/removes existing container named "web_crawler"
- Builds image from Dockerfile
- Runs container on port 5001 with volume mount to current directory
- Container restarts automatically unless stopped

## Architecture

### Backend Structure (app.py)
- **Entry point**: `app.py` – Flask application with route handlers
- **Configuration**: `config.py` – API headers, base_url template
- **Data model**: `people.py` – JSON array of person objects

### Data Format (people.py)
```json
[
  {"name": "john_doe", "last_seen": "2026-03-29T14:32:45+01:00"},
  {"name": "jane_smith", "last_seen": null}
]
```
- `name` – username (required)
- `last_seen` – ISO timestamp, updated **only when person is found online**. `null` if never seen online.

### Routes
| Route | Method | Purpose |
|-------|--------|---------|
| `/` | GET | Render index.html with current items and task results |
| `/add` | POST | Add person to list (form data: `add_item`) |
| `/remove` | POST | Remove person from list (form data: `remove_item`) |
| `/start_task` | POST | Trigger long-running monitoring task in background thread |
| `/task_status` | GET | Poll for task completion status and results |

### Global State Management
```python
file_lock = threading.Lock()  # Serialises all file reads/writes
items = read_from_file()      # Current list of people (list of dicts)
task_results = []             # Results from last monitoring run
task_running = False          # Flag for task execution status
```
⚠️ **Note**: `task_results` and `task_running` are in-memory only and lost on restart.

### Thread Safety
All mutations to `items` and `people.py` are protected by `file_lock`:
- `/add` and `/remove` acquire the lock, re-read file for consistency, then write atomically
- `long_running_task()` takes a snapshot inside the lock before iterating
- `write_to_file()` writes to a temp file then renames atomically to prevent corruption
- Flask auto-reloader is **disabled** (`use_reloader=False`) to prevent `people.py` writes from triggering restarts

### Long-Running Task Pattern
- Triggered via `/start_task` → spawns background thread
- Task takes a deep copy snapshot of `items` before iterating
- For each person: makes HTTP request, counts `'offline'` occurrences in response
- **`last_seen` updated only when `online_count == 5`** (person confirmed online)
- Results written back to `people.py` at end of task
- Frontend polls `/task_status` every 1 second to display results
- Results include timestamp (Europe/Amsterdam timezone)

### `format_last_seen()` Helper
Converts ISO timestamp to human-readable string:
- `"Today"` – same day
- `"Yesterday"` – 1 day ago
- `"N days ago"` – older
- `None` → displays as `"Never checked"` in template

### Frontend (static/, templates/)
- **HTML**: `templates/index.html` – Two-column layout (Manage People | Online results)
- **JavaScript**: `static/script.js` – Event handlers for forms, polling logic
- **Styling**: `static/style.css` – Layout and visual styling

#### Frontend Patterns
- Add/Remove forms use `async fetch()` with `FormData`, reload page on success
- Task status polling: shows spinner while running, updates table when complete
- Messages display briefly (1.5s) in `.message` element above list
- People table columns: **Name** | **Last Seen** (no description column)
- Templates use Jinja2; `last_seen_formatted` field added server-side before render

## Code Conventions

### Python
- **Logging**: Use `logging` module (basicConfig level: DEBUG)
- **Timezone-aware timestamps**: Use `pytz.timezone('Europe/Amsterdam')`, ISO format via `.isoformat()`
- **JSON responses**: Always use `jsonify()` for API consistency
- **File I/O**: Use context managers (`with open(...)`)
- **Threading**: Use `threading.Thread()` for background tasks; always declare `global` when mutating shared state
- **File writes**: Always go through `write_to_file()` – never write directly to `people.py`
- **File reads in routes**: Re-read from disk inside the lock before modifying to avoid stale state

### JavaScript
- Event listeners attached to form/button IDs
- No framework (vanilla JS with Fetch API)
- All API calls use `method: 'POST'` or `GET`, expect JSON responses
- Polling interval hardcoded to 1000ms

### File Organization
```
app.py              # Main Flask app with all routes
config.py           # Configuration constants (headers, base_url)
people.py           # JSON data file (name + last_seen per person)
requirements.txt    # Python dependencies
Dockerfile          # Alpine-based Python 3 container
docker.sh           # Build and run script
DEPLOYMENT.md       # Full deployment guide
README.md           # Project readme
test_concurrency.py # Concurrency stress test
templates/
  index.html        # Single-page template with two columns
static/
  script.js         # Event handling and polling logic
  style.css         # Styling
  assets/images/    # Static assets
```

## Common Patterns & Gotchas

### Adding Features to Routes
1. Define route with `@app.route()`
2. Extract request data via `request.form.get()` or `request.json`
3. Acquire `file_lock` before touching `items` or `people.py`
4. Re-read from file inside lock: `items = read_from_file()`
5. Modify, then call `write_to_file()`
6. Return JSON: `jsonify({'key': value})`

### Modifying Long-Running Task
- Task runs in a separate thread – use global variables to communicate state
- Always clear `task_results` at start: `task_results.clear()`
- Always snapshot items: `items_snapshot = [p.copy() for p in items]` inside `file_lock`
- Only update `last_seen` when the person is confirmed online
- Write snapshot back to `people.py` via `write_to_file()` at end of task
- Update `task_running` flag before and after task executes

### Frontend Updates
- Full page reload only needed for CRUD operations (add/remove)
- Task polling uses partial HTML updates (table swap) without reload
- Add new event listeners in `script.js` with same pattern (`addEventListener` + async fetch)

## Potential Issues

1. **Auto-reloader disabled**: `use_reloader=False` prevents `people.py` writes restarting Flask, but means Python code changes require a manual restart
2. **In-memory results**: `task_results` lost on restart; consider Redis if persistence needed
3. **Memory leaks**: If polling requests pile up, consider timeout/abort patterns in JS
4. **Container volume mounts**: Docker mounts `$(pwd)/` allowing live edits, but `__pycache__/` may accumulate

## Assistance Guidelines

### When asked to:
- **Fix bugs**: Check `file_lock` usage, global state mutations, and concurrent access patterns
- **Add features**: Follow routes/frontend patterns; always protect `items` mutations with `file_lock`; use `jsonify()` for responses
- **Modify data model**: Update `read_from_file()`, `write_to_file()`, `/add` route, and template together
- **Optimize**: Profile the monitoring task; consider connection pooling for requests
- **Deploy**: Use `docker.sh`; see `DEPLOYMENT.md` for production setup
- **Debug**: Check logs (`docker logs web_crawler`); auto-reloader is off so restart manually after code changes


## Quick Start & Build Commands

### Local Development
```bash
# Activate venv (auto-activated by terminal at /Users/lee/PycharmProjects/new_web)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run Flask app (default: http://localhost:5000)
python app.py
```

### Docker Deployment
```bash
bash docker.sh
```
- Stops/removes existing container named "web_crawler"
- Builds image from Dockerfile
- Runs container on port 5001 with volume mount to current directory
- Container restarts automatically unless stopped

## Architecture

### Backend Structure (app.py)
- **Entry point**: `app.py` – Flask application with route handlers
- **Configuration**: `config.py` – API headers, base_url template
- **Data model**: `people.py` – newline-delimited list of usernames (one per line)

### Routes
| Route | Method | Purpose |
|-------|--------|---------|
| `/` | GET | Render index.html with current items and task results |
| `/add` | POST | Add item to list (form data: `add_item`) |
| `/remove` | POST | Remove item from list (form data: `remove_item`) |
| `/start_task` | POST | Trigger long-running monitoring task in background thread |
| `/task_status` | GET | Poll for task completion status and results |

### Global State Management
```python
items = read_from_file()  # Current list of people
task_results = []  # Results from last monitoring run
task_running = False  # Flag for task execution status
```
⚠️ **Note**: Global state uses file persistence for `items` (via `people.py`), but `task_results` and `task_running` are in-memory only.

### Long-Running Task Pattern
- Triggered via `/start_task` → spawns background thread
- Task iterates through `items`, makes HTTP requests to check status
- Results stored in `task_results`, `task_running` flag updated
- Frontend polls `/task_status` every 1 second to display results
- Results include timestamp (Europe/Amsterdam timezone)

### Frontend (static/, templates/)
- **HTML**: `templates/index.html` – Two-column layout (Manage People | Online results)
- **JavaScript**: `static/script.js` – Event handlers for forms, polling logic
- **Styling**: `static/style.css` – Layout and visual styling

#### Frontend Patterns
- Add/Remove forms use `async fetch()` with `FormData`, reload page on success
- Task status polling: Shows spinner while running, updates table when complete
- Messages display briefly (1.5s) in `.message` element above list
- Templates use Jinja2 syntax (server-side rendering of initial state)

## Code Conventions

### Python
- **Logging**: Use `logging` module (basicConfig level: DEBUG)
- **Timezone-aware timestamps**: Use `pytz.timezone('Europe/Amsterdam')`, format as `%H:%M:%S`
- **JSON responses**: Always use `jsonify()` for API consistency
- **File I/O**: Use context managers (`with open(...)`)
- **Threading**: Use `threading.Thread()` for background tasks, manage global state with `global` keyword

### JavaScript
- Event listeners attached to form/button IDs
- No framework (vanilla JS with Fetch API)
- All API calls use `method: 'POST'` or `GET`, expect JSON responses
- Polling intervals hardcoded to 1000ms

### File Organization
```
app.py              # Main Flask app with all routes
config.py           # Configuration constants (headers, base_url)
people.py           # Data file (auto-generated from user input)
requirements.txt    # Python dependencies
Dockerfile          # Alpine-based Python 3 container
docker.sh           # Build and run script
templates/
  index.html        # Single-page template with two columns
static/
  script.js         # Event handling and polling logic
  style.css         # Styling
  assets/images/    # Static assets
```

## Common Patterns & Gotchas

### Adding Features to Routes
1. Define route with `@app.route()` 
2. Extract request data via `request.form.get()` or `request.json`
3. Modify global state if needed (use `global` keyword if updating `items`, `task_results`, etc.)
4. Get from file if adding to items: `read_from_file()` → list
5. Write back if modifying items: `write_to_file()`
6. Return JSON: `jsonify({'key': value})`

### Modifying Long-Running Task
- Task runs in separate thread, **do not directly interact with kwargs/locals from main thread**
- Use global variables to communicate state changes
- Always clear `task_results` at start: `task_results.clear()`
- Always log significant events with `logging.info()`
- Update `task_running` flag before and after task executes

### Frontend Updates
- Full page reload only needed for CRUD operations (add/remove)
- Task polling uses partial HTML updates (table swap) without reload
- Add new event listeners in `script.js` with same pattern (addEventListener + async fetch)

## Potential Issues

1. **Thread-safety**: Global state modifications could race; current app is single-threaded request handler, but background thread needs careful coordination
2. **File conflicts**: Concurrent writes to `people.py` could corrupt data if multiple requests add/remove items simultaneously
3. **Memory leaks**: If polling requests pile up, consider timeout/abort patterns
4. **Container volume mounts**: Docker mounts `$(pwd)/` allowing real-time edits without rebuild, but log files and __pycache__/ may accumulate

## Assistance Guidelines

### When asked to:
- **Fix bugs**: Check global state management, file operations, and concurrent access
- **Add features**: Follow the routes/frontend patterns above; use `jsonify()` for responses
- **Optimize**: Profile the monitoring task; consider connection pooling for requests
- **Deploy**: Use `docker.sh` script; verify port 5001 availability
- **Debug**: Enable Flask debug mode (`app.run(debug=True)`) and check logs for task status
