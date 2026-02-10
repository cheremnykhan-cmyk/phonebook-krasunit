from flask import Flask, request, jsonify, render_template_string, send_file
import sqlite3
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import pandas as pd
from io import BytesIO

app = Flask(__name__)

# === НАСТРОЙКИ (измени под себя) ===
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'KrasUnit2026!PhoneBook')
SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.mail.ru')
SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
EMAIL_USER = os.environ.get('EMAIL_USER', 'KrasUnit@mail.ru')
EMAIL_PASS = os.environ.get('EMAIL_PASS', 'твой_пароль_от_mail.ru')

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

# Получить все контакты + поиск
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
                           LOWER(address) LIKE ?""",
                  (f'%{search}%', f'%{search}%', f'%{search}%', f'%{search}%'))
    else:
        c.execute("SELECT * FROM contacts")
    contacts = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(contacts)

# Экспорт в Excel
@app.route('/api/export', methods=['GET'])
def export_excel():
    conn = sqlite3.connect('phonebook.db')
    df = pd.read_sql_query("SELECT * FROM contacts", conn)
    conn.close()
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Контакты')
    output.seek(0)
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='krasunit_phonebook.xlsx'
    )

# Добавить контакт + уведомление
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
    contact_id = c.lastrowid
    conn.commit()
    conn.close()

    # Отправка email-уведомления
    try:
        send_notification(data)
    except Exception as e:
        print(f"Ошибка отправки email: {e}")

    return jsonify({"success": True, "id": contact_id}), 201

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

# Функция отправки email
def send_notification(contact):
    msg = MIMEMultipart()
    msg['From'] = EMAIL_USER
    msg['To'] = EMAIL_USER
    msg['Subject'] = "📞 Новый контакт в справочнике КрасЮнит"
    
    body = f"""
    Добавлен новый контакт:
    Имя: {contact.get('name')}
    Телефон: {contact.get('phone')}
    Должность: {contact.get('position')}
    Организация: {contact.get('organization')}
    Email: {contact.get('email', '—')}
    Адрес: {contact.get('address', '—')}
    Примечания: {contact.get('notes', '—')}
    """
    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        text = msg.as_string()
        server.sendmail(EMAIL_USER, EMAIL_USER, text)
        server.quit()
    except Exception as e:
        print(f"Ошибка SMTP: {e}")

# === HTML + JS ===
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
    .delete-btn { background: #f44336; }
    .export-btn { background: #2196F3; }
    .contact { background: white; padding: 14px; margin: 12px 0; border-radius: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); cursor: pointer; }
    .admin-actions { display: none; margin-top: 25px; padding: 15px; background: #fffbe6; border-radius: 6px; }
    h1 { text-align: center; color: #2c3e50; }
    h2 { margin-top: 30px; color: #333; }
    hr { margin: 20px 0; }
    #search { margin-bottom: 15px; }
  </style>
</head>
<body>

  <h1>📞 Корпоративный справочник «КрасЮнит»</h1>

  <div>
    <input type="text" id="search" placeholder="Поиск по имени, телефону, email..." oninput="loadContacts()" />
    <input type="text" id="name" placeholder="Имя сотрудника" />
    <input type="text" id="phone" placeholder="+7 (999) 999-99-99" maxlength="18" oninput="formatPhone(this)" />
    <input type="text" id="organization" placeholder="Организация" value="КрасЮнит" />
    <input type="text" id="position" placeholder="Должность" />
    <input type="email" id="email" placeholder="Эл. почта (необязательно)" />
    <input type="text" id="address" placeholder="Адрес (необязательно)" />
    <textarea id="notes" rows="2" placeholder="Примечания (необязательно)"></textarea>
    <button onclick="addContact()">➕ Добавить контакт</button>
    <button class="export-btn" onclick="exportExcel()">📥 Экспорт в Excel</button>
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
        el.innerHTML = '<p>Контакты не найдены.</p>';
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
      // Сброс
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

      const data = {
        name: document.getElementById('editName').value.trim(),
        phone: document.getElementById('editPhone').value.trim(),
        organization: document.getElementById('editOrganization').value.trim() || 'КрасЮнит',
        position: document.getElementById('editPosition').value.trim(),
        email: document.getElementById('editEmail').value.trim(),
        address: document.getElementById('editAddress').value.trim(),
        notes: document.getElementById('editNotes').value.trim()
      };
      if (!data.name || !data.phone || !data.position) return alert('Заполните обязательные поля');

      const res = await fetch(`${API}/${id}`, {
        method: 'PUT',
        headers: {'Content-Type': 'application/json', 'X-Admin-Password': pass},
        body: JSON.stringify(data)
      });

      if (res.ok) {
        loadContacts();
        document.getElementById('editForm').style.display = 'none';
        document.getElementById('adminPass').value = '';
      } else {
        alert('Ошибка: неверный пароль или сервер не отвечает.');
      }
    }

    async function deleteContact() {
      if (!confirm('Удалить контакт?')) return;
      const id = document.getElementById('editId').value;
      const pass = document.getElementById('adminPass').value;
      if (!pass) return alert('Введите пароль!');

      const res = await fetch(`${API}/${id}`, {
        method: 'DELETE',
        headers: {'X-Admin-Password': pass}
      });

      if (res.ok) {
        loadContacts();
        document.getElementById('editForm').style.display = 'none';
        document.getElementById('adminPass').value = '';
      } else {
        alert('Ошибка: доступ запрещён.');
      }
    }

    async function exportExcel() {
      window.location.href = '/api/export';
    }

    loadContacts();
  </script>
</body>
</html>
"""

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))