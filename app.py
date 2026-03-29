import logging
from datetime import datetime
import json

import requests
from flask import Flask, render_template, request, jsonify
import threading
import pytz

from config import headers, base_url

app = Flask(__name__)

logging.basicConfig(level=logging.DEBUG)

# Lock for thread-safe file operations
file_lock = threading.Lock()

def read_from_file():
    """Read people data from JSON file."""
    try:
        with open("people.py") as file:
            data = json.load(file)
            return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        logging.warning("people.py not found or invalid JSON, returning empty list")
        return []

tz = pytz.timezone('Europe/Amsterdam')

# Shared state
items = read_from_file()
task_results = []
task_running = False

def format_last_seen(iso_timestamp):
    """Format ISO timestamp as 'N days ago' for display."""
    if not iso_timestamp:
        return None
    try:
        last_seen = datetime.fromisoformat(iso_timestamp)
        now = datetime.now(tz)
        delta = now - last_seen
        days = delta.days
        
        if days == 0:
            return "Today"
        elif days == 1:
            return "Yesterday"
        else:
            return f"{days} days ago"
    except Exception as e:
        logging.error(f"Error formatting timestamp: {e}")
        return iso_timestamp


@app.route('/')
def index():
    # Format last_seen timestamps for display
    formatted_items = [
        {**person, 'last_seen_formatted': format_last_seen(person.get('last_seen'))}
        for person in items
    ]
    return render_template('index.html', items=formatted_items, task_results=task_results, task_running=task_running)


@app.route('/add', methods=['POST'])
def add_item():
    global items
    name = request.form.get('add_item', '').strip()
    if not name:
        return jsonify({'success': False, 'message': 'No name provided.'})
    
    with file_lock:
        items = read_from_file()  # Re-read to ensure consistency
        # Check if person already exists
        if any(person['name'] == name for person in items):
            return jsonify({'success': False, 'message': f'"{name}" already exists in list.'})
        
        # Create new person object
        new_person = {
            'name': name,
            'description': request.form.get('description', '').strip(),
            'last_seen': None
        }
        items.append(new_person)
        write_to_file()
        msg = f'Added "{name}" to list.'
        logging.info(f"Added person: {name}")
    
    return jsonify({'success': True, 'message': msg})


@app.route('/remove', methods=['POST'])
def remove_item():
    global items
    name = request.form.get('remove_item', '').strip()
    if not name:
        return jsonify({'success': False, 'message': 'No name provided.'})
    
    with file_lock:
        items = read_from_file()  # Re-read to ensure consistency
        person_to_remove = None
        for person in items:
            if person['name'] == name:
                person_to_remove = person
                break
        
        if person_to_remove:
            items.remove(person_to_remove)
            write_to_file()
            msg = f'Removed "{name}" from list.'
            logging.info(f"Removed person: {name}")
        else:
            msg = f'"{name}" not found in list.'
            logging.warning(f"Attempt to remove non-existent person: {name}")
    
    return jsonify({'success': True, 'message': msg})


def long_running_task():
    global task_running, task_results, items
    task_running = True
    task_results.clear()
    
    # Take a snapshot of items to avoid conflicts with concurrent add/remove
    with file_lock:
        items_snapshot = [person.copy() for person in items]
    
    logging.info(f"Starting task with {len(items_snapshot)} people")
    
    for person in sorted(items_snapshot, key=lambda p: p['name']):
        try:
            name = person['name']
            resp = make_request(name)
            online_count = str(resp.content).count('offline')
            logging.info(f"Count for {name} is {online_count}")

            # Update last_seen for every person checked
            person['last_seen'] = datetime.now(tz).isoformat()
            
            if online_count == 5:
                task_results.append(base_url.format(name))
        except Exception as e:
            logging.error(f"Error processing {person['name']}: {e}")
            task_results.append(f"Error: {person['name']}")

    if len(task_results) == 0:
        task_results = ["All Offline"]

    # Write back updated items with last_seen timestamps
    with file_lock:
        for updated_person in items_snapshot:
            for i, item in enumerate(items):
                if item['name'] == updated_person['name']:
                    items[i] = updated_person
                    break
        write_to_file()

    now = datetime.now(tz)
    task_results.append(f"Last run at {now.strftime('%H:%M:%S')}")
    logging.info(f"Task completed with {len(task_results)} results")
    print(task_results)
    task_running = False


@app.route('/start_task', methods=['POST'])
def start_task():
    global task_running
    if not task_running:
        thread = threading.Thread(target=long_running_task)
        thread.start()
        return jsonify({'started': True})
    return jsonify({'started': False})


@app.route('/task_status')
def task_status():
    return jsonify({
        'running': task_running,
        'results': task_results
    })


def write_to_file():
    """Atomically write people data to JSON file to prevent corruption."""
    import tempfile
    import shutil
    try:
        # Write to temporary file first
        temp_fd, temp_path = tempfile.mkstemp(dir='.', prefix='.people_', suffix='.tmp')
        try:
            with open(temp_fd, 'w') as f:
                json.dump(items, f, indent=2)
            # Atomic move (rename) replaces original
            shutil.move(temp_path, 'people.py')
            logging.debug(f"Successfully wrote {len(items)} people to people.py")
        except Exception as e:
            import os
            os.close(temp_fd)
            os.unlink(temp_path)
            raise e
    except Exception as e:
        logging.error(f"Failed to write to people.py: {e}")
        raise


def make_request(person_name):
    """Make HTTP request to check person's status."""
    person_name = person_name.rstrip('\n')
    session = requests.Session()
    session.headers['User-Agent'] = headers
    url = base_url.format(person_name + "/?")
    resp = session.get(url)
    return resp

if __name__ == '__main__':
    app.run(debug=True)
