from flask import Flask, request, redirect, render_template_string
import sqlite3

app = Flask(__name__)

HTML = """
<h1>My Tracker</h1>

<form method="post" action="/add">
 <input name="text" placeholder="Type something to track..." required style="width:300px;">
 <button type="submit">Add</button>
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

@app.route("/")
def home():
   conn = db()
   items = conn.execute("SELECT id, text FROM items ORDER BY id DESC").fetchall()
   conn.close()
   return render_template_string(HTML, items=items)

@app.route("/add", methods=["POST"])
def add():
   conn = db()
   conn.execute("INSERT INTO items (text) VALUES (?)", (request.form["text"],))
   conn.commit()
   conn.close()
   return redirect("/")

@app.route("/delete/<int:item_id>", methods=["POST"])
def delete(item_id):
   conn = db()
   conn.execute("DELETE FROM items WHERE id=?", (item_id,))
   conn.commit()
   conn.close()
   return redirect("/")

if __name__ == "__main__":
   app.run()
