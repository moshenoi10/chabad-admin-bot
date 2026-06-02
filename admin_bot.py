import os, json, time, requests, threading, pickle
from datetime import datetime

ADMIN_TOKEN = os.environ.get("ADMIN_BOT_TOKEN", "")
ADMIN_ID = os.environ.get("ADMIN_ID", "1798097090")
RENDER_API_KEY = os.environ.get("RENDER_API_KEY", "")
CLIENTS_FILE = "clients.pkl"

# ─── נתוני לקוחות ─────────────────────────────────────
def load_clients():
    try:
        with open(CLIENTS_FILE, "rb") as f:
            return pickle.load(f)
    except:
        return {}

def save_clients(clients):
    with open(CLIENTS_FILE, "wb") as f:
        pickle.dump(clients, f)

clients = load_clients()
sessions = {}  # session של הגדרת לקוח חדש
offset = 0

# ─── חבילות ────────────────────────────────────────────
PACKAGES = {
    "basic": {
        "name": "בסיסי",
        "price": 99,
        "features": ["wordpress", "telegram_channel", "smart_upload", "mazaltov"],
        "description": "העלאת כתבות + ערוץ טלגרם"
    },
    "advanced": {
        "name": "מתקדם",
        "price": 199,
        "features": ["wordpress", "telegram_channel", "smart_upload", "mazaltov",
                    "facebook", "instagram", "whatsapp"],
        "description": "+ רשתות חברתיות + WhatsApp"
    },
    "premium": {
        "name": "פרימיום",
        "price": 299,
        "features": ["wordpress", "telegram_channel", "smart_upload", "mazaltov",
                    "facebook", "instagram", "whatsapp", "vimeo", "youtube",
                    "analytics", "email_monitor", "ai_gemini"],
        "description": "כל הפונקציות"
    },
    "custom": {
        "name": "מותאם אישית",
        "price": 0,
        "features": [],
        "description": "הגדרה ידנית"
    }
}

FEATURE_NAMES = {
    "wordpress": "📝 WordPress",
    "telegram_channel": "📢 ערוץ טלגרם",
    "smart_upload": "🤖 העלאה חכמה (AI)",
    "mazaltov": "🎉 מזל טוב",
    "facebook": "📘 פייסבוק",
    "instagram": "📸 אינסטגרם",
    "whatsapp": "💬 WhatsApp",
    "vimeo": "🎬 Vimeo",
    "youtube": "▶️ YouTube",
    "analytics": "📊 אנליטיקס",
    "email_monitor": "📧 ניטור מייל",
    "ai_gemini": "🤖 Gemini AI"
}

# ─── API ────────────────────────────────────────────────
def send(chat_id, text, markup=None):
    data = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if markup:
        data["reply_markup"] = json.dumps(markup)
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{ADMIN_TOKEN}/sendMessage",
            json=data, timeout=10)
        return r.json().get("result", {}).get("message_id")
    except:
        return None

def edit(chat_id, msg_id, text, markup=None):
    data = {"chat_id": chat_id, "message_id": msg_id, "text": text, "parse_mode": "HTML"}
    if markup:
        data["reply_markup"] = json.dumps(markup)
    try:
        requests.post(f"https://api.telegram.org/bot{ADMIN_TOKEN}/editMessageText",
                     json=data, timeout=10)
    except:
        pass

def answer_cb(cb_id):
    try:
        requests.post(f"https://api.telegram.org/bot{ADMIN_TOKEN}/answerCallbackQuery",
                     json={"callback_query_id": cb_id}, timeout=5)
    except:
        pass

# ─── תפריט ראשי ─────────────────────────────────────────
MAIN_MENU = {
    "keyboard": [
        [{"text": "➕ לקוח חדש"}, {"text": "📋 כל הלקוחות"}],
        [{"text": "📊 סטטיסטיקות"}, {"text": "⚙️ הגדרות"}]
    ],
    "resize_keyboard": True
}

def show_main(chat_id):
    total = len(clients)
    active = sum(1 for c in clients.values() if c.get("active"))
    revenue = sum(PACKAGES.get(c.get("package","custom"), {}).get("price", c.get("custom_price",0))
                 for c in clients.values() if c.get("active"))
    send(chat_id,
        f"👑 <b>Admin Panel - עדכוני חב״ד Network</b>\n\n"
        f"👥 לקוחות פעילים: <b>{active}/{total}</b>\n"
        f"💰 הכנסה חודשית: <b>₪{revenue}</b>\n\n"
        f"בחר פעולה:", MAIN_MENU)

# ─── יצירת לקוח חדש ─────────────────────────────────────
def start_new_client(chat_id):
    sessions[chat_id] = {
        "step": "name",
        "data": {}
    }
    send(chat_id, "➕ <b>לקוח חדש</b>\n\nשלח את <b>שם הלקוח/האתר</b>:")

def handle_session(chat_id, text, msg):
    session = sessions.get(chat_id)
    if not session:
        return False
    
    step = session["step"]
    data = session["data"]

    if step == "name":
        data["name"] = text
        session["step"] = "site_url"
        send(chat_id, f"✅ שם: <b>{text}</b>\n\nשלח את <b>כתובת האתר</b>:\n(לדוגמה: https://mysite.co.il)")

    elif step == "site_url":
        data["site_url"] = text.rstrip("/")
        data["wp_url"] = data["site_url"] + "/wp-json/wp/v2"
        session["step"] = "wp_user"
        send(chat_id, f"✅ אתר: <b>{text}</b>\n\nשלח <b>שם משתמש WordPress</b>:")

    elif step == "wp_user":
        data["wp_user"] = text
        session["step"] = "wp_password"
        send(chat_id, "שלח <b>סיסמת WordPress</b> (Application Password):")

    elif step == "wp_password":
        data["wp_password"] = text
        session["step"] = "telegram_token"
        send(chat_id, "שלח את <b>טוקן הבוט</b> של הלקוח (מ-BotFather):")

    elif step == "telegram_token":
        data["telegram_token"] = text
        session["step"] = "channel_id"
        send(chat_id, "שלח את <b>מזהה הערוץ</b> בטלגרם:\n(לדוגמה: -1001234567890)\n\nאו /skip אם אין:")

    elif step == "channel_id":
        data["channel_id"] = "" if text == "/skip" else text
        session["step"] = "site_name"
        send(chat_id, "שלח את <b>שם האתר</b> שיופיע בהודעות:\n(לדוגמה: עדכוני חב״ד)")

    elif step == "site_name":
        data["site_name"] = text
        session["step"] = "gemini_key"
        send(chat_id, "שלח את <b>Gemini API Key</b> של הלקוח:\n\n(כל לקוח צריך key משלו)\nאו /skip לדלג:")

    elif step == "gemini_key":
        data["gemini_key"] = "" if text == "/skip" else text
        session["step"] = "package"
        send(chat_id, "בחר <b>חבילה</b>:", {
            "inline_keyboard": [
                [{"text": "⭐ בסיסי – ₪99/חודש", "callback_data": "pkg_basic"}],
                [{"text": "🌟 מתקדם – ₪199/חודש", "callback_data": "pkg_advanced"}],
                [{"text": "💎 פרימיום – ₪299/חודש", "callback_data": "pkg_premium"}],
                [{"text": "⚙️ מותאם אישית", "callback_data": "pkg_custom"}]
            ]
        })

    elif step == "facebook_token":
        data["fb_token"] = "" if text == "/skip" else text
        session["step"] = "facebook_page_id"
        send(chat_id, "שלח <b>Facebook Page ID</b> (או /skip):")

    elif step == "facebook_page_id":
        data["fb_page_id"] = "" if text == "/skip" else text
        session["step"] = "instagram_id"
        send(chat_id, "שלח <b>Instagram User ID</b> (או /skip):")

    elif step == "instagram_id":
        data["ig_user_id"] = "" if text == "/skip" else text
        session["step"] = "whatsapp_url"
        send(chat_id, "שלח <b>WhatsApp Group ID</b> (או /skip):")

    elif step == "whatsapp_url":
        data["whatsapp_group_id"] = "" if text == "/skip" else text
        session["step"] = "vimeo_token"
        send(chat_id, "שלח <b>Vimeo Token</b> (או /skip):")

    elif step == "vimeo_token":
        data["vimeo_token"] = "" if text == "/skip" else text
        session["step"] = "custom_price"
        send(chat_id, "שלח <b>מחיר חודשי בשקלים</b> (ללא ₪):")

    elif step == "custom_price":
        try:
            data["custom_price"] = int(text)
        except:
            data["custom_price"] = 0
        _finalize_client(chat_id, session)

    return True

def _finalize_client(chat_id, session):
    data = session["data"]
    client_id = f"client_{int(time.time())}"
    
    pkg = data.get("package", "custom")
    package = PACKAGES.get(pkg, PACKAGES["custom"])
    
    client = {
        "id": client_id,
        "name": data.get("name", ""),
        "created": datetime.now().strftime("%d/%m/%Y"),
        "active": True,
        "package": pkg,
        "custom_price": data.get("custom_price", 0),
        "features": data.get("custom_features", package["features"]),
        "config": {
            "TELEGRAM_TOKEN": data.get("telegram_token", ""),
            "WP_URL": data.get("wp_url", ""),
            "WP_SITE_URL": data.get("site_url", ""),
            "WP_USER": data.get("wp_user", ""),
            "WP_PASSWORD": data.get("wp_password", ""),
            "CHANNEL_ID": data.get("channel_id", ""),
            "SITE_NAME": data.get("site_name", ""),
            "GEMINI_API_KEY": data.get("gemini_key", ""),
            "FB_PAGE_TOKEN": data.get("fb_token", ""),
            "FB_PAGE_ID": data.get("fb_page_id", ""),
            "IG_USER_ID": data.get("ig_user_id", ""),
            "WHATSAPP_GROUP_ID": data.get("whatsapp_group_id", ""),
            "VIMEO_TOKEN": data.get("vimeo_token", ""),
        }
    }
    
    clients[client_id] = client
    save_clients(clients)
    del sessions[chat_id]
    
    price = data.get("custom_price", 0) or package.get("price", 0)
    features_list = "\n".join([f"  ✅ {FEATURE_NAMES.get(f, f)}" for f in client["features"]])
    
    send(chat_id, f"""✅ <b>לקוח נוצר בהצלחה!</b>

👤 שם: <b>{client['name']}</b>
📦 חבילה: <b>{package['name']}</b>
💰 מחיר: <b>₪{price}/חודש</b>
🆔 ID: <code>{client_id}</code>

<b>פונקציות:</b>
{features_list}""", {
        "inline_keyboard": [
            [{"text": "📋 הצג Config להעתקה", "callback_data": f"show_config_{client_id}"}],
            [{"text": "✏️ ערוך לקוח", "callback_data": f"edit_client_{client_id}"}],
            [{"text": "🏠 חזור לראשי", "callback_data": "main"}]
        ]
    })

# ─── רשימת לקוחות ───────────────────────────────────────
def show_clients(chat_id):
    if not clients:
        send(chat_id, "📋 אין לקוחות עדיין.", {"inline_keyboard": [[{"text": "➕ לקוח חדש", "callback_data": "new_client"}]]})
        return
    
    keyboard = []
    for cid, c in clients.items():
        status = "🟢" if c.get("active") else "🔴"
        pkg = PACKAGES.get(c.get("package","custom"), {})
        price = c.get("custom_price", 0) or pkg.get("price", 0)
        keyboard.append([{"text": f"{status} {c['name']} – ₪{price}/חודש",
                         "callback_data": f"client_{cid}"}])
    keyboard.append([{"text": "🏠 חזור", "callback_data": "main"}])
    send(chat_id, f"📋 <b>כל הלקוחות ({len(clients)}):</b>", {"inline_keyboard": keyboard})

# ─── פרטי לקוח ──────────────────────────────────────────
def show_client(chat_id, client_id):
    c = clients.get(client_id)
    if not c:
        send(chat_id, "❌ לקוח לא נמצא")
        return
    
    pkg = PACKAGES.get(c.get("package","custom"), {})
    price = c.get("custom_price", 0) or pkg.get("price", 0)
    status = "🟢 פעיל" if c.get("active") else "🔴 מושהה"
    features_list = "\n".join([f"  ✅ {FEATURE_NAMES.get(f, f)}" for f in c.get("features", [])])
    
    send(chat_id, f"""👤 <b>{c['name']}</b>

📦 חבילה: {pkg.get('name','מותאם')}
💰 מחיר: ₪{price}/חודש
📅 נוצר: {c.get('created','')}
סטטוס: {status}

<b>פונקציות:</b>
{features_list}""", {
        "inline_keyboard": [
            [{"text": "📋 הצג Config", "callback_data": f"show_config_{client_id}"},
             {"text": "✏️ ערוך", "callback_data": f"edit_client_{client_id}"}],
            [{"text": "🔧 נהל פונקציות", "callback_data": f"manage_features_{client_id}"}],
            [{"text": "⏸️ השהה" if c.get("active") else "▶️ הפעל",
              "callback_data": f"toggle_client_{client_id}"}],
            [{"text": "🗑️ מחק", "callback_data": f"delete_client_{client_id}"},
             {"text": "↩️ חזור", "callback_data": "list_clients"}]
        ]
    })

def show_config(chat_id, client_id):
    c = clients.get(client_id)
    if not c:
        return
    
    config = c.get("config", {})
    config_text = "\n".join([f"{k}={v}" for k, v in config.items() if v])
    
    send(chat_id, f"📋 <b>Config – {c['name']}</b>\n\nהעתק לRender → Environment:\n\n<code>{config_text}</code>", {
        "inline_keyboard": [[{"text": "↩️ חזור", "callback_data": f"client_{client_id}"}]]
    })

def manage_features(chat_id, client_id):
    c = clients.get(client_id)
    if not c:
        return
    
    active_features = c.get("features", [])
    keyboard = []
    for feat_id, feat_name in FEATURE_NAMES.items():
        is_active = feat_id in active_features
        icon = "✅" if is_active else "❌"
        keyboard.append([{"text": f"{icon} {feat_name}",
                         "callback_data": f"toggle_feature_{client_id}_{feat_id}"}])
    keyboard.append([{"text": "↩️ חזור", "callback_data": f"client_{client_id}"}])
    send(chat_id, f"🔧 <b>ניהול פונקציות – {c['name']}</b>", {"inline_keyboard": keyboard})

# ─── Callbacks ───────────────────────────────────────────
def handle_callback(cb):
    chat_id = cb["message"]["chat"]["id"]
    user_id = str(cb["from"]["id"])
    data = cb["data"]
    answer_cb(cb["id"])

    if user_id != str(ADMIN_ID):
        return

    if data == "main":
        show_main(chat_id)
    elif data == "new_client":
        start_new_client(chat_id)
    elif data == "list_clients":
        show_clients(chat_id)
    elif data.startswith("client_") and not data.startswith("client_id"):
        client_id = data[7:]
        show_client(chat_id, client_id)
    elif data.startswith("show_config_"):
        show_config(chat_id, data[12:])
    elif data.startswith("edit_client_"):
        client_id = data[12:]
        send(chat_id, "✏️ מה לערוך?", {
            "inline_keyboard": [
                [{"text": "💰 מחיר", "callback_data": f"edit_price_{client_id}"},
                 {"text": "📦 חבילה", "callback_data": f"edit_package_{client_id}"}],
                [{"text": "🔑 טוקן בוט", "callback_data": f"edit_token_{client_id}"},
                 {"text": "🌐 כתובת אתר", "callback_data": f"edit_url_{client_id}"}],
                [{"text": "↩️ חזור", "callback_data": f"client_{client_id}"}]
            ]
        })
    elif data.startswith("manage_features_"):
        manage_features(chat_id, data[16:])
    elif data.startswith("toggle_feature_"):
        parts = data[15:].split("_", 1)
        client_id, feat_id = parts[0], parts[1]
        c = clients.get(client_id)
        if c:
            features = c.get("features", [])
            if feat_id in features:
                features.remove(feat_id)
            else:
                features.append(feat_id)
            c["features"] = features
            save_clients(clients)
            manage_features(chat_id, client_id)
    elif data.startswith("toggle_client_"):
        client_id = data[14:]
        c = clients.get(client_id)
        if c:
            c["active"] = not c.get("active", True)
            save_clients(clients)
            show_client(chat_id, client_id)
    elif data.startswith("delete_client_"):
        client_id = data[14:]
        c = clients.get(client_id)
        if c:
            send(chat_id, f"⚠️ למחוק את <b>{c['name']}</b>?", {
                "inline_keyboard": [
                    [{"text": "✅ כן, מחק", "callback_data": f"confirm_delete_{client_id}"},
                     {"text": "❌ ביטול", "callback_data": f"client_{client_id}"}]
                ]
            })
    elif data.startswith("confirm_delete_"):
        client_id = data[15:]
        name = clients.get(client_id, {}).get("name", "")
        del clients[client_id]
        save_clients(clients)
        send(chat_id, f"🗑️ הלקוח <b>{name}</b> נמחק.")
        show_clients(chat_id)
    elif data.startswith("pkg_"):
        pkg = data[4:]
        # מצא session
        session = sessions.get(chat_id)
        if not session:
            return
        session["data"]["package"] = pkg
        if pkg == "custom":
            session["step"] = "facebook_token"
            send(chat_id, "⚙️ <b>הגדרה מותאמת</b>\n\nשלח <b>Facebook Page Token</b> (או /skip):")
        elif pkg in ("advanced", "premium"):
            session["step"] = "facebook_token"
            send(chat_id, f"✅ חבילה: <b>{PACKAGES[pkg]['name']}</b>\n\nשלח <b>Facebook Page Token</b> (או /skip):")
        else:
            # בסיסי – ללא רשתות חברתיות
            _finalize_client(chat_id, session)

# ─── הודעות ─────────────────────────────────────────────
def handle_message(msg):
    chat_id = msg["chat"]["id"]
    user_id = str(msg["from"]["id"])
    text = msg.get("text", "")

    if user_id != str(ADMIN_ID):
        return

    if text == "/start":
        show_main(chat_id)
        return

    if text == "➕ לקוח חדש":
        start_new_client(chat_id)
        return

    if text == "📋 כל הלקוחות":
        show_clients(chat_id)
        return

    if text == "📊 סטטיסטיקות":
        total = len(clients)
        active = sum(1 for c in clients.values() if c.get("active"))
        revenue = sum(
            PACKAGES.get(c.get("package","custom"), {}).get("price", c.get("custom_price",0))
            for c in clients.values() if c.get("active"))
        send(chat_id, f"""📊 <b>סטטיסטיקות</b>

👥 סה״כ לקוחות: <b>{total}</b>
🟢 פעילים: <b>{active}</b>
🔴 מושהים: <b>{total - active}</b>
💰 הכנסה חודשית: <b>₪{revenue}</b>""")
        return

    # טיפול ב-session
    if chat_id in sessions:
        handle_session(chat_id, text, msg)
        return

def run_http():
    from http.server import HTTPServer, BaseHTTPRequestHandler
    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Admin Bot OK")
        def log_message(self, *args): pass
    HTTPServer(("0.0.0.0", int(os.environ.get("PORT", 8080))), H).serve_forever()

def main():
    global offset
    print("🚀 Admin Bot פועל!", flush=True)
    threading.Thread(target=run_http, daemon=True).start()
    while True:
        try:
            resp = requests.get(
                f"https://api.telegram.org/bot{ADMIN_TOKEN}/getUpdates",
                params={"offset": offset, "timeout": 30}, timeout=35)
            if resp.ok:
                for update in resp.json().get("result", []):
                    offset = update["update_id"] + 1
                    if "message" in update:
                        try:
                            handle_message(update["message"])
                        except Exception as e:
                            print(f"שגיאה: {e}", flush=True)
                    elif "callback_query" in update:
                        try:
                            handle_callback(update["callback_query"])
                        except Exception as e:
                            print(f"שגיאה callback: {e}", flush=True)
        except Exception as e:
            print(f"שגיאה כללית: {e}", flush=True)
            time.sleep(5)

if __name__ == "__main__":
    main()
