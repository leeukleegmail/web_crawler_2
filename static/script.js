// Add Item
document.getElementById('addForm').addEventListener('submit', async e => {
  e.preventDefault();
  const formData = new FormData(e.target);
  const res = await fetch('/add', { method: 'POST', body: formData });
  const data = await res.json();
  showMessage(data.message);
  setTimeout(() => location.reload(), 800);
});

// Remove Item
document.getElementById('removeForm').addEventListener('submit', async e => {
  e.preventDefault();
  const formData = new FormData(e.target);
  const res = await fetch('/remove', { method: 'POST', body: formData });
  const data = await res.json();
  showMessage(data.message);
  setTimeout(() => location.reload(), 800);
});

// Confirmation Message
function showMessage(msg) {
  const el = document.getElementById('message');
  el.innerText = msg;
  el.style.display = 'block';
  setTimeout(() => el.style.display = 'none', 1500);
}

// Start Long Task
document.getElementById('startTaskBtn').addEventListener('click', async () => {
  await fetch('/start_task', { method: 'POST' });
  pollTask();
});

// Poll for Task Status
async function pollTask() {
  const area = document.getElementById('taskArea');
  area.innerHTML = '<div class="loading"><img src="https://i.gifer.com/ZZ5H.gif" width="50"></div>';
  const interval = setInterval(async () => {
    const res = await fetch('/task_status');
    const data = await res.json();
    if (!data.running) {
      clearInterval(interval);
      let html = '<table><tr><th>Result</th></tr>';
      data.results.forEach(r => html += `<tr><td>${r}</td></tr>`);
      html += '</table>';
      area.innerHTML = html;
    }
  }, 1000);
}
