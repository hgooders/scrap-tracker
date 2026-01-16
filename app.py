from flask import Flask, request, redirect, render_template_string, Response
import sqlite3, json, io

app = Flask(__name__)

HTML = """
<h1>My Tracker</h1>

<form method="post" action="/add">
 <input name="text" placeholder="Type something to track..." required style="width:300px;">
 <button type="submit">Add</button>
</form>

<p style="margin-top:10px;">
 <a href="/export"><button type="button">Download backup</button></a>
</p>

<form method="post" action="/import" enctype="multipart/form-data" style="margin-top:10px;">
 <input type="file" name="file" accept="application/json" required>
 <button type="submit">Restore backup</button>
</form>

<ul>
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

@app.get("/")
def home():
   conn = db()
   items = conn.execute("SELECT id, text FROM items ORDER BY id DESC").fetchall()
   conn.close()
   return render_template_string(HTML, items=items)

@app.post("/add")
def add():
   conn = db()
   conn.execute("INSERT INTO items (text) VALUES (?)", (request.form["text"],))
   conn.commit()
   conn.close()
   return redirect("/")

@app.post("/delete/<int:item_id>")
def delete(item_id):
   conn = db()
   conn.execute("DELETE FROM items WHERE id=?", (item_id,))
   conn.commit()
   conn.close()
   return redirect("/")

@app.get("/export")
def export():
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

@app.post("/import")
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
