import os

import sqlite3

import csv

import io

from functools import wraps

from flask import (

    Flask, request, redirect, session, url_for,

    render_template_string, Response

)

app = Flask(__name__)

# Set these in Render → Environment

app.secret_key = os.getenv("SECRET_KEY", "dev-secret")

TRACKER_PASSWORD = os.getenv("TRACKER_PASSWORD", "changeme")

# Dropdown options (edit these freely)

LINE_OPTIONS = ["TRIM 1", "TRIM 2", "CHASSIS 1", "CHASSIS 2", "CHASSIS 3", "FINAL 1", "FINAL 2", "DOORLINE", "IP LINE", "ENGINE LINE", ]

SHIFT_OPTIONS = ["BLUE", "RED", ]

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
<input name="sequence" type="number"

         required style="width:100%;padding:8px;"><br><br>
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
</p>
<ul style="margin-top:16px;">

  {% for i in items %}
<li>
<b>{{ i[1] }}</b> |

      Line: {{ i[2] }} |

      Reason: {{ i[3] }} |

      Seq: {{ i[4] }} |

      Shift: {{ i[5] }}
</li>

  {% endfor %}
</ul>

"""

def db():

    conn = sqlite3.connect("data.db")

    conn.execute("""

      CREATE TABLE IF NOT EXISTS items (

        id INTEGER PRIMARY KEY,

        parts TEXT,

        line TEXT,

        reason TEXT,

        sequence INTEGER,

        shift TEXT

      )

    """)

    return conn

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

        if request.form["password"] == TRACKER_PASSWORD:

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

    items = conn.execute(

        "SELECT id, parts, line, reason, sequence, shift FROM items ORDER BY id DESC"

    ).fetchall()

    conn.close()

    return render_template_string(

        APP_HTML,

        items=items,

        line_options=LINE_OPTIONS,

        shift_options=SHIFT_OPTIONS

    )

@app.post("/add")

@login_required

def add():

    conn = db()

    conn.execute(

        "INSERT INTO items (parts, line, reason, sequence, shift) VALUES (?, ?, ?, ?, ?)",

        (

            request.form["parts"],

            request.form["line"],

            request.form["reason"],

            request.form["sequence"],

            request.form["shift"],

        ),

    )

    conn.commit()

    conn.close()

    return redirect("/")

@app.get("/export.csv")

@login_required

def export_csv():

    conn = db()

    rows = conn.execute(

        "SELECT parts, line, reason, sequence, shift FROM items ORDER BY id ASC"

    ).fetchall()

    conn.close()

    output = io.StringIO()

    writer = csv.writer(output)

    writer.writerow(["Parts", "Line", "Reason", "Sequence", "Shift"])

    for r in rows:

        writer.writerow(r)

    return Response(

        output.getvalue(),

        mimetype="text/csv",

        headers={"Content-Disposition": "attachment; filename=tracker.csv"},

    )

if __name__ == "__main__":

    app.run()
 
