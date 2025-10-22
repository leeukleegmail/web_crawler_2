import requests
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
import threading

from config import base_url, headers

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Needed for flash messages



def read_from_file():
    with open("people.py") as file:
        return [line.rstrip() for line in file]

items = read_from_file()

task_result = []
task_running = False

def long_running_task():
    global task_result, task_running
    # time.sleep(5)  # Simulate time-consuming work
    # task_result = [f"Processed item {i}" for i in range(1, 6)]

    task_running = True

    online_list = []
    for person in sorted(items):
        resp = make_request(person)

        if str(resp.content).count('offline') == 5:
            online_list.append(person)
        task_result = online_list

    if len(online_list) == 0:
        task_result = ["all offline"]

    task_running = False


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html", items=items)

@app.route("/add", methods=["POST"])
def add_item():
    item = request.form.get("add_item")
    if item:
        items.append(item)
        write_to_file()
        flash(f"Item '{item}' added successfully!", "add_success")
    return redirect(url_for("index"))

@app.route("/remove", methods=["POST"])
def remove_item():
    item = request.form.get("remove_item")
    if item in items:
        items.remove(item)
        write_to_file()
        flash(f"Item '{item}' removed successfully!", "remove_success")
    else:
        flash(f"Item '{item}' not found in list.", "remove_error")
    return redirect(url_for("index"))

@app.route("/start-task", methods=["POST"])
def start_task():
    global task_running
    if not task_running:
        thread = threading.Thread(target=long_running_task)
        thread.start()
    return jsonify({"status": "started"})

@app.route("/task-status")
def task_status():
    return jsonify({
        "running": task_running,
        "result": task_result if not task_running else []
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
    print(resp.content)
    return resp

if __name__ == "__main__":
    app.run(debug=True, port=5001)
