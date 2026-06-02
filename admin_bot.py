import os, json, time, requests, threading, pickle
from datetime import datetime

ADMIN_TOKEN = os.environ.get("ADMIN_BOT_TOKEN", "")
ADMIN_ID = os.environ.get("ADMIN_ID", "1798097090")
RENDER_API_KEY = os.environ.get("RENDER_API_KEY", "")
CLIENTS_FILE = "clients.pkl"
RENDER_API = "https://api.render.com/v1"
BOT_TEMPLATE_REPO = "moshenoi10/chabad-bot"

# ─── Render API ─────────────────────────────────────────
def render_headers():
    return {"Authorization": "Bearer " + RENDER_API_KEY, "Content-Type": "application/json"}

def render_get_owner_id():
    try:
        resp = requests.get(RENDER_API + "/owners", headers=render_headers(), timeout=10)
        if resp.ok and resp.json():
            return resp.json()[0].get("owner", {}).get("id", "")
    except:
        pass
    return ""

def render_list_services():
    try:
        resp = requests.get(RENDER_API + "/services", headers=render_headers(), timeout=10)
        if resp.ok:
            return resp.json()
    except Exception as e:
        print("Render list error: " + str(e), flush=True)
    return []

def render_update_env_vars(service_id, env_vars):
    try:
        updates = [{"key": k, "value": str(v)} for k, v in env_vars.items()]
        resp = requests.put(RENDER_API + "/services/" + service_id + "/env-vars",
                           headers=render_headers(), json=updates, timeout=15)
        return resp.ok
    except Exception as e:
        print("Render env error: " + str(e), flush=True)
        return False

def render_deploy(service_id):
    try:
        resp = requests.post(RENDER_API + "/services/" + service_id + "/deploys",
                            headers=render_headers(), timeout=10)
        return resp.ok
    except:
        return False

def render_suspend(service_id):
    try:
        resp = requests.post(RENDER_API + "/services/" + service_id + "/suspend",
                            headers=render_headers(), timeout=10)
        return resp.ok
    except:
        return False

def render_resume(service_id):
    try:
        resp = requests.post(RENDER_API + "/services/" + service_id + "/resume",
                            headers=render_headers(), timeout=10)
        return resp.ok
    except:
        return False

def render_create_service(client_name, env_vars):
    try:
        service_name = client_name.lower().replace(" ", "-").replace('"', "").replace("'", "")
        owner_id = render_get_owner_id()
        payload = {
            "type": "web_service",
            "name": "bot-" + service_name,
            "ownerId": owner_id,
            "repo": "https://github.com/" + BOT_TEMPLATE_REPO,
            "branch": "main",
            "plan": "free",
            "region": "frankfurt",
            "buildCommand": "pip install -r requirements.txt",
            "startCommand": "python bot.py",
            "envVars": [{"key": k, "value": str(v)} for k, v in env_vars.items()]
        }
        resp = requests.post(RENDER_API + "/services", headers=render_headers(),
                            json=payload, timeout=30)
        if resp.ok:
            data = resp.json()
            return data.get("service") or data
        print("Render create error: " + resp.text[:200], flush=True)
    except Exception as e:
        print("Render create error: " + str(e), flush=True)
    return None

def get_features_env(features):
    return ",".join(features) if features else "all"

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
sessions = {}
offset = 0

# ─── חבילות ────────────────────────────────────────────
PACKAGES = {
    "basic": {"name": "בסיסי", "price": 99,
               "features": ["wordpress", "telegram_channel", "smart_upload", "mazaltov"],
               "description": "העלאת כתבות + ערוץ טלגרם"},
    "advanced": {"name": "מתקדם", "price": 199,
                  "features": ["wordpress", "telegram_channel", "smart_upload", "mazaltov",
                               "facebook", "instagram", "whatsapp"],
                  "description": "+ רשתות חברתיות + WhatsApp"},
    "premium": {"name": "פרימיום", "price": 299,
                 "features": ["wordpress", "telegram_channel", "smart_upload", "mazaltov",
                              "facebook", "instagram", "whatsapp", "vimeo", "youtube",
                              "analytics", "email_monitor", "ai_gemini"],
                 "description": "כל הפונקציות"},
    "custom": {"name": "מותאם אישית", "price": 0, "features": [], "description": "הגדרה ידנית"}
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
        r = requests.post("https://api.telegram.org/bot" + ADMIN_TOKEN + "/sendMessage",
                         json=data, timeout=10)
        return r.json().get("result", {}).get("message_id")
    except:
        return None

def edit(chat_id, msg_id, text, markup=None):
    data = {"chat_id": chat_id, "message_id": msg_id, "text": text, "parse_mode": "HTML"}
    if markup:
        data["reply_markup"] = json.dumps(markup)
    try:
        requests.post("https://api.telegram.org/bot" + ADMIN_TOKEN + "/editMessageText",
                     json=data, timeout=10)
    except:
        pass

def answer_cb(cb_id):
    try:
        requests.post("https://api.telegram.org/bot" + ADMIN_TOKEN + "/answerCallbackQuery",
                     json={"callback_query_id": cb_id}, timeout=5)
    except:
        pass

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
    revenue = sum(PACKAGES.get(c.get("package", "custom"), {}).get("price", c.get("custom_price", 0))
                 for c in clients.values() if c.get("active"))
    send(chat_id,
        "👑 <b>Admin Panel - עדכוני חב\"ד Network</b>\n\n"
        "👥 לקוחות פעילים: <b>" + str(active) + "/" + str(total) + "</b>\n"
        "💰 הכנסה חודשית: <b>₪" + str(revenue) + "</b>\n\n"
        "בחר פעולה:", MAIN_MENU)

# ─── יצירת לקוח חדש ─────────────────────────────────────
def start_new_client(chat_id):
    sessions[chat_id] = {"step": "name", "data": {}}
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
        send(chat_id, "✅ שם: <b>" + text + "</b>\n\nשלח את <b>כתובת האתר</b>:\n(לדוגמה: https://mysite.co.il)")

    elif step == "site_url":
        data["site_url"] = text.rstrip("/")
        data["wp_url"] = data["site_url"] + "/wp-json/wp/v2"
        session["step"] = "wp_user"
        send(chat_id, "✅ אתר: <b>" + text + "</b>\n\nשלח <b>שם משתמש WordPress</b>:")

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
        send(chat_id, "שלח את <b>שם האתר</b> שיופיע בהודעות:")

    elif step == "site_name":
        data["site_name"] = text
        session["step"] = "gemini_key"
        send(chat_id, "שלח <b>Gemini API Key</b> של הלקוח:\n\n(כל לקוח צריך key משלו)\nאו /skip לדלג:")

    elif step == "gemini_key":
        data["gemini_key"] = "" if text == "/skip" else text
        session["step"] = "package"
        send(chat_id, "בחר <b>חבילה</b>:", {
            "inline_keyboard": [
                [{"text": "⭐ בסיסי - ₪99/חודש", "callback_data": "pkg_basic"}],
                [{"text": "🌟 מתקדם - ₪199/חודש", "callback_data": "pkg_advanced"}],
                [{"text": "💎 פרימיום - ₪299/חודש", "callback_data": "pkg_premium"}],
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
        session["step"] = "whatsapp_group"
        send(chat_id, "שלח <b>WhatsApp Group ID</b> (או /skip):")

    elif step == "whatsapp_group":
        data["whatsapp_group_id"] = "" if text == "/skip" else text
        session["step"] = "greenapi_id"
        send(chat_id, "שלח <b>Green API Instance ID</b> (או /skip):")

    elif step == "greenapi_id":
        data["greenapi_id"] = "" if text == "/skip" else text
        session["step"] = "greenapi_token"
        send(chat_id, "שלח <b>Green API Token</b> (או /skip):")

    elif step == "greenapi_token":
        data["greenapi_token"] = "" if text == "/skip" else text
        session["step"] = "vimeo_token"
        send(chat_id, "שלח <b>Vimeo Token</b> (או /skip):")

    elif step == "vimeo_token":
        data["vimeo_token"] = "" if text == "/skip" else text
        session["step"] = "custom_price"
        send(chat_id, "שלח <b>מחיר חודשי בשקלים</b>:")

    elif step == "custom_price":
        try:
            data["custom_price"] = int(text)
        except:
            data["custom_price"] = 0
        _finalize_client(chat_id, session)

    elif step == "edit_price":
        try:
            clients[session["client_id"]]["custom_price"] = int(text)
            save_clients(clients)
            send(chat_id, "✅ מחיר עודכן ל-₪" + text + "/חודש")
            show_client(chat_id, session["client_id"])
        except:
            send(chat_id, "⚠️ שלח מספר תקין")
        del sessions[chat_id]
        return True

    elif step == "edit_token":
        clients[session["client_id"]]["config"]["TELEGRAM_TOKEN"] = text
        save_clients(clients)
        send(chat_id, "✅ טוקן עודכן!")
        show_client(chat_id, session["client_id"])
        del sessions[chat_id]
        return True

    elif step == "edit_url":
        clients[session["client_id"]]["config"]["WP_SITE_URL"] = text.rstrip("/")
        clients[session["client_id"]]["config"]["WP_URL"] = text.rstrip("/") + "/wp-json/wp/v2"
        save_clients(clients)
        send(chat_id, "✅ כתובת אתר עודכנה!")
        show_client(chat_id, session["client_id"])
        del sessions[chat_id]
        return True

    return True

def _finalize_client(chat_id, session):
    data = session["data"]
    client_id = "client_" + str(int(time.time()))
    pkg = data.get("package", "custom")
    package = PACKAGES.get(pkg, PACKAGES["custom"])

    client = {
        "id": client_id,
        "name": data.get("name", ""),
        "created": datetime.now().strftime("%d/%m/%Y"),
        "active": True,
        "package": pkg,
        "custom_price": data.get("custom_price", 0),
        "features": list(package["features"]),
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
            "GREENAPI_ID": data.get("greenapi_id", ""),
            "GREENAPI_TOKEN": data.get("greenapi_token", ""),
            "VIMEO_TOKEN": data.get("vimeo_token", ""),
            "SUPER_ADMIN_ID": ADMIN_ID,
            "FEATURES": get_features_env(list(package["features"]))
        }
    }

    clients[client_id] = client
    save_clients(clients)
    del sessions[chat_id]

    # צור שירות ב-Render אוטומטית
    if RENDER_API_KEY:
        send(chat_id, "⏳ יוצר שירות ב-Render...")
        def _create():
            svc = render_create_service(data.get("name", ""), client["config"])
            if svc:
                client["render_service_id"] = svc.get("id", "")
                client["render_url"] = svc.get("serviceDetails", {}).get("url", "") or svc.get("url", "")
                clients[client_id] = client
                save_clients(clients)
                send(chat_id, "✅ שירות נוצר ב-Render!\n🌐 " + client.get("render_url", ""))
            else:
                send(chat_id, "⚠️ לא הצלחתי ליצור שירות ב-Render. תצור ידנית.")
            _show_client_created(chat_id, client_id)
        threading.Thread(target=_create, daemon=True).start()
        return

    _show_client_created(chat_id, client_id)

def _show_client_created(chat_id, client_id):
    c = clients.get(client_id)
    if not c:
        return
    pkg = PACKAGES.get(c.get("package", "custom"), {})
    price = c.get("custom_price", 0) or pkg.get("price", 0)
    features_list = "\n".join(["  - " + FEATURE_NAMES.get(f, f) for f in c.get("features", [])])
    send(chat_id,
        "✅ <b>לקוח נוצר בהצלחה!</b>\n\n"
        "👤 שם: <b>" + c["name"] + "</b>\n"
        "📦 חבילה: <b>" + pkg.get("name", "מותאם") + "</b>\n"
        "💰 מחיר: <b>₪" + str(price) + "/חודש</b>\n"
        "🆔 ID: <code>" + client_id + "</code>\n\n"
        "<b>פונקציות:</b>\n" + features_list, {
        "inline_keyboard": [
            [{"text": "📋 הצג Config", "callback_data": "show_config_" + client_id}],
            [{"text": "✏️ ערוך לקוח", "callback_data": "edit_client_" + client_id}],
            [{"text": "🏠 חזור לראשי", "callback_data": "main"}]
        ]
    })

# ─── רשימת לקוחות ───────────────────────────────────────
def show_clients(chat_id):
    if not clients:
        send(chat_id, "📋 אין לקוחות עדיין.", {
            "inline_keyboard": [[{"text": "➕ לקוח חדש", "callback_data": "new_client"}]]
        })
        return
    keyboard = []
    for cid, c in clients.items():
        status = "🟢" if c.get("active") else "🔴"
        pkg = PACKAGES.get(c.get("package", "custom"), {})
        price = c.get("custom_price", 0) or pkg.get("price", 0)
        keyboard.append([{"text": status + " " + c["name"] + " - ₪" + str(price) + "/חודש",
                         "callback_data": "client_" + cid}])
    keyboard.append([{"text": "🏠 חזור", "callback_data": "main"}])
    send(chat_id, "📋 <b>כל הלקוחות (" + str(len(clients)) + "):</b>", {"inline_keyboard": keyboard})

def show_client(chat_id, client_id):
    c = clients.get(client_id)
    if not c:
        send(chat_id, "❌ לקוח לא נמצא")
        return
    pkg = PACKAGES.get(c.get("package", "custom"), {})
    price = c.get("custom_price", 0) or pkg.get("price", 0)
    status = "🟢 פעיל" if c.get("active") else "🔴 מושהה"
    features_list = "\n".join(["  - " + FEATURE_NAMES.get(f, f) for f in c.get("features", [])])
    render_url = c.get("render_url", "")
    render_line = "\n🌐 " + render_url if render_url else ""
    send(chat_id,
        "👤 <b>" + c["name"] + "</b>" + render_line + "\n\n"
        "📦 חבילה: " + pkg.get("name", "מותאם") + "\n"
        "💰 מחיר: ₪" + str(price) + "/חודש\n"
        "📅 נוצר: " + c.get("created", "") + "\n"
        "סטטוס: " + status + "\n\n"
        "<b>פונקציות:</b>\n" + features_list, {
        "inline_keyboard": [
            [{"text": "📋 הצג Config", "callback_data": "show_config_" + client_id},
             {"text": "✏️ ערוך", "callback_data": "edit_client_" + client_id}],
            [{"text": "🔧 נהל פונקציות", "callback_data": "manage_features_" + client_id}],
            [{"text": "⏸️ השהה" if c.get("active") else "▶️ הפעל",
              "callback_data": "toggle_client_" + client_id}],
            [{"text": "🗑️ מחק", "callback_data": "delete_client_" + client_id},
             {"text": "↩️ חזור", "callback_data": "list_clients"}]
        ]
    })

def show_config(chat_id, client_id):
    c = clients.get(client_id)
    if not c:
        return
    config = c.get("config", {})
    config_text = "\n".join([k + "=" + v for k, v in config.items() if v])
    send(chat_id,
        "📋 <b>Config - " + c["name"] + "</b>\n\nהעתק ל-Render Environment:\n\n<code>" + config_text + "</code>", {
        "inline_keyboard": [[{"text": "↩️ חזור", "callback_data": "client_" + client_id}]]
    })

def manage_features(chat_id, client_id):
    c = clients.get(client_id)
    if not c:
        return
    active_features = c.get("features", [])
    keyboard = []
    for feat_id, feat_name in FEATURE_NAMES.items():
        icon = "✅" if feat_id in active_features else "❌"
        keyboard.append([{"text": icon + " " + feat_name,
                         "callback_data": "toggle_feature_" + client_id + "_" + feat_id}])
    keyboard.append([{"text": "↩️ חזור", "callback_data": "client_" + client_id}])
    send(chat_id, "🔧 <b>ניהול פונקציות - " + c["name"] + "</b>", {"inline_keyboard": keyboard})

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
    elif data.startswith("client_"):
        show_client(chat_id, data[7:])
    elif data.startswith("show_config_"):
        show_config(chat_id, data[12:])
    elif data.startswith("edit_client_"):
        client_id = data[12:]
        send(chat_id, "✏️ מה לערוך?", {
            "inline_keyboard": [
                [{"text": "💰 מחיר", "callback_data": "edit_price_" + client_id},
                 {"text": "📦 חבילה", "callback_data": "edit_package_" + client_id}],
                [{"text": "🔑 טוקן בוט", "callback_data": "edit_token_" + client_id},
                 {"text": "🌐 כתובת אתר", "callback_data": "edit_url_" + client_id}],
                [{"text": "↩️ חזור", "callback_data": "client_" + client_id}]
            ]
        })
    elif data.startswith("manage_features_"):
        manage_features(chat_id, data[16:])
    elif data.startswith("toggle_feature_"):
        parts = data[15:].split("_", 1)
        client_id, feat_id = parts[0], parts[1]
        c = clients.get(client_id)
        if c:
            features = list(c.get("features", []))
            if feat_id in features:
                features.remove(feat_id)
            else:
                features.append(feat_id)
            c["features"] = features
            save_clients(clients)
            # עדכן ב-Render
            service_id = c.get("render_service_id")
            if service_id and RENDER_API_KEY:
                def _update(sid=service_id, feats=features):
                    render_update_env_vars(sid, {"FEATURES": get_features_env(feats)})
                    render_deploy(sid)
                threading.Thread(target=_update, daemon=True).start()
            manage_features(chat_id, client_id)
    elif data.startswith("toggle_client_"):
        client_id = data[14:]
        c = clients.get(client_id)
        if c:
            new_status = not c.get("active", True)
            c["active"] = new_status
            save_clients(clients)
            service_id = c.get("render_service_id")
            if service_id and RENDER_API_KEY:
                def _toggle(sid=service_id, active=new_status, name=c["name"]):
                    if active:
                        ok = render_resume(sid)
                        send(chat_id, ("✅" if ok else "⚠️") + " " + name + " - הופעל")
                    else:
                        ok = render_suspend(sid)
                        send(chat_id, ("✅" if ok else "⚠️") + " " + name + " - הושהה")
                threading.Thread(target=_toggle, daemon=True).start()
            show_client(chat_id, client_id)
    elif data.startswith("delete_client_"):
        client_id = data[14:]
        c = clients.get(client_id)
        if c:
            send(chat_id, "⚠️ למחוק את <b>" + c["name"] + "</b>?", {
                "inline_keyboard": [
                    [{"text": "✅ כן, מחק", "callback_data": "confirm_delete_" + client_id},
                     {"text": "❌ ביטול", "callback_data": "client_" + client_id}]
                ]
            })
    elif data.startswith("confirm_delete_"):
        client_id = data[15:]
        name = clients.get(client_id, {}).get("name", "")
        if client_id in clients:
            del clients[client_id]
            save_clients(clients)
        send(chat_id, "🗑️ הלקוח <b>" + name + "</b> נמחק.")
        show_clients(chat_id)
    elif data.startswith("edit_price_"):
        client_id = data[11:]
        sessions[chat_id] = {"step": "edit_price", "client_id": client_id}
        send(chat_id, "💰 שלח מחיר חדש בשקלים:")
    elif data.startswith("edit_token_"):
        client_id = data[11:]
        sessions[chat_id] = {"step": "edit_token", "client_id": client_id}
        send(chat_id, "🔑 שלח טוקן בוט חדש:")
    elif data.startswith("edit_url_"):
        client_id = data[9:]
        sessions[chat_id] = {"step": "edit_url", "client_id": client_id}
        send(chat_id, "🌐 שלח כתובת אתר חדשה:")
    elif data.startswith("edit_package_"):
        client_id = data[13:]
        send(chat_id, "📦 בחר חבילה חדשה:", {
            "inline_keyboard": [
                [{"text": "⭐ בסיסי - ₪99", "callback_data": "setpkg_basic_" + client_id}],
                [{"text": "🌟 מתקדם - ₪199", "callback_data": "setpkg_advanced_" + client_id}],
                [{"text": "💎 פרימיום - ₪299", "callback_data": "setpkg_premium_" + client_id}],
            ]
        })
    elif data.startswith("setpkg_"):
        parts = data[7:].split("_", 1)
        pkg, client_id = parts[0], parts[1]
        c = clients.get(client_id)
        if c and pkg in PACKAGES:
            c["package"] = pkg
            c["features"] = list(PACKAGES[pkg]["features"])
            save_clients(clients)
            send(chat_id, "✅ חבילה עודכנה ל-" + PACKAGES[pkg]["name"])
            show_client(chat_id, client_id)
    elif data.startswith("pkg_"):
        pkg = data[4:]
        session = sessions.get(chat_id)
        if not session:
            return
        session["data"]["package"] = pkg
        if pkg in ("advanced", "premium", "custom"):
            session["step"] = "facebook_token"
            send(chat_id, "✅ חבילה: <b>" + PACKAGES.get(pkg, {}).get("name", "") + "</b>\n\nשלח <b>Facebook Page Token</b> (או /skip):")
        else:
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
        revenue = sum(PACKAGES.get(c.get("package", "custom"), {}).get("price", c.get("custom_price", 0))
                     for c in clients.values() if c.get("active"))
        send(chat_id,
            "📊 <b>סטטיסטיקות</b>\n\n"
            "👥 סה\"כ לקוחות: <b>" + str(total) + "</b>\n"
            "🟢 פעילים: <b>" + str(active) + "</b>\n"
            "🔴 מושהים: <b>" + str(total - active) + "</b>\n"
            "💰 הכנסה חודשית: <b>₪" + str(revenue) + "</b>")
        return

    if chat_id in sessions:
        handle_session(chat_id, text, msg)
        return

# ─── init חב״ד ──────────────────────────────────────────
def init_chabad_client():
    if "client_chabad" in clients:
        return
    clients["client_chabad"] = {
        "id": "client_chabad",
        "name": "עדכוני חב\"ד",
        "created": datetime.now().strftime("%d/%m/%Y"),
        "active": True,
        "package": "premium",
        "custom_price": 0,
        "features": list(FEATURE_NAMES.keys()),
        "is_owner": True,
        "render_url": "https://chabad-bot.onrender.com",
        "notes": "לקוח ראשון - הנתונים שמורים ב-Render שלו",
        "config": {
            "WP_SITE_URL": "https://chabadupdates.com",
            "SITE_NAME": "עדכוני חב\"ד",
            "RENDER_SERVICE": "chabad-bot",
        }
    }
    save_clients(clients)
    print("✅ לקוח חבד נוצר", flush=True)

def run_http():
    from http.server import HTTPServer, BaseHTTPRequestHandler
    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Admin Bot OK")
        def log_message(self, *args):
            pass
    HTTPServer(("0.0.0.0", int(os.environ.get("PORT", 8080))), H).serve_forever()

def main():
    global offset
    print("🚀 Admin Bot פועל!", flush=True)
    init_chabad_client()
    threading.Thread(target=run_http, daemon=True).start()
    while True:
        try:
            resp = requests.get(
                "https://api.telegram.org/bot" + ADMIN_TOKEN + "/getUpdates",
                params={"offset": offset, "timeout": 30}, timeout=35)
            if resp.ok:
                for update in resp.json().get("result", []):
                    offset = update["update_id"] + 1
                    if "message" in update:
                        try:
                            handle_message(update["message"])
                        except Exception as e:
                            print("שגיאה: " + str(e), flush=True)
                    elif "callback_query" in update:
                        try:
                            handle_callback(update["callback_query"])
                        except Exception as e:
                            print("שגיאה callback: " + str(e), flush=True)
        except Exception as e:
            print("שגיאה כללית: " + str(e), flush=True)
            time.sleep(5)

if __name__ == "__main__":
    main()
