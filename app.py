from flask import Flask, request, jsonify, render_template_string, send_file
import sqlite3
import os
from io import BytesIO
import json

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
                    notes TEXT,
                    telegram TEXT
                )''')
    conn.commit()
    conn.close()

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/contacts', methods=['GET'])
def get_contacts():
    search = request.args.get('q', '').lower()
    conn = sqlite3.connect('phonebook.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    if search:
        c.execute("""SELECT * FROM contacts 
                     WHERE LOWER(name) LIKE ? OR 
                           LOWER(phone) LIKE ? OR 
                           LOWER(email) LIKE ? OR 
                           LOWER(address) LIKE ? OR
                           LOWER(telegram) LIKE ?""",
                  (f'%{search}%', f'%{search}%', f'%{search}%', f'%{search}%', f'%{search}%'))
    else:
        c.execute("SELECT * FROM contacts")
    contacts = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(contacts)

# 💾 Бэкап базы
@app.route('/api/backup')
def download_backup():
    return send_file('phonebook.db', as_attachment=True, download_name='krasunit_phonebook.db')

@app.route('/api/contacts', methods=['POST'])
def add_contact():
    data = request.json
    required = ['name', 'phone', 'organization', 'position']
    if not all(k in data for k in required):
        return jsonify({"error": "Обязательные поля не заполнены"}), 400

    conn = sqlite3.connect('phonebook.db')
    c = conn.cursor()
    c.execute("""INSERT INTO contacts 
                 (name, phone, organization, position, email, address, notes, telegram) 
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
              (data.get('name'),
               data.get('phone'),
               data.get('organization', 'КрасЮнит'),
               data.get('position'),
               data.get('email', ''),
               data.get('address', ''),
               data.get('notes', ''),
               data.get('telegram', '')))
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
                     email = ?, address = ?, notes = ?, telegram = ?
                     WHERE id = ?""",
                  (data.get('name'),
                   data.get('phone'),
                   data.get('organization', 'КрасЮнит'),
                   data.get('position'),
                   data.get('email', ''),
                   data.get('address', ''),
                   data.get('notes', ''),
                   data.get('telegram', ''),
                   contact_id))
        conn.commit()
        conn.close()
        return jsonify({"success": True})

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <link rel="manifest" href="/static/manifest.json">
  <meta name="theme-color" content="#2c3e50">
  <title>Корпоративный справочник «КрасЮнит»</title>
  <style>
    body { font-family: Arial; max-width: 750px; margin: 20px auto; padding: 15px; background: #f9f9f9; }
    input, textarea, button { padding: 10px; margin: 5px 0; width: 100%; box-sizing: border-box; border-radius: 4px; border: 1px solid #ccc; }
    button { background: #4CAF50; color: white; cursor: pointer; }
    button:hover { opacity: 0.9; }
    .backup-btn { background: #9C27B0; }
    .contact { background: white; padding: 14px; margin: 12px 0; border-radius: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    .admin-actions { display: none; margin-top: 25px; padding: 15px; background: #fffbe6; border-radius: 6px; }
    h1 { text-align: center; color: #2c3e50; }
    h2 { margin-top: 30px; color: #333; }
    hr { margin: 20px 0; }
    #search { margin-bottom: 15px; }
    .tg-btn {
      display: inline-block;
      margin-top: 8px;
      padding: 6px 12px;
      background: #0088cc;
      color: white;
      text-decoration: none;
      border-radius: 4px;
      font-size: 14px;
    }
    .tg-btn:hover { opacity: 0.9; }
  </style>
</head>
<body>

  <h1>📞 Корпоративный справочник «КрасЮнит»</h1>

  <div>
    <input type="text" id="search" placeholder="Поиск..." oninput="loadContacts()" />
    <input type="text" id="name" placeholder="Имя сотрудника" />
    <input type="text" id="phone" placeholder="+7 (999) 999-99-99" maxlength="18" oninput="formatPhone(this)" />
    <input type="text" id="organization" placeholder="Организация" value="КрасЮнит" />
    <input type="text" id="position" placeholder="Должность" />
    <input type="email" id="email" placeholder="Эл. почта" />
    <input type="text" id="address" placeholder="Адрес" />
    <input type="text" id="telegram" placeholder="Telegram (@username)" />
    <textarea id="notes" rows="2" placeholder="Примечания"></textarea>
    <button onclick="addContact()">➕ Добавить контакт</button>
    <br><br>
    <button class="backup-btn" onclick="backupDB()">💾 Бэкап базы (phonebook.db)</button>
  </div>

  <h2>Контакты:</h2>
  <div id="contacts"></div>

  <div class="admin-actions" id="adminPanel">
    <hr>
    <h3>🛠️ Админка (только для владельца)</h3>
    <input type="password" id="adminPass" placeholder="Пароль администратора" />
    <div id="editForm" style="display:none; margin-top:15px;">
      <input type="hidden" id="editId" />
      <input type="text" id="editName" placeholder="Имя" />
      <input type="text" id="editPhone" maxlength="18" oninput="formatPhone(this)" />
      <input type="text" id="editOrganization" placeholder="Организация" />
      <input type="text" id="editPosition" placeholder="Должность" />
      <input type="email" id="editEmail" placeholder="Эл. почта" />
      <input type="text" id="editAddress" placeholder="Адрес" />
      <input type="text" id="editTelegram" placeholder="Telegram (@username)" />
      <textarea id="editNotes" rows="2" placeholder="Примечания"></textarea>
      <button onclick="updateContact()">✅ Сохранить</button>
      <button class="delete-btn" style="background:#f44336;" onclick="deleteContact()">🗑️ Удалить</button>
    </div>
  </div>

  <script>
    function formatPhone(input) {
      let v = input.value.replace(/\D/g,'').substring(0,11);
      if(v.length===0) input.value='';
      else if(v.length<=1) input.value='+7';
      else if(v.length<=4) input.value='+7 ('+v.substring(1);
      else if(v.length<=7) input.value='+7 ('+v.substring(1,4)+') '+v.substring(4);
      else input.value='+7 ('+v.substring(1,4)+') '+v.substring(4,7)+'-'+v.substring(7,9)+'-'+v.substring(9,11);
    }

    let contacts = [];
    const API = '/api/contacts';

    async function loadContacts() {
      const q = document.getElementById('search').value.trim();
      const url = q ? `${API}?q=${encodeURIComponent(q)}` : API;
      const res = await fetch(url);
      contacts = await res.json();
      render();
    }

    function render() {
      const el = document.getElementById('contacts');
      el.innerHTML = contacts.map(c => {
        let s = `<strong>${c.name}</strong><br>`;
        if(c.position) s += `<small>${c.position}, ${c.organization}</small><br>`;
        if(c.phone) s += `📞 ${c.phone}<br>`;
        if(c.email) s += `✉️ ${c.email}<br>`;
        if(c.address) s += `📍 ${c.address}<br>`;
        if(c.notes) s += `<em>📝 ${c.notes}</em><br>`;
        if(c.telegram) {
          const user = c.telegram.startsWith('@') ? c.telegram.substring(1) : c.telegram;
          s += `<a href="https://t.me/${user}" target="_blank" class="tg-btn">✉️ Написать в Telegram</a><br>`;
        }
        return `<div class="contact">${s}</div>`;
      }).join('') || '<p>Нет контактов</p>';
    }

    async function addContact() {
      const d = {
        name: document.getElementById('name').value.trim(),
        phone: document.getElementById('phone').value.trim(),
        organization: document.getElementById('organization').value.trim()||'КрасЮнит',
        position: document.getElementById('position').value.trim(),
        email: document.getElementById('email').value.trim(),
        address: document.getElementById('address').value.trim(),
        telegram: document.getElementById('telegram').value.trim(),
        notes: document.getElementById('notes').value.trim()
      };
      if(!d.name||!d.phone||!d.position) return alert('Заполните обязательные поля');
      await fetch(API, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(d)});
      ['name','phone','position','email','address','telegram','notes'].forEach(id=>document.getElementById(id).value='');
      loadContacts();
    }

    function showEdit(id) {
      document.getElementById('adminPanel').style.display='block';
      const c = contacts.find(x=>x.id==id);
      Object.assign(document, {
        editId: c.id,
        editName: c.name,
        editPhone: c.phone,
        editOrganization: c.organization,
        editPosition: c.position,
        editEmail: c.email||'',
        editAddress: c.address||'',
        editTelegram: c.telegram||'',
        editNotes: c.notes||''
      });
      document.getElementById('editForm').style.display='block';
    }

    async function updateContact() {
      const id = document.getElementById('editId').value;
      const pass = document.getElementById('adminPass').value;
      if(!pass) return alert('Пароль!');
      const d = {
        name: document.getElementById('editName').value.trim(),
        phone: document.getElementById('editPhone').value.trim(),
        organization: document.getElementById('editOrganization').value.trim()||'КрасЮнит',
        position: document.getElementById('editPosition').value.trim(),
        email: document.getElementById('editEmail').value.trim(),
        address: document.getElementById('editAddress').value.trim(),
        telegram: document.getElementById('editTelegram').value.trim(),
        notes: document.getElementById('editNotes').value.trim()
      };
      if(!d.name||!d.phone||!d.position) return alert('Обязательные поля');
      await fetch(`${API}/${id}`, {
        method:'PUT',
        headers:{'Content-Type':'application/json','X-Admin-Password':pass},
        body:JSON.stringify(d)
      });
      loadContacts();
      document.getElementById('editForm').style.display='none';
      document.getElementById('adminPass').value='';
    }

    async function deleteContact() {
      if(!confirm('Удалить?')) return;
      const id = document.getElementById('editId').value;
      const pass = document.getElementById('adminPass').value;
      if(!pass) return alert('Пароль!');
      await fetch(`${API}/${id}`, {method:'DELETE', headers:{'X-Admin-Password':pass}});
      loadContacts();
      document.getElementById('editForm').style.display='none';
      document.getElementById('adminPass').value='';
    }

    function backupDB() {
      if(confirm('Скачать полную резервную копию базы данных?\\nФайл: krasunit_phonebook.db')) {
        window.location.href = '/api/backup';
      }
    }

    // При клике на контакт — показать админку
    document.addEventListener('click', function(e) {
      if (e.target.closest('.contact')) {
        const contactDiv = e.target.closest('.contact');
        const index = Array.from(document.querySelectorAll('.contact')).indexOf(contactDiv);
        if (index >= 0) showEdit(contacts[index].id);
      }
    });

    loadContacts();
  </script>
</body>
</html>
"""

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
