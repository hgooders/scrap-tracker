import os

import sqlite3

import json

import csv

import io

from functools import wraps

from flask import (

    Flask, request, redirect, session, url_for,

    render_template_string, Response

)

app = Flask(__name__)

# IMPORTANT:

# - Set SECRET_KEY and TRACKER_PASSWORD in Render Environment

app.secret_key = os.getenv("SECRET_KEY", "dev-secret-change-me")

TRACKER_PASSWORD = os.getenv("TRACKER_PASSWORD", "changeme")

LOGIN_HTML = """
<h1>My Tracker</h1>
<h2>Login</h2>
<form method="post" action="/login">
<input type="password" name="password" placeholder="Password" required>
<button type="submit">Login</button>
</form>

{% if error %}<p style="color:red;">{{ error }}</p>{% endif %}

"""

APP_HTML = """
<h1>My Tracker</h1>
<p>
<a href="/logout">Logout</a>
</p>
<form method="post" action="/add">
<input name="text" placeholder="Type something to track..." required style="width:360px;">
<button type="submit">Add</button>
</form>
<p style="margin-top:12px;">
<a href="/export.csv"><button type="button">Download CSV (Excel)</button></a>
<a href="/export.json"><button type="button">Download JSON backup</button></a>
</p>
<form method="post" action="/import" enctype="multipart/form-data" style="margin-top:10px;">
<input type="file" name="file" accept="application/json" required>
<button type="submit">Restore JSON backup</button>
</form>
<ul style="margin-top:16px;">

  {% for item in items %}
<li>{{ item[1] }}
<form method="post" action="/delete/{{ item[0] }}" style="display:inline;">
<button type="submit">X</button>
</form>
</li>

  {% endfor %}
</ul>

"""

def db():

    conn = sqlite3.connect("data.db")

    conn.execute("CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY, text TEXT)")

    return conn

def login_required(fn):

    @wraps(fn)

    def wrapper(*args, **kwargs):

        if not session.get("logged_in"):

            return redirect(url_for("login"))

        return fn(*args, **kwargs)

    return wrapper

@app.get("/login")

def login():

    return render_template_string(LOGIN_HTML, error=None)

@app.post("/login")

def login_post():

    pw = request.form.get("password", "")

    if pw == TRACKER_PASSWORD:

        session["logged_in"] = True

        return redirect("/")

    return render_template_string(LOGIN_HTML, error="Wrong password.")

@app.get("/logout")

def logout():

    session.clear()

    return redirect("/login")

@app.get("/")

@login_required

def home():

    conn = db()

    items = conn.execute("SELECT id, text FROM items ORDER BY id DESC").fetchall()

    conn.close()

    return render_template_string(APP_HTML, items=items)

@app.post("/add")

@login_required

def add():

    text = request.form["text"]

    conn = db()

    conn.execute("INSERT INTO items (text) VALUES (?)", (text,))

    conn.commit()

    conn.close()

    return redirect("/")

@app.post("/delete/<int:item_id>")

@login_required

def delete(item_id):

    conn = db()

    conn.execute("DELETE FROM items WHERE id=?", (item_id,))

    conn.commit()

    conn.close()

    return redirect("/")

@app.get("/export.json")

@login_required

def export_json():

    conn = db()

    rows = conn.execute("SELECT id, text FROM items ORDER BY id ASC").fetchall()

    conn.close()

    data = [{"id": r[0], "text": r[1]} for r in rows]

    payload = json.dumps(data, ensure_ascii=False, indent=2)

    return Response(

        payload,

        mimetype="application/json",

        headers={"Content-Disposition": "attachment; filename=tracker-backup.json"},

    )

@app.get("/export.csv")

@login_required

def export_csv():

    conn = db()

    rows = conn.execute("SELECT id, text FROM items ORDER BY id ASC").fetchall()

    conn.close()

    output = io.StringIO()

    writer = csv.writer(output)

    writer.writerow(["id", "text"])

    for r in rows:

        writer.writerow([r[0], r[1]])

    return Response(

        output.getvalue(),

        mimetype="text/csv",

        headers={"Content-Disposition": "attachment; filename=tracker.csv"},

    )

@app.post("/import")

@login_required

def import_():

    f = request.files.get("file")

    if not f:

        return redirect("/")

    data = json.loads(f.read().decode("utf-8"))

    conn = db()

    conn.execute("DELETE FROM items")

    for row in data:

        conn.execute("INSERT INTO items (id, text) VALUES (?, ?)", (row["id"], row["text"]))

    conn.commit()

    conn.close()

    return redirect("/")

if __name__ == "__main__":

    app.run()
 
