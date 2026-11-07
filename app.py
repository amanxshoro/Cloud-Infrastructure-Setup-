import os
import socket
import urllib.request
from functools import lru_cache

import pymysql
import pymysql.cursors
from flask import Flask, redirect, render_template_string, request, url_for

app = Flask(__name__)

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "port": int(os.environ.get("DB_PORT", "3306")),
    "database": os.environ.get("DB_NAME", "cloudnotes"),
    "user": os.environ.get("DB_USER", "cloudnotes"),
    "password": os.environ.get("DB_PASSWORD", "change_me"),
    "cursorclass": pymysql.cursors.DictCursor,
    "autocommit": True,
}


def get_conn():
    return pymysql.connect(**DB_CONFIG)


def _get(url, headers=None, method="GET", timeout=1.5):
    req = urllib.request.Request(url, headers=headers or {}, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode()


@lru_cache(maxsize=1)
def detect_cloud():
    """Detect the cloud provider using the instance metadata service."""
    try:  # Azure
        _get("http://169.254.169.254/metadata/instance?api-version=2021-02-01",
             {"Metadata": "true"})
        return "Microsoft Azure"
    except Exception:
        pass
    try:  # GCP
        _get("http://metadata.google.internal/computeMetadata/v1/instance/id",
             {"Metadata-Flavor": "Google"})
        return "Google Cloud Platform"
    except Exception:
        pass
    try:  # AWS (IMDSv2)
        token = _get("http://169.254.169.254/latest/api/token",
                     {"X-aws-ec2-metadata-token-ttl-seconds": "60"}, method="PUT")
        _get("http://169.254.169.254/latest/meta-data/instance-id",
             {"X-aws-ec2-metadata-token": token})
        return "Amazon Web Services"
    except Exception:
        pass
    return "Unknown / local machine"


def init_db():
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS notes (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    author VARCHAR(80) NOT NULL,
                    message TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
    finally:
        conn.close()


PAGE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Cloud Notes</title>
  <style>
    body { font-family: system-ui, sans-serif; background:#f4f6fb; margin:0; color:#1b2330; }
    header { background:#1f3a68; color:#fff; padding:24px 16px; text-align:center; }
    main { max-width:720px; margin:24px auto; padding:0 16px; }
    .card { background:#fff; border-radius:10px; padding:16px 20px; margin-bottom:16px;
            box-shadow:0 1px 4px rgba(0,0,0,.08); }
    .badge { display:inline-block; background:#e3ecff; color:#1f3a68; border-radius:999px;
             padding:2px 10px; font-size:.85rem; margin-right:6px; }
    input, textarea { width:100%; padding:10px; margin:6px 0 12px; border:1px solid #c9d2e3;
                      border-radius:6px; box-sizing:border-box; font:inherit; }
    button { background:#1f3a68; color:#fff; border:0; padding:10px 18px; border-radius:6px;
             cursor:pointer; font:inherit; }
    small { color:#6b778c; }
  </style>
</head>
<body>
  <header>
    <h1>Cloud Notes</h1>
    <p>Flask web server + MySQL database on a Linux VM</p>
  </header>
  <main>
    <div class="card">
      <span class="badge">Cloud: {{ cloud }}</span>
      <span class="badge">Server: {{ host }}</span>
      <span class="badge">MySQL {{ dbver }}</span>
    </div>
    <div class="card">
      <form method="post" action="{{ url_for('add') }}">
        <label>Your name</label>
        <input name="author" maxlength="80" required>
        <label>Message</label>
        <textarea name="message" rows="3" required></textarea>
        <button type="submit">Post note</button>
      </form>
    </div>
    {% for n in notes %}
    <div class="card">
      <strong>{{ n.author }}</strong> <small>{{ n.created_at.strftime('%Y-%m-%d %H:%M') }}</small>
      <p>{{ n.message }}</p>
    </div>
    {% else %}
    <div class="card"><em>No notes yet. Be the first to post.</em></div>
    {% endfor %}
  </main>
</body>
</html>
"""


@app.route("/")
def index():
    init_db()
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT VERSION() AS v")
            dbver = cur.fetchone()["v"]
            cur.execute("SELECT * FROM notes ORDER BY created_at DESC, id DESC LIMIT 50")
            notes = cur.fetchall()
    finally:
        conn.close()
    return render_template_string(PAGE, notes=notes, cloud=detect_cloud(),
                                  host=socket.gethostname(), dbver=dbver)


@app.route("/add", methods=["POST"])
def add():
    author = request.form.get("author", "").strip()[:80]
    message = request.form.get("message", "").strip()
    if author and message:
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO notes (author, message) VALUES (%s, %s)",
                            (author, message))
        finally:
            conn.close()
    return redirect(url_for("index"))


@app.route("/health")
def health():
    try:
        conn = get_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
        conn.close()
        return {"status": "ok", "database": "connected", "cloud": detect_cloud()}
    except Exception as e:
        return {"status": "error", "detail": str(e)}, 500


try:
    init_db()
except Exception as e:
    print("DB init failed:", e)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
