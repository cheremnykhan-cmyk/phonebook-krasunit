from flask import Flask, request, jsonify, render_template_string
import sqlite3
import os

app = Flask(__name__)
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', '4722')

def init_db():
    conn = sqlite3.connect('phonebook.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS contacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    organization TEXT NOT NULL DEFAULT 'КрасЮнит',
                    position TEXT NOT NULL,
                    email TEXT,
                    address TEXT,
                    notes TEXT
                )''')
    conn.commit()
    conn.close()

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/api/contacts', methods=['GET'])
def get_contacts():
    conn = sqlite3.connect('phonebook.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM contacts")
    contacts = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(contacts)

@app.route('/api/contacts', methods=['POST'])
def add_contact():
    data = request.json
    if not data or not all(k in data for k in ('name', 'phone', 'position')):
        return jsonify({"error": "Недостаточно данных"}), 400

    conn = sqlite3.connect('phonebook.db')
    c = conn.cursor()
    c.execute("""INSERT INTO contacts 
                 (name, phone, organization, position, email, address, notes) 
                 VALUES (?, ?, ?, ?, ?, ?, ?)""",
              (data['name'],
               data['phone'],
               data.get('organization', 'КрасЮнит'),
               data['position'],
               data.get('email', ''),
               data.get('address', ''),
               data.get('notes', '')))
    conn.commit()
    conn.close()
    return jsonify({"success": True}), 201

HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8" />
  <title>КрасЮнит</title>
  <style>
    body { font-family: Arial; max-width: 600px; margin: 20px auto; }
    input, textarea, button { width: 100%; padding: 10px; margin: 5px 0; box-sizing: border-box; }
    button { background: #4CAF50; color: white; border: none; cursor: pointer; }
    .contact { background: #f9f9f9; padding: 10px; margin: 10px 0; border-radius: 4px; }
  </style>
</head>
<body>

  <h2>Добавить контакт</h2>
  <input type="text" id="name" placeholder="Имя" />
  <input type="text" id="phone" placeholder="+7 (999) 999-99-99" maxlength="18" oninput="formatPhone(this)" />
  <input type="text" id="position" placeholder="Должность" />
  <button onclick="addContact()">➕ Добавить</button>

  <h2>Контакты:</h2>
  <div id="contacts"></div>

  <script>
    function formatPhone(input) {
      let v = input.value.replace(/\D/g,'').substring(0,11);
      if(v.length===0) input.value='';
      else if(v.length<=1) input.value='+7';
      else if(v.length<=4) input.value='+7 ('+v.substring(1);
      else if(v.length<=7) input.value='+7 ('+v.substring(1,4)+') '+v.substring(4);
      else input.value='+7 ('+v.substring(1,4)+') '+v.substring(4,7)+'-'+v.substring(7,9)+'-'+v.substring(9,11);
    }

    async function loadContacts() {
      const res = await fetch('/api/contacts');
      const contacts = await res.json();
      document.getElementById('contacts').innerHTML = contacts.map(c => 
        `<div class="contact">${c.name} — ${c.phone}</div>`
      ).join('');
    }

    async function addContact() {
      const name = document.getElementById('name').value.trim();
      const phone = document.getElementById('phone').value.trim();
      const position = document.getElementById('position').value.trim();
      if (!name || !phone || !position) {
        alert('Заполните все поля!');
        return;
      }

      await fetch('/api/contacts', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({name, phone, position})
      });

      // Сброс формы
      document.getElementById('name').value = '';
      document.getElementById('phone').value = '';
      document.getElementById('position').value = '';

      loadContacts();
    }

    loadContacts();
  </script>
</body>
</html>
"""

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))