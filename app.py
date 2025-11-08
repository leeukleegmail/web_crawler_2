import logging

import requests
from flask import Flask, render_template, request, jsonify
import threading
import time

from config import headers, base_url

app = Flask(__name__)

logging.basicConfig(level=logging.DEBUG)


def read_from_file():
    with open("people.py") as file:
        return [line.rstrip() for line in file]

# Shared state
items = read_from_file()
task_results = []
task_running = False


@app.route('/')
def index():
    return render_template('index.html', items=items, task_results=task_results, task_running=task_running)


@app.route('/add', methods=['POST'])
def add_item():
    item = request.form.get('add_item')
    if item:
        items.append(item)
        msg = f'Added "{item}" to list.'
    else:
        msg = 'No item provided.'
    write_to_file()
    return jsonify({'success': True, 'message': msg})


@app.route('/remove', methods=['POST'])
def remove_item():
    item = request.form.get('remove_item')
    if item in items:
        items.remove(item)
        msg = f'Removed "{item}" from list.'
    else:
        msg = f'"{item}" not found in list.'
    write_to_file()
    return jsonify({'success': True, 'message': msg})


def long_running_task():
    global task_running, task_results
    task_running = True
    task_results.clear()


    for person in sorted(items):
        resp = make_request(person)

        online_count = str(resp.content).count('offline')
        logging.info(f"Count for {person} is {online_count}")

        if online_count == 5:
            task_results.append(base_url.format(person))
        # task_results = [base_url.format("queen_kitty1818"), base_url.format("kaeliascorch")]

    if len(task_results) == 0:
        from time import gmtime, strftime
        task_results = [f"all offline, last check at {strftime('%Y-%m-%d %H:%M:%S', gmtime())}"]
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
    with open("people.py", 'w') as f:
        for s in items:
            f.write(s + '\n')
        f.close()


def make_request(person):
    person = person.rstrip('\n')

    session = requests.Session()
    session.headers['User-Agent'] = headers
    url = base_url.format(person + "/?")
    resp = session.get(url)
    # logging.info(f"Resp for {person} is {resp.content}")
    return resp

if __name__ == '__main__':
    app.run(debug=True)
