from flask import Flask, request, jsonify, render_template_string, send_file
import sqlite3
import os

app = Flask(__name__)

# === Настройки ===
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', '4722')

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

# Получить контакты + поиск
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

    # Фильтрация на Python — поддерживает кириллицу
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

# Добавить контакт
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

# Редактирование и удаление
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

# 💾 Бэкап базы данных
@app.route('/api/backup')
def download_backup():
    return send_file('phonebook.db', as_attachment=True, download_name='krasunit_phonebook.db')

# === HTML + JS ===
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Корпоративный справочник «КрасЮнит»</title>
  <style>
    body {
      font-family: Arial;
      max-width: 750px;
      margin: 20px auto;
      padding: 15px;
      background: #f9f9f9;
    }
    .content {
      background: white;
      padding: 20px;
      border-radius: 10px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    input, textarea, button {
      padding: 10px;
      margin: 5px 0;
      width: 100%;
      box-sizing: border-box;
      border-radius: 4px;
      border: 1px solid #ccc;
    }
    button {
      background: #4CAF50;
      color: white;
      cursor: pointer;
    }
    button:hover { opacity: 0.9; }
    .delete-btn { background: #f44336; }
    .backup-btn { background: #9C27B0; }
    .contact {
      background: #f9f9f9;
      padding: 12px;
      margin: 10px 0;
      border-radius: 6px;
      cursor: pointer;
    }
    .admin-actions {
      display: none;
      margin-top: 25px;
      padding: 15px;
      background: #fffbe6;
      border-radius: 6px;
    }
    h1 {
      text-align: center;
      color: #2c3e50;
    }
    h2 {
      margin-top: 30px;
      color: #333;
    }
    hr { margin: 20px 0; }
    #search { margin-bottom: 15px; }
  </style>
</head>
<body>

  <div class="content">

    <h1>📞 Корпоративный справочник «КрасЮнит»</h1>

    <div>
      <input type="text" id="search" placeholder="Поиск по имени, телефону..." oninput="loadContacts()" />
      <input type="text" id="name" placeholder="Имя сотрудника" />
      <input type="text" id="phone" placeholder="+7 (999) 999-99-99" maxlength="18" oninput="formatPhone(this)" />
      <input type="text" id="organization" placeholder="Организация" value="КрасЮнит" />
      <input type="text" id="position" placeholder="Должность" />
      <input type="email" id="email" placeholder="Эл. почта" />
      <input type="text" id="address" placeholder="Адрес" />
      <textarea id="notes" rows="2" placeholder="Примечания"></textarea>
      <button onclick="addContact()">➕ Добавить контакт</button>
    </div>

    <h2>Контакты:</h2>
    <div id="contacts"></div>

    <div class="admin-actions" id="adminPanel">
      <hr>
      <h3>🛠️ Админка (только для владельца)</h3>
      <input type="password" id="adminPass" placeholder="Пароль администратора" />
      
      <button class="backup-btn" style="margin-top:12px;" onclick="backupDB()">💾 Бэкап базы</button>
      
      <div id="editForm" style="display:none; margin-top:15px;">
        <input type="hidden" id="editId" />
        <input type="text" id="editName" placeholder="Имя" />
        <input type="text" id="editPhone" placeholder="+7 (999) 999-99-99" maxlength="18" oninput="formatPhone(this)" />
        <input type="text" id="editOrganization" placeholder="Организация" />
        <input type="text" id="editPosition" placeholder="Должность" />
        <input type="email" id="editEmail" placeholder="Эл. почта" />
        <input type="text" id="editAddress" placeholder="Адрес" />
        <textarea id="editNotes" rows="2" placeholder="Примечания"></textarea>
        <button onclick="updateContact()">✅ Сохранить</button>
        <button class="delete-btn" onclick="deleteContact()">🗑️ Удалить</button>
      </div>
    </div>

  </div>

  <script>
    function formatPhone(input) {
      let value = input.value.replace(/\D/g, '').substring(0, 11);
      if (value.length === 0) input.value = '';
      else if (value.length <= 1) input.value = '+7';
      else if (value.length <= 4) input.value = '+7 (' + value.substring(1);
      else if (value.length <= 7) input.value = '+7 (' + value.substring(1, 4) + ') ' + value.substring(4);
      else input.value = '+7 (' + value.substring(1, 4) + ') ' + value.substring(4, 7) + '-' + value.substring(7, 9) + '-' + value.substring(9, 11);
    }

    let contacts = [];
    const API = '/api/contacts';

    async function loadContacts() {
      const search = document.getElementById('search').value.trim();
      const url = search ? `${API}?q=${encodeURIComponent(search)}` : API;
      const res = await fetch(url);
      contacts = await res.json();
      renderContacts();
    }

    function renderContacts() {
      const el = document.getElementById('contacts');
      if (contacts.length === 0) {
        el.innerHTML = '<p>Список контактов пуст.</p>';
        return;
      }
      el.innerHTML = contacts.map(c => {
        let info = `<strong>${c.name}</strong><br>`;
        if (c.position || c.organization) info += `<small>${c.position || ''}${c.organization ? ', ' + c.organization : ''}</small><br>`;
        if (c.phone) info += `📞 ${c.phone}<br>`;
        if (c.email) info += `✉️ ${c.email}<br>`;
        if (c.address) info += `📍 ${c.address}<br>`;
        if (c.notes) info += `<em>📝 ${c.notes}</em><br>`;
        return `<div class="contact" onclick="showEdit(${c.id})">${info}</div>`;
      }).join('');
    }

    async function addContact() {
      const name = document.getElementById('name').value.trim();
      const phone = document.getElementById('phone').value.trim();
      const organization = document.getElementById('organization').value.trim() || 'КрасЮнит';
      const position = document.getElementById('position').value.trim();
      if (!name || !phone || !position) {
        alert('Заполните обязательные поля: Имя, Телефон, Должность');
        return;
      }

      await fetch(API, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          name, phone, organization, position,
          email: document.getElementById('email').value.trim(),
          address: document.getElementById('address').value.trim(),
          notes: document.getElementById('notes').value.trim()
        })
      });
      document.getElementById('name').value = '';
      document.getElementById('phone').value = '';
      document.getElementById('position').value = '';
      document.getElementById('email').value = '';
      document.getElementById('address').value = '';
      document.getElementById('notes').value = '';
      loadContacts();
    }

    function showEdit(id) {
      document.getElementById('adminPanel').style.display = 'block';
      const contact = contacts.find(c => c.id == id);
      if (!contact) return;

      document.getElementById('editId').value = contact.id;
      document.getElementById('editName').value = contact.name;
      document.getElementById('editPhone').value = contact.phone;
      document.getElementById('editOrganization').value = contact.organization;
      document.getElementById('editPosition').value = contact.position;
      document.getElementById('editEmail').value = contact.email || '';
      document.getElementById('editAddress').value = contact.address || '';
      document.getElementById('editNotes').value = contact.notes || '';
      document.getElementById('editForm').style.display = 'block';
    }

    async function updateContact() {
      const id = document.getElementById('editId').value;
      const pass = document.getElementById('adminPass').value;
      if (!pass) return alert('Введите пароль администратора!');

      const data = {
        name: document.getElementById('editName').value.trim(),
        phone: document.getElementById('editPhone').value.trim(),
        organization: document.getElementById('editOrganization').value.trim() || 'КрасЮнит',
        position: document.getElementById('editPosition').value.trim(),
        email: document.getElementById('editEmail').value.trim(),
        address: document.getElementById('editAddress').value.trim(),
        notes: document.getElementById('editNotes').value.trim()
      };

      if (!data.name || !data.phone || !data.position) {
        return alert('Заполните обязательные поля: Имя, Телефон, Должность');
      }

      const res = await fetch(`${API}/${id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'X-Admin-Password': pass
        },
        body: JSON.stringify(data)
      });

      if (res.ok) {
        loadContacts();
        document.getElementById('editForm').style.display = 'none';
        document.getElementById('adminPass').value = '';
      } else {
        const error = await res.json();
        alert('Ошибка: ' + (error.error || 'сервер не отвечает'));
      }
    }

    async function deleteContact() {
      if (!confirm('Удалить контакт?')) return;
      const id = document.getElementById('editId').value;
      const pass = document.getElementById('adminPass').value;
      if (!pass) return alert('Введите пароль администратора!');

      const res = await fetch(`${API}/${id}`, {
        method: 'DELETE',
        headers: {'X-Admin-Password': pass}
      });

      if (res.ok) {
        loadContacts();
        document.getElementById('editForm').style.display = 'none';
        document.getElementById('adminPass').value = '';
      } else {
        const error = await res.json();
        alert('Ошибка: ' + (error.error || 'доступ запрещён'));
      }
    }

    function backupDB() {
      if (confirm('Скачать полную резервную копию базы данных?\\nФайл: krasunit_phonebook.db')) {
        window.location.href = '/api/backup';
      }
    }

    loadContacts();
  </script>
</body>
</html>
"""

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))