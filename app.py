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

# Render → Environment
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
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Tracker - Login</title>
  <style>
    body { font-family: Arial, sans-serif; background:#0b1220; color:#e8eefc; margin:0; }
    .wrap { max-width: 520px; margin: 64px auto; padding: 0 16px; }
    .card { background:#121b2f; border:1px solid rgba(255,255,255,.08); border-radius:14px; padding:18px; }
    h1 { margin:0 0 10px; font-size: 26px; }
    .muted { color: rgba(232,238,252,.75); }
    input { width:100%; padding:12px; border-radius:10px; border:1px solid rgba(255,255,255,.16); background:#0f1730; color:#e8eefc; }
    button { padding:12px 14px; border-radius:10px; border:0; background:#4f7cff; color:white; font-weight:700; cursor:pointer; width:100%; margin-top:10px; }
    .error { background: rgba(255, 77, 77, .18); border:1px solid rgba(255,77,77,.35); padding:10px; border-radius:10px; margin-top:10px; }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <h1>Scrap Tracker</h1>
      <p class="muted">Enter your password to continue.</p>
      <form method="post">
        <input type="password" name="password" placeholder="Password" required>
        <button>Login</button>
      </form>
      {% if error %}
        <div class="error">{{ error }}</div>
      {% endif %}
    </div>
  </div>
</body>
</html>
"""

APP_HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Scrap Tracker</title>
  <style>
    body { font-family: Arial, sans-serif; background:#0b1220; color:#e8eefc; margin:0; }
    a { color:#9bb6ff; text-decoration:none; }
    .topbar { position: sticky; top:0; background: rgba(11,18,32,.92); backdrop-filter: blur(10px);
              border-bottom:1px solid rgba(255,255,255,.08); }
    .topbar-inner { max-width:1100px; margin:0 auto; padding:14px 16px; display:flex; align-items:center; justify-content:space-between; gap:12px; }
    .brand { display:flex; flex-direction:column; gap:2px; }
    .brand h1 { margin:0; font-size:18px; letter-spacing:.2px; }
    .brand .muted { color: rgba(232,238,252,.7); font-size: 12px; }
    .wrap { max-width:1100px; margin: 18px auto; padding: 0 16px 40px; }
    .grid { display:grid; grid-template-columns: 1fr; gap:14px; }
    @media (min-width: 980px) {
      .grid { grid-template-columns: 1.2fr .8fr; align-items:start; }
    }
    .card { background:#121b2f; border:1px solid rgba(255,255,255,.08); border-radius:14px; padding:14px; }
    h2 { margin:0 0 10px; font-size:16px; }
    label { font-size: 12px; color: rgba(232,238,252,.75); }
    input, select, textarea {
      width:100%;
      padding:10px;
      border-radius:10px;
      border:1px solid rgba(255,255,255,.16);
      background:#0f1730;
      color:#e8eefc;
      margin-top:6px;
      box-sizing:border-box;
    }
    textarea { min-height: 72px; resize: vertical; }
    .row { display:grid; grid-template-columns: 1fr; gap:12px; }
    @media (min-width: 720px) {
      .row.two { grid-template-columns: 1fr 1fr; }
      .row.three { grid-template-columns: 1fr 1fr 1fr; }
    }
    .btn { display:inline-flex; align-items:center; justify-content:center; gap:8px;
           padding:10px 12px; border-radius:10px; border:0; cursor:pointer; font-weight:700; }
    .btn-primary { background:#4f7cff; color:#fff; }
    .btn-ghost { background:transparent; border:1px solid rgba(255,255,255,.16); color:#e8eefc; }
    .btn-danger { background: rgba(255, 77, 77, .20); border:1px solid rgba(255,77,77,.35); color:#ffd2d2; }
    .btn-small { padding:8px 10px; font-weight:700; border-radius:10px; }
    .actions { display:flex; flex-wrap:wrap; gap:10px; margin-top:10px; }
    .pill { display:inline-flex; align-items:center; gap:8px; padding:8px 10px; border-radius:999px;
            border:1px solid rgba(255,255,255,.12); background: rgba(255,255,255,.03); }
    .pill b { font-size: 13px; }
    .muted { color: rgba(232,238,252,.70); }
    .table { width:100%; border-collapse: collapse; }
    .table th, .table td { border-bottom: 1px solid rgba(255,255,255,.08); padding: 10px 8px; vertical-align: top; }
    .table th { text-align:left; font-size: 12px; color: rgba(232,238,252,.75); }
    .k { color: rgba(232,238,252,.75); font-size: 12px; }
    details { margin-top: 4px; }
    summary { cursor:pointer; color:#9bb6ff; }
    .list-muted { color: rgba(232,238,252,.7); font-size: 12px; }
    .split { display:grid; grid-template-columns: 1fr; gap:14px; }
    @media (min-width: 980px) { .split { grid-template-columns: 1fr 1fr; } }
    .mini { font-size: 12px; color: rgba(232,238,252,.75); }
    .hr { height:1px; background: rgba(255,255,255,.08); margin: 12px 0; }
  </style>
</head>
<body>

  <div class="topbar">
    <div class="topbar-inner">
      <div class="brand">
        <h1>Scrap Tracker</h1>
        <div class="muted">Live • Password protected • Backups available</div>
      </div>
      <div class="actions">
        <a href="/logout" class="btn btn-ghost btn-small">Logout</a>
      </div>
    </div>
  </div>

  <div class="wrap">

    <div class="card">
      <div style="display:flex; flex-wrap:wrap; gap:10px; align-items:center; justify-content:space-between;">
        <div style="display:flex; flex-wrap:wrap; gap:10px;">
          <span class="pill"><span class="k">Total entries</span> <b>{{ totals.total }}</b></span>
          <span class="pill"><span class="k">Showing</span> <b>{{ totals.shown }}</b></span>
        </div>

        <div class="actions">
          <a href="/export.csv" class="btn btn-ghost btn-small">Download CSV</a>
          <a href="/export.json" class="btn btn-ghost btn-small">Save (Backup)</a>
          <form method="post" action="/import" enctype="multipart/form-data" style="display:flex; gap:8px; align-items:center;">
            <input type="file" name="file" accept="application/json" required style="max-width:260px;">
            <button class="btn btn-primary btn-small" type="submit">Restore</button>
          </form>
        </div>
      </div>
    </div>

    <div class="grid">

      <div class="card">
        <h2>Add entry</h2>
        <form method="post" action="/add">
          <div class="row two">
            <div>
              <label>Parts</label>
              <input name="parts" required>
            </div>
            <div>
              <label>Reason</label>
              <input name="reason" required>
            </div>
          </div>

          <div class="row three" style="margin-top:10px;">
            <div>
              <label>Line</label>
              <select name="line" required>
                {% for l in line_options %}
                  <option value="{{ l }}">{{ l }}</option>
                {% endfor %}
              </select>
            </div>
            <div>
              <label>Sequence Number</label>
              <input name="sequence" type="number" required>
            </div>
            <div>
              <label>Shift</label>
              <select name="shift" required>
                {% for s in shift_options %}
                  <option value="{{ s }}">{{ s }}</option>
                {% endfor %}
              </select>
            </div>
          </div>

          <div class="row two" style="margin-top:10px;">
            <div>
              <label>Notes</label>
              <textarea name="notes" placeholder="Optional notes..."></textarea>
            </div>
            <div>
              <label>Comments</label>
              <textarea name="comments" placeholder="Optional comments..."></textarea>
            </div>
          </div>

          <div class="actions">
            <button class="btn btn-primary" type="submit">Add</button>
          </div>
        </form>

        <div class="hr"></div>

        <h2>Filters</h2>
        <form method="get" action="/">
          <div class="row three">
            <div>
              <label>Line</label>
              <select name="f_line">
                <option value="">(All)</option>
                {% for l in line_options %}
                  <option value="{{ l }}" {% if filters.f_line==l %}selected{% endif %}>{{ l }}</option>
                {% endfor %}
              </select>
            </div>
            <div>
              <label>Shift</label>
              <select name="f_shift">
                <option value="">(All)</option>
                {% for s in shift_options %}
                  <option value="{{ s }}" {% if filters.f_shift==s %}selected{% endif %}>{{ s }}</option>
                {% endfor %}
              </select>
            </div>
            <div>
              <label>Contains (Parts / Reason)</label>
              <input name="q" value="{{ filters.q }}" placeholder="e.g. bolt, scratch, trim...">
            </div>
          </div>

          <div class="row three" style="margin-top:10px;">
            <div>
              <label>Date from (YYYY-MM-DD)</label>
              <input name="from" value="{{ filters.from_ }}" placeholder="2026-01-16">
            </div>
            <div>
              <label>Date to (YYYY-MM-DD)</label>
              <input name="to" value="{{ filters.to_ }}" placeholder="2026-01-16">
            </div>
            <div>
              <label>Reason contains</label>
              <input name="f_reason" value="{{ filters.f_reason }}" placeholder="optional">
            </div>
          </div>

          <div class="actions">
            <button class="btn btn-primary" type="submit">Apply filters</button>
            <a class="btn btn-ghost" href="/">Clear</a>
          </div>
        </form>
      </div>

      <div class="card">
        <h2>Totals</h2>
        <div class="split">
          <div>
            <div class="mini">By Line</div>
            <table class="table">
              <thead><tr><th>Line</th><th>Count</th></tr></thead>
              <tbody>
                {% for r in totals.by_line %}
                  <tr><td>{{ r[0] }}</td><td><b>{{ r[1] }}</b></td></tr>
                {% endfor %}
              </tbody>
            </table>
          </div>

          <div>
            <div class="mini">By Shift</div>
            <table class="table">
              <thead><tr><th>Shift</th><th>Count</th></tr></thead>
              <tbody>
                {% for r in totals.by_shift %}
                  <tr><td>{{ r[0] }}</td><td><b>{{ r[1] }}</b></td></tr>
                {% endfor %}
              </tbody>
            </table>

            <div class="mini" style="margin-top:12px;">Top Reasons (filtered)</div>
            <table class="table">
              <thead><tr><th>Reason</th><th>Count</th></tr></thead>
              <tbody>
                {% for r in totals.by_reason %}
                  <tr><td>{{ r[0] }}</td><td><b>{{ r[1] }}</b></td></tr>
                {% endfor %}
              </tbody>
            </table>
          </div>
        </div>
      </div>

    </div>

    <div class="card" style="margin-top:14px;">
      <h2>Entries</h2>
      <div class="list-muted">Tip: Notes/comments are hidden under “Details”. Date/time is automatic.</div>

      <table class="table" style="margin-top:10px;">
        <thead>
          <tr>
            <th>Date/Time</th>
            <th>Parts</th>
            <th>Line</th>
            <th>Reason</th>
            <th>Seq</th>
            <th>Shift</th>
            <th>More</th>
            <th>Delete</th>
          </tr>
        </thead>
        <tbody>
          {% for i in items %}
            <tr>
              <td class="muted">{{ i["created_at"] }}</td>
              <td><b>{{ i["parts"] }}</b></td>
              <td>{{ i["line"] }}</td>
              <td>{{ i["reason"] }}</td>
              <td>{{ i["sequence"] }}</td>
              <td>{{ i["shift"] }}</td>
              <td>
                <details>
                  <summary>Details</summary>
                  <div style="margin-top:6px;">
                    <div class="k">Notes</div>
                    <div>{{ i["notes"] or "-" }}</div>
                    <div class="k" style="margin-top:8px;">Comments</div>
                    <div>{{ i["comments"] or "-" }}</div>
                  </div>
                </details>
              </td>
              <td>
                <form method="post" action="/delete/{{ i['id'] }}">
                  <button class="btn btn-danger btn-small" type="submit">Delete</button>
                </form>
              </td>
            </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>

    <div class="card" style="margin-top:14px;">
      <h2>Manage dropdowns</h2>
      <div class="list-muted">These are saved in the database and included in backups.</div>

      <div class="split" style="margin-top:10px;">
        <div class="card" style="background:#0f1730;">
          <h2>Lines</h2>
          <form method="post" action="/options/add">
            <input type="hidden" name="group" value="line">
            <input name="value" placeholder="Add new line..." required>
            <div class="actions"><button class="btn btn-primary" type="submit">Add Line</button></div>
          </form>
          <div class="hr"></div>
          <table class="table">
            <thead><tr><th>Line</th><th>Remove</th></tr></thead>
            <tbody>
              {% for l in line_options %}
                <tr>
                  <td>{{ l }}</td>
                  <td>
                    <form method="post" action="/options/delete">
                      <input type="hidden" name="group" value="line">
                      <input type="hidden" name="value" value="{{ l }}">
                      <button class="btn btn-ghost btn-small" type="submit">X</button>
                    </form>
                  </td>
                </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>

        <div class="card" style="background:#0f1730;">
          <h2>Shifts</h2>
          <form method="post" action="/options/add">
            <input type="hidden" name="group" value="shift">
            <input name="value" placeholder="Add new shift..." required>
            <div class="actions"><button class="btn btn-primary" type="submit">Add Shift</button></div>
          </form>
          <div class="hr"></div>
          <table class="table">
            <thead><tr><th>Shift</th><th>Remove</th></tr></thead>
            <tbody>
              {% for s in shift_options %}
                <tr>
                  <td>{{ s }}</td>
                  <td>
                    <form method="post" action="/options/delete">
                      <input type="hidden" name="group" value="shift">
                      <input type="hidden" name="value" value="{{ s }}">
                      <button class="btn btn-ghost btn-small" type="submit">X</button>
                    </form>
                  </td>
                </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>

      </div>
    </div>

  </div>
</body>
</html>
"""

def ensure_default_options(conn, group, defaults):
    cur = conn.execute("SELECT COUNT(*) AS c FROM options WHERE opt_group=?", (group,))
    count = cur.fetchone()[0]
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
    return [r[0] for r in rows]

def column_exists(conn, table, col):
    cols = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(c[1] == col for c in cols)

def db():
    conn = sqlite3.connect("data.db")
    conn.row_factory = sqlite3.Row

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

    conn.execute("""
      CREATE TABLE IF NOT EXISTS options (
        id INTEGER PRIMARY KEY,
        opt_group TEXT NOT NULL,
        opt_value TEXT NOT NULL,
        UNIQUE(opt_group, opt_value)
      )
    """)

    # Migrate schema
    if not column_exists(conn, "items", "notes"):
        conn.execute("ALTER TABLE items ADD COLUMN notes TEXT")
    if not column_exists(conn, "items", "comments"):
        conn.execute("ALTER TABLE items ADD COLUMN comments TEXT")

    ensure_default_options(conn, "line", DEFAULT_LINE_OPTIONS)
    ensure_default_options(conn, "shift", DEFAULT_SHIFT_OPTIONS)

    conn.commit()
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
        if request.form.get("password", "") == TRACKER_PASSWORD:
            session["logged_in"] = True
            return redirect("/")
        return render_template_string(LOGIN_HTML, error="Wrong password")
    return render_template_string(LOGIN_HTML, error=None)

@app.get("/logout")
def logout():
    session.clear()
    return redirect("/login")

def build_filters(args):
    return {
        "f_line": (args.get("f_line") or "").strip(),
        "f_shift": (args.get("f_shift") or "").strip(),
        "q": (args.get("q") or "").strip(),
        "from_": (args.get("from") or "").strip(),
        "to_": (args.get("to") or "").strip(),
        "f_reason": (args.get("f_reason") or "").strip(),
    }

def apply_filters_sql(filters):
    where = []
    params = []

    if filters["f_line"]:
        where.append("line = ?")
        params.append(filters["f_line"])

    if filters["f_shift"]:
        where.append("shift = ?")
        params.append(filters["f_shift"])

    if filters["q"]:
        where.append("(parts LIKE ? OR reason LIKE ?)")
        like = f"%{filters['q']}%"
        params.extend([like, like])

    if filters["f_reason"]:
        where.append("reason LIKE ?")
        params.append(f"%{filters['f_reason']}%")

    # created_at stored as "YYYY-MM-DD HH:MM:SS" so date filtering works with LIKE/range
    if filters["from_"]:
        where.append("created_at >= ?")
        params.append(filters["from_"] + " 00:00:00")

    if filters["to_"]:
        where.append("created_at <= ?")
        params.append(filters["to_"] + " 23:59:59")

    clause = ("WHERE " + " AND ".join(where)) if where else ""
    return clause, params

def totals_for(rows):
    by_line = {}
    by_shift = {}
    by_reason = {}

    for r in rows:
        by_line[r["line"]] = by_line.get(r["line"], 0) + 1
        by_shift[r["shift"]] = by_shift.get(r["shift"], 0) + 1
        by_reason[r["reason"]] = by_reason.get(r["reason"], 0) + 1

    def sort_dict(d):
        return sorted(d.items(), key=lambda x: (-x[1], x[0]))

    return {
        "by_line": sort_dict(by_line),
        "by_shift": sort_dict(by_shift),
        "by_reason": sort_dict(by_reason)[:20],  # top 20 reasons
    }

@app.get("/")
@login_required
def home():
    conn = db()
    line_options = get_options(conn, "line")
    shift_options = get_options(conn, "shift")

    filters = build_filters(request.args)
    clause, params = apply_filters_sql(filters)

    # Total count (all)
    total_all = conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]

    # Filtered rows
    rows = conn.execute(
        f"""
        SELECT id, parts, line, reason, sequence, shift, created_at, notes, comments
        FROM items
        {clause}
        ORDER BY id DESC
        """,
        params
    ).fetchall()

    items = [{
        "id": r["id"],
        "parts": r["parts"],
        "line": r["line"],
        "reason": r["reason"],
        "sequence": r["sequence"],
        "shift": r["shift"],
        "created_at": r["created_at"],
        "notes": r["notes"],
        "comments": r["comments"],
    } for r in rows]

    t = totals_for(rows)
    totals = {
        "total": total_all,
        "shown": len(rows),
        "by_line": t["by_line"],
        "by_shift": t["by_shift"],
        "by_reason": t["by_reason"],
    }

    conn.close()

    return render_template_string(
        APP_HTML,
        items=items,
        line_options=line_options,
        shift_options=shift_options,
        filters=filters,
        totals=totals
    )

@app.post("/add")
@login_required
def add():
    parts = request.form["parts"].strip()
    line = request.form["line"].strip()
    reason = request.form["reason"].strip()
    sequence = int(request.form["sequence"].strip())
    shift = request.form["shift"].strip()
    notes = (request.form.get("notes") or "").strip() or None
    comments = (request.form.get("comments") or "").strip() or None

    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = db()
    conn.execute(
        """
        INSERT INTO items (parts, line, reason, sequence, shift, created_at, notes, comments)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (parts, line, reason, sequence, shift, created_at, notes, comments),
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
    group = (request.form.get("group") or "").strip()
    value = (request.form.get("value") or "").strip()
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
    group = (request.form.get("group") or "").strip()
    value = (request.form.get("value") or "").strip()
    if group in ("line", "shift") and value:
        conn = db()
        cur = conn.execute("SELECT COUNT(*) FROM options WHERE opt_group=?", (group,))
        if cur.fetchone()[0] > 1:
            conn.execute("DELETE FROM options WHERE opt_group=? AND opt_value=?", (group, value))
            conn.commit()
        conn.close()
    return redirect("/")

@app.get("/export.csv")
@login_required
def export_csv():
    conn = db()
    rows = conn.execute(
        """
        SELECT created_at, parts, line, reason, sequence, shift, notes, comments
        FROM items
        ORDER BY id ASC
        """
    ).fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["DateTime", "Parts", "Line", "Reason", "Sequence", "Shift", "Notes", "Comments"])
    for r in rows:
        writer.writerow([
            r["created_at"], r["parts"], r["line"], r["reason"], r["sequence"], r["shift"],
            r["notes"] or "", r["comments"] or ""
        ])

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
        """
        SELECT id, created_at, parts, line, reason, sequence, shift, notes, comments
        FROM items
        ORDER BY id ASC
        """
    ).fetchall()

    line_options = get_options(conn, "line")
    shift_options = get_options(conn, "shift")
    conn.close()

    payload = {
        "options": {"line": line_options, "shift": shift_options},
        "items": [
            {
                "id": r["id"],
                "created_at": r["created_at"],
                "parts": r["parts"],
                "line": r["line"],
                "reason": r["reason"],
                "sequence": r["sequence"],
                "shift": r["shift"],
                "notes": r["notes"],
                "comments": r["comments"],
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

    ensure_default_options(conn, "line", DEFAULT_LINE_OPTIONS)
    ensure_default_options(conn, "shift", DEFAULT_SHIFT_OPTIONS)

    # Restore items (overwrite)
    conn.execute("DELETE FROM items")
    for r in items:
        conn.execute(
            """
            INSERT INTO items (id, parts, line, reason, sequence, shift, created_at, notes, comments)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(r["id"]),
                str(r["parts"]),
                str(r["line"]),
                str(r["reason"]),
                int(r["sequence"]),
                str(r["shift"]),
                str(r.get("created_at") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                (r.get("notes") or None),
                (r.get("comments") or None),
            ),
        )

    conn.commit()
    conn.close()
    return redirect("/")

if __name__ == "__main__":
    app.run()
