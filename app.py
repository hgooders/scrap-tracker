import os

import sqlite3

import csv

import io

import json

from datetime import datetime

from functools import wraps

from flask import (

    Flask, request, redirect, session, url_for,

    render_template_string, Response

)

app = Flask(__name__)

# Render -> Environment

app.secret_key = os.getenv("SECRET_KEY", "dev-secret")

TRACKER_PASSWORD = os.getenv("TRACKER_PASSWORD", "changeme")

# Default dropdown values (used ONLY if the database has none yet)

DEFAULT_LINE_OPTIONS = [

    "TRIM 1", "TRIM 2",

    "CHASSIS 1", "CHASSIS 2", "CHASSIS 3",

    "FINAL 1", "FINAL 2",

    "DOORLINE", "IP LINE", "ENGINE LINE"

]

DEFAULT_SHIFT_OPTIONS = ["BLUE", "RED"]

LOGIN_HTML = """
<h1>Tracker</h1>
<form method="post">
<input type="password" name="password" placeholder="Password" required>
<button>Login</button>
</form>

{% if error %}<p style="color:red;">{{ error }}</p>{% endif %}

"""

APP_HTML = """
<h1>Tracker</h1>
<p><a href="/logout">Logout</a></p>
<h2>Add Entry</h2>
<form method="post" action="/add"

      style="border:1px solid #ccc;padding:12px;border-radius:8px;max-width:900px;">
<label><b>Parts</b></label><br>
<input name="parts" required style="width:100%;padding:8px;"><br><br>
<label><b>Line</b></label><br>
<select name="line" required style="width:100%;padding:8px;">

    {% for l in line_options %}
<option value="{{ l }}">{{ l }}</option>

    {% endfor %}
</select>
<br><br>
<label><b>Reason</b></label><br>
<input name="reason" required style="width:100%;padding:8px;"><br><br>
<label><b>Sequence Number</b></label><br>
<input name="sequence" type="number" required style="width:100%;padding:8px;"><br><br>
<label><b>Shift</b></label><br>
<select name="shift" required style="width:100%;padding:8px;">

    {% for s in shift_options %}
<option value="{{ s }}">{{ s }}</option>

    {% endfor %}
</select>
<br><br>
<button type="submit">Add</button>
</form>
<p style="margin-top:12px;">
<a href="/export.csv"><button type="button">Download CSV</button></a>
<a href="/export.json"><button type="button">Save (Download Backup)</button></a>
</p>
<form method="post" action="/import" enctype="multipart/form-data" style="margin-top:10px;">
<input type="file" name="file" accept="application/json" required>
<button type="submit">Restore Backup</button>
</form>
<h2 style="margin-top:22px;">Entries</h2>
<ul style="margin-top:10px; padding-left: 18px;">

  {% for i in items %}
<li style="margin-bottom:10px;">
<div>
<b>{{ i["parts"] }}</b> |

        Line: {{ i["line"] }} |

        Reason: {{ i["reason"] }} |

        Seq: {{ i["sequence"] }} |

        Shift: {{ i["shift"] }} |
<span style="color:#666;">{{ i["created_at"] }}</span>
<form method="post" action="/delete/{{ i['id'] }}" style="display:inline;">
<button type="submit" style="margin-left:10px;">Delete</button>
</form>
</div>
</li>

  {% endfor %}
</ul>
<h2 style="margin-top:22px;">Manage dropdowns</h2>
<div style="display:flex; gap:18px; flex-wrap:wrap; border:1px solid #eee; padding:12px; border-radius:8px; max-width:900px;">
<div style="flex:1; min-width:260px;">
<h3>Lines</h3>
<form method="post" action="/options/add">
<input type="hidden" name="group" value="line">
<input name="value" placeholder="Add new line..." required style="width:100%;padding:8px;">
<button type="submit" style="margin-top:8px;">Add Line</button>
</form>
<ul>

      {% for l in line_options %}
<li>

          {{ l }}
<form method="post" action="/options/delete" style="display:inline;">
<input type="hidden" name="group" value="line">
<input type="hidden" name="value" value="{{ l }}">
<button type="submit">X</button>
</form>
</li>

      {% endfor %}
</ul>
</div>
<div style="flex:1; min-width:260px;">
<h3>Shifts</h3>
<form method="post" action="/options/add">
<input type="hidden" name="group" value="shift">
<input name="value" placeholder="Add new shift..." required style="width:100%;padding:8px;">
<button type="submit" style="margin-top:8px;">Add Shift</button>
</form>
<ul>

      {% for s in shift_options %}
<li>

          {{ s }}
<form method="post" action="/options/delete" style="display:inline;">
<input type="hidden" name="group" value="shift">
<input type="hidden" name="value" value="{{ s }}">
<button type="submit">X</button>
</form>
</li>

      {% endfor %}
</ul>
</div>
</div>

"""

def db():

    conn = sqlite3.connect("data.db")

    conn.row_factory = sqlite3.Row

    # Items table (with created_at)

    conn.execute("""

      CREATE TABLE IF NOT EXISTS items (

        id INTEGER PRIMARY KEY,

        parts TEXT NOT NULL,

        line TEXT NOT NULL,

        reason TEXT NOT NULL,

        sequence INTEGER NOT NULL,

        shift TEXT NOT NULL,

        created_at TEXT NOT NULL

      )

    """)

    # Options table (saves dropdown lists)

    conn.execute("""

      CREATE TABLE IF NOT EXISTS options (

        id INTEGER PRIMARY KEY,

        opt_group TEXT NOT NULL,

        opt_value TEXT NOT NULL,

        UNIQUE(opt_group, opt_value)

      )

    """)

    # Seed defaults if empty

    ensure_default_options(conn, "line", DEFAULT_LINE_OPTIONS)

    ensure_default_options(conn, "shift", DEFAULT_SHIFT_OPTIONS)

    conn.commit()

    return conn

def ensure_default_options(conn, group, defaults):

    cur = conn.execute("SELECT COUNT(*) AS c FROM options WHERE opt_group=?", (group,))

    count = cur.fetchone()["c"]

    if count == 0:

        for v in defaults:

            conn.execute(

                "INSERT OR IGNORE INTO options (opt_group, opt_value) VALUES (?, ?)",

                (group, v.strip())

            )

def get_options(conn, group):

    rows = conn.execute(

        "SELECT opt_value FROM options WHERE opt_group=? ORDER BY opt_value ASC",

        (group,)

    ).fetchall()

    return [r["opt_value"] for r in rows]

def login_required(fn):

    @wraps(fn)

    def wrapper(*args, **kwargs):

        if not session.get("logged_in"):

            return redirect(url_for("login"))

        return fn(*args, **kwargs)

    return wrapper

@app.route("/login", methods=["GET", "POST"])

def login():

    if request.method == "POST":

        if request.form.get("password", "") == TRACKER_PASSWORD:

            session["logged_in"] = True

            return redirect("/")

        return render_template_string(LOGIN_HTML, error="Wrong password")

    return render_template_string(LOGIN_HTML, error=None)

@app.get("/logout")

def logout():

    session.clear()

    return redirect("/login")

@app.get("/")

@login_required

def home():

    conn = db()

    line_options = get_options(conn, "line")

    shift_options = get_options(conn, "shift")

    rows = conn.execute(

        "SELECT id, parts, line, reason, sequence, shift, created_at FROM items ORDER BY id DESC"

    ).fetchall()

    conn.close()

    items = []

    for r in rows:

        items.append({

            "id": r["id"],

            "parts": r["parts"],

            "line": r["line"],

            "reason": r["reason"],

            "sequence": r["sequence"],

            "shift": r["shift"],

            "created_at": r["created_at"],

        })

    return render_template_string(

        APP_HTML,

        items=items,

        line_options=line_options,

        shift_options=shift_options

    )

@app.post("/add")

@login_required

def add():

    parts = request.form["parts"].strip()

    line = request.form["line"].strip()

    reason = request.form["reason"].strip()

    sequence = request.form["sequence"].strip()

    shift = request.form["shift"].strip()

    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = db()

    conn.execute(

        "INSERT INTO items (parts, line, reason, sequence, shift, created_at) VALUES (?, ?, ?, ?, ?, ?)",

        (parts, line, reason, int(sequence), shift, created_at),

    )

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

@app.post("/options/add")

@login_required

def options_add():

    group = request.form.get("group", "").strip()

    value = request.form.get("value", "").strip()

    if group in ("line", "shift") and value:

        conn = db()

        conn.execute(

            "INSERT OR IGNORE INTO options (opt_group, opt_value) VALUES (?, ?)",

            (group, value),

        )

        conn.commit()

        conn.close()

    return redirect("/")

@app.post("/options/delete")

@login_required

def options_delete():

    group = request.form.get("group", "").strip()

    value = request.form.get("value", "").strip()

    if group in ("line", "shift") and value:

        conn = db()

        # Safety: keep at least 1 option so the dropdown never becomes empty

        cur = conn.execute(

            "SELECT COUNT(*) AS c FROM options WHERE opt_group=?",

            (group,)

        )

        if cur.fetchone()["c"] > 1:

            conn.execute(

                "DELETE FROM options WHERE opt_group=? AND opt_value=?",

                (group, value),

            )

            conn.commit()

        conn.close()

    return redirect("/")

@app.get("/export.csv")

@login_required

def export_csv():

    conn = db()

    rows = conn.execute(

        "SELECT created_at, parts, line, reason, sequence, shift FROM items ORDER BY id ASC"

    ).fetchall()

    conn.close()

    output = io.StringIO()

    writer = csv.writer(output)

    writer.writerow(["DateTime", "Parts", "Line", "Reason", "Sequence", "Shift"])

    for r in rows:

        writer.writerow([r["created_at"], r["parts"], r["line"], r["reason"], r["sequence"], r["shift"]])

    return Response(

        output.getvalue(),

        mimetype="text/csv",

        headers={"Content-Disposition": "attachment; filename=tracker.csv"},

    )

@app.get("/export.json")

@login_required

def export_json():

    conn = db()

    items = conn.execute(

        "SELECT id, created_at, parts, line, reason, sequence, shift FROM items ORDER BY id ASC"

    ).fetchall()

    line_options = get_options(conn, "line")

    shift_options = get_options(conn, "shift")

    conn.close()

    payload = {

        "options": {

            "line": line_options,

            "shift": shift_options

        },

        "items": [

            {

                "id": r["id"],

                "created_at": r["created_at"],

                "parts": r["parts"],

                "line": r["line"],

                "reason": r["reason"],

                "sequence": r["sequence"],

                "shift": r["shift"]

            }

            for r in items

        ]

    }

    return Response(

        json.dumps(payload, ensure_ascii=False, indent=2),

        mimetype="application/json",

        headers={"Content-Disposition": "attachment; filename=tracker-backup.json"},

    )

@app.post("/import")

@login_required

def import_():

    f = request.files.get("file")

    if not f:

        return redirect("/")

    data = json.loads(f.read().decode("utf-8"))

    options = data.get("options", {})

    items = data.get("items", [])

    conn = db()

    # Restore options (overwrite)

    conn.execute("DELETE FROM options WHERE opt_group IN ('line','shift')")

    for v in options.get("line", []):

        conn.execute("INSERT OR IGNORE INTO options (opt_group, opt_value) VALUES ('line', ?)", (str(v).strip(),))

    for v in options.get("shift", []):

        conn.execute("INSERT OR IGNORE INTO options (opt_group, opt_value) VALUES ('shift', ?)", (str(v).strip(),))

    # Ensure we still have at least 1 each

    ensure_default_options(conn, "line", DEFAULT_LINE_OPTIONS)

    ensure_default_options(conn, "shift", DEFAULT_SHIFT_OPTIONS)

    # Restore items (overwrite)

    conn.execute("DELETE FROM items")

    for r in items:

        conn.execute(

            "INSERT INTO items (id, parts, line, reason, sequence, shift, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",

            (

                int(r["id"]),

                str(r["parts"]),

                str(r["line"]),

                str(r["reason"]),

                int(r["sequence"]),

                str(r["shift"]),

                str(r.get("created_at", "")) or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),

            ),

        )

    conn.commit()

    conn.close()

    return redirect("/")

if __name__ == "__main__":

    app.run()
 
