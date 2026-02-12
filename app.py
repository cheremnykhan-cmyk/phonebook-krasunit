from flask import Flask, request, jsonify, render_template_string
import sqlite3
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

app = Flask(__name__)

# === Настройки ===
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', '4722')
EMAIL_USER = os.environ.get('EMAIL_USER', 'KrasUnit@mail.ru')
EMAIL_PASS = os.environ.get('EMAIL_PASS', '')
SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.mail.ru')
SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))

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

def send_backup_email():
    """Отправляет phonebook.db на EMAIL_USER"""
    if not EMAIL_PASS:
        return  # пропустить, если нет пароля

    msg = MIMEMultipart()
    msg['From'] = EMAIL_USER
    msg['To'] = EMAIL_USER
    msg['Subject'] = "Авто-бэкап: КрасЮнит справочник"

    # Прикрепляем файл
    with open('phonebook.db', 'rb') as f:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', 'attachment; filename="krasunit_phonebook.db"')
    msg.attach(part)

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, EMAIL_USER, msg.as_string())
        server.quit()
    except Exception as e:
        print(f"Ошибка отправки бэкапа: {e}")

# === API ===
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

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

    # 🔁 Авто-бэкап
    send_backup_email()

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
    else:
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

    # 🔁 Авто-бэкап
    send_backup_email()

    return jsonify({"success": True})

# === HTML ===
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Корпоративный справочник «КрасЮнит»</title>
  <style>
    body { font-family: Arial; max-width: 700px; margin: 20px auto; padding: 15px; background: #f9f9f9; }
    input, textarea, button { padding: 10px; margin: 5px 0; width: 100%; box-sizing: border-box; border-radius: 4px; border: 1px solid #ccc; }
    button { background: #4CAF50; color: white; cursor: pointer; }
    .delete-btn { background: #f44336; }
    .contact { background: white; padding: 12px; margin: 10px 0; border-radius: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); cursor: pointer; }
    .admin-actions { display: none; margin-top: 20px; padding: 15px; background: #fffbe6; border-radius: 6px; }
    h1 { text-align: center; color: #2c3e50; }
    h2 { margin-top: 30px; color: #333; }
  </style>
</head>
<body>

  <h1>📞 Корпоративный справочник «КрасЮнит»</h1>

  <div>
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
    <div id="editForm" style="display:none; margin-top:10px;">
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
      const res = await fetch(API);
      contacts = await res.json();
      renderContacts();
    }

    function renderContacts() {
      const el = document.getElementById('contacts');
      el.innerHTML = contacts.map(c => 
        `<div class="contact" onclick="showEdit(${c.id})">
          <strong>${c.name}</strong><br>
          <small>${c.position}, ${c.organization}</small><br>
          📞 ${c.phone}<br>
          ${c.email ? '✉️ ' + c.email + '<br>' : ''}
          ${c.address ? '📍 ' + c.address + '<br>' : ''}
          ${c.notes ? '<em>📝 ' + c.notes + '</em><br>' : ''}
        </div>`
      ).join('') || '<p>Список контактов пуст.</p>';
    }

    async function addContact() {
      const d = {
        name: document.getElementById('name').value.trim(),
        phone: document.getElementById('phone').value.trim(),
        organization: document.getElementById('organization').value.trim() || 'КрасЮнит',
        position: document.getElementById('position').value.trim(),
        email: document.getElementById('email').value.trim(),
        address: document.getElementById('address').value.trim(),
        notes: document.getElementById('notes').value.trim()
      };
      if (!d.name || !d.phone || !d.position) return alert('Заполните обязательные поля!');
      await fetch(API, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(d)});
      document.querySelectorAll('#name,#phone,#position,#email,#address,#notes').forEach(el=>el.value='');
      loadContacts();
    }

    function showEdit(id) {
      document.getElementById('adminPanel').style.display = 'block';
      const c = contacts.find(x => x.id == id);
      document.getElementById('editId').value = id;
      document.getElementById('editName').value = c.name;
      document.getElementById('editPhone').value = c.phone;
      document.getElementById('editOrganization').value = c.organization;
      document.getElementById('editPosition').value = c.position;
      document.getElementById('editEmail').value = c.email || '';
      document.getElementById('editAddress').value = c.address || '';
      document.getElementById('editNotes').value = c.notes || '';
      document.getElementById('editForm').style.display = 'block';
    }

    async function updateContact() {
      const id = document.getElementById('editId').value;
      const pass = document.getElementById('adminPass').value;
      if (!pass) return alert('Введите пароль!');
      const d = {
        name: document.getElementById('editName').value.trim(),
        phone: document.getElementById('editPhone').value.trim(),
        organization: document.getElementById('editOrganization').value.trim() || 'КрасЮнит',
        position: document.getElementById('editPosition').value.trim(),
        email: document.getElementById('editEmail').value.trim(),
        address: document.getElementById('editAddress').value.trim(),
        notes: document.getElementById('editNotes').value.trim()
      };
      if (!d.name || !d.phone || !d.position) return alert('Заполните все обязательные поля!');
      await fetch(`${API}/${id}`, {
        method: 'PUT',
        headers: {'Content-Type': 'application/json', 'X-Admin-Password': pass},
        body: JSON.stringify(d)
      });
      loadContacts();
      document.getElementById('editForm').style.display = 'none';
      document.getElementById('adminPass').value = '';
    }

    async function deleteContact() {
      if (!confirm('Удалить контакт?')) return;
      const id = document.getElementById('editId').value;
      const pass = document.getElementById('adminPass').value;
      if (!pass) return alert('Введите пароль!');
      await fetch(`${API}/${id}`, {method: 'DELETE', headers: {'X-Admin-Password': pass}});
      loadContacts();
      document.getElementById('editForm').style.display = 'none';
      document.getElementById('adminPass').value = '';
    }

    loadContacts();
  </script>
</body>
</html>
"""

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))