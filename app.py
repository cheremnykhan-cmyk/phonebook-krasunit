from flask import Flask, request, jsonify, render_template_string, send_file
import sqlite3
import os
import json
from io import BytesIO

app = Flask(__name__)

ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'KrasUnit2026!PhoneBook')

def init_db():
    conn = sqlite3.connect('phonebook.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS contacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    organization TEXT NOT NULL,
                    position TEXT NOT NULL,
                    email TEXT,
                    address TEXT,
                    notes TEXT
                )''')
    conn.commit()
    conn.close()

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/contacts', methods=['GET'])
def get_contacts():
    search = request.args.get('q', '').strip()
    conn = sqlite3.connect('phonebook.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM contacts")
    all_rows = c.fetchall()
    conn.close()

    if not search:
        return jsonify([dict(row) for row in all_rows])

    search_lower = search.lower()
    filtered = []
    for row in all_rows:
        r = dict(row)
        if (search_lower in str(r['name']).lower() or
            search_lower in str(r['phone']).lower() or
            search_lower in str(r['email'] or '').lower() or
            search_lower in str(r['address'] or '').lower()):
            filtered.append(r)
    return jsonify(filtered)

@app.route('/api/contacts', methods=['POST'])
def add_contact():
    data = request.json
    required = ['name', 'phone', 'organization', 'position']
    if not all(k in data for k in required):
        return jsonify({"error": "Обязательные поля не заполнены"}), 400

    conn = sqlite3.connect('phonebook.db')
    c = conn.cursor()
    c.execute("""INSERT INTO contacts 
                 (name, phone, organization, position, email, address, notes) 
                 VALUES (?, ?, ?, ?, ?, ?, ?)""",
              (data.get('name'),
               data.get('phone'),
               data.get('organization', 'КрасЮнит'),
               data.get('position'),
               data.get('email', ''),
               data.get('address', ''),
               data.get('notes', '')))
    conn.commit()
    conn.close()
    return jsonify({"success": True}), 201

@app.route('/api/contacts/<int:contact_id>', methods=['PUT', 'DELETE'])
def manage_contact(contact_id):
    password = request.headers.get('X-Admin-Password')
    if password != ADMIN_PASSWORD:
        return jsonify({"error": "Доступ запрещён"}), 403

    conn = sqlite3.connect('phonebook.db')
    c = conn.cursor()

    if request.method == 'DELETE':
        c.execute("DELETE FROM contacts WHERE id = ?", (contact_id,))
        conn.commit()
        conn.close()
        return jsonify({"success": True})

    elif request.method == 'PUT':
        data = request.json
        c.execute("""UPDATE contacts SET 
                     name = ?, phone = ?, organization = ?, position = ?,
                     email = ?, address = ?, notes = ?
                     WHERE id = ?""",
                  (data.get('name'),
                   data.get('phone'),
                   data.get('organization', 'КрасЮнит'),
                   data.get('position'),
                   data.get('email', ''),
                   data.get('address', ''),
                   data.get('notes', ''),
                   contact_id))
        conn.commit()
        conn.close()
        return jsonify({"success": True})

@app.route('/api/backup')
def download_backup():
    return send_file('phonebook.db', as_attachment=True, download_name='krasunit_phonebook.db')

HTML_TEMPLATE = """<!DOCTYPE html><html lang="ru"><head><meta charset="UTF-8"><title>КрасЮнит</title><style>body{font:14px Arial;margin:20px}</style></head><body><h1>📞 Корпоративный справочник «КрасЮнит»</h1><div id="app"></div><script>
const API='/api/contacts';let contacts=[];async function load(){const q=location.search.slice(1);const res=await fetch(q?`${API}?${q}`:API);contacts=await res.json();render();}function render(){document.getElementById('app').innerHTML=`<input placeholder="Поиск" oninput="load()"/><div>${contacts.map(c=>`<div onclick="edit(${c.id})">${c.name}<br>${c.phone}</div>`).join('')}</div>`;}function edit(id){alert('Редактирование доступно в админке');}load();
</script></body></html>"""

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))