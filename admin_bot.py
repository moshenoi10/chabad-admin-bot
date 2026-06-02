import os, json, time, requests, threading, pickle
from datetime import datetime

ADMIN_TOKEN = os.environ.get("ADMIN_BOT_TOKEN", "")
ADMIN_ID = os.environ.get("ADMIN_ID", "1798097090")
RENDER_API_KEY = os.environ.get("RENDER_API_KEY", "")
CLIENTS_FILE = "clients.pkl"
RENDER_API = "https://api.render.com/v1"
BOT_TEMPLATE_REPO = "moshenoi10/chabad-bot"

# ─── כל הפונקציות האפשריות ─────────────────────────────
ALL_FEATURES = {
    # העלאת תוכן
    "new_article": "✍️ כתבה חדשה (ידנית)",
    "smart_upload": "🤖 העלאה חכמה (AI)",
    "quick_upload": "⚡ העלאה מהירה",
    "mazaltov": "🎉 מזל טוב",
    "email_monitor": "📧 קבלת כתבות ממייל",
    # עריכה וניהול
    "edit_article": "✏️ עריכת כתבה",
    "delete_article": "🗑️ מחיקת כתבה",
    "view_recent": "📋 כתבות אחרונות",
    "drafts": "📝 טיוטות",
    # הפצה
    "telegram_channel": "📢 ערוץ טלגרם",
    "whatsapp": "💬 WhatsApp",
    "facebook": "📘 פייסבוק",
    "instagram": "📸 אינסטגרם",
    "twitter": "🐦 טוויטר",
    # וידאו
    "vimeo": "🎬 Vimeo",
    "youtube": "▶️ YouTube",
    "share_video": "🎥 הפצת וידאו",
    # כלים
    "analytics": "📊 אנליטיקס",
    "watermark": "🖼️ ווטרמארק",
    "story": "📱 סטורי",
    "monthly_report": "📅 דוח חודשי",
    "top_articles": "🏆 כתבות נצפות",
    # ניהול משתמשים
    "user_management": "👥 ניהול משתמשים",
    "settings": "⚙️ הגדרות מערכת",
}

# קבוצות פונקציות לתצוגה מסודרת
FEATURE_GROUPS = {
    "📤 העלאת תוכן": ["new_article", "smart_upload", "quick_upload", "mazaltov", "email_monitor"],
    "✏️ עריכה וניהול": ["edit_article", "delete_article", "view_recent", "drafts"],
    "📢 הפצה": ["telegram_channel", "whatsapp", "facebook", "instagram", "twitter"],
    "🎬 וידאו": ["vimeo", "youtube", "share_video"],
    "🔧 כלים": ["analytics", "watermark", "story", "monthly_report", "top_articles"],
    "⚙️ ניהול": ["user_management", "settings"],
}

# ─── Render API ─────────────────────────────────────────
def render_headers():
    return {"Authorization": "Bearer " + RENDER_API_KEY, "Content-Type": "application/json"}

def render_get_owner_id():
    try:
        resp = requests.get(RENDER_API + "/owners", headers=render_headers(), timeout=10)
        if resp.ok:
            data = resp.json()
            if data:
                return data[0].get("owner", {}).get("id", "")
    except Exception as e:
        print("Render owner error: " + str(e), flush=True)
    return ""

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

def render_create_service(service_name, env_vars):
    try:
        owner_id = render_get_owner_id()
        payload = {
            "type": "web_service",
            "name": service_name,
            "ownerId": owner_id,
            "repo": "https://github.com/" + BOT_TEMPLATE_REPO,
            "branch": "main",
            "plan": "free",
            "region": "frankfurt",
            "runtime": "python",
            "serviceDetails": {
                "buildCommand": "pip install -r requirements.txt",
                "startCommand": "python bot.py",
                "envSpecificDetails": {
                    "buildCommand": "pip install -r requirements.txt",
                    "startCommand": "python bot.py"
                }
            },
            "envVars": [{"key": k, "value": str(v)} for k, v in env_vars.items()]
        }
        resp = requests.post(RENDER_API + "/services", headers=render_headers(),
                            json=payload, timeout=30)
        if resp.ok:
            data = resp.json()
            return data.get("service") or data
        print("Render create error: " + resp.text[:300], flush=True)
    except Exception as e:
        print("Render create error: " + str(e), flush=True)
    return None


def render_get_logs(service_id):
    """קבל לוגים אחרונים"""
    try:
        resp = requests.get(RENDER_API + "/services/" + service_id + "/logs",
                           headers=render_headers(), timeout=10)
        if resp.ok:
            logs = resp.json()
            if isinstance(logs, list):
                return logs[-20:]  # 20 שורות אחרונות
    except Exception as e:
        print("Render logs error: " + str(e), flush=True)
    return []

def render_get_service_status(service_id):
    """קבל סטטוס שירות"""
    try:
        resp = requests.get(RENDER_API + "/services/" + service_id,
                           headers=render_headers(), timeout=10)
        if resp.ok:
            data = resp.json()
            return data.get("serviceDetails", {}).get("status", "unknown")
    except:
        pass
    return "unknown"

def ping_bot(bot_token):
    """בדוק אם הבוט מגיב"""
    try:
        resp = requests.get(
            "https://api.telegram.org/bot" + bot_token + "/getMe",
            timeout=5)
        return resp.ok
    except:
        return False

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

# ─── API טלגרם ──────────────────────────────────────────
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

def edit_msg(chat_id, msg_id, text, markup=None):
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
    revenue = sum(c.get("price", 0) for c in clients.values() if c.get("active"))
    send(chat_id,
        "👑 <b>Admin Panel</b>\n\n"
        "👥 לקוחות פעילים: <b>" + str(active) + "/" + str(total) + "</b>\n"
        "💰 הכנסה חודשית: <b>₪" + str(revenue) + "</b>\n\n"
        "בחר פעולה:", MAIN_MENU)

# ─── שאלון יצירת לקוח ───────────────────────────────────
WIZARD_STEPS = [
    # (step_id, שאלה, מפתח_שמירה, הסבר)
    ("name", "שלח את <b>שם הלקוח/האתר</b>:", "name", ""),
    ("site_url", "שלח את <b>כתובת האתר</b>:", "site_url",
     "📌 לדוגמה: <code>https://mysite.co.il</code>"),
    ("wp_user", "שלח <b>שם משתמש WordPress</b>:", "wp_user",
     "📌 משתמש שיש לו הרשאות עריכה באתר"),
    ("wp_password", "שלח <b>סיסמת WordPress</b>:", "wp_password",
     "📌 צור Application Password:\nוורדפרס → משתמשים → הפרופיל שלי → Application Passwords → הוסף חדש"),
    ("bot_token", "שלח את <b>טוקן הבוט</b> של הלקוח:", "bot_token",
     "📌 צור בוט חדש:\n1. פתח @BotFather בטלגרם\n2. שלח /newbot\n3. בחר שם ו-username\n4. קבל את הטוקן"),
    ("channel_id", "שלח את <b>מזהה ערוץ הטלגרם</b>:", "channel_id",
     "📌 איך מוצאים:\n1. הוסף @userinfobot לערוץ\n2. שלח הודעה בערוץ\n3. הבוט יחזיר את ה-ID\n\nאו שלח /skip אם אין ערוץ"),
    ("site_name", "שלח את <b>שם האתר</b> שיופיע בהודעות:", "site_name",
     "📌 לדוגמה: עדכוני חב\"ד, אתר החדשות שלי וכו'"),
    ("super_admin", "שלח את <b>מזהה המנהל הראשי</b> של הבוט:", "super_admin",
     "📌 איך מוצאים:\nשלח הודעה ל-@userinfobot בטלגרם - הוא יחזיר את ה-ID שלך"),
    ("gemini_key", "שלח <b>Gemini API Key</b>:", "gemini_key",
     "📌 איך יוצרים:\n1. כנס ל-aistudio.google.com\n2. לחץ 'Get API Key'\n3. צור Key חדש (חינמי)\n\nאו /skip לדלג (ללא AI)"),
    ("price", "שלח את <b>המחיר החודשי</b> בשקלים:", "price",
     "📌 הזן מספר בלבד, לדוגמה: 299"),
]

OPTIONAL_STEPS = [
    ("fb_token", "שלח <b>Facebook Page Token</b>:", "fb_token",
     "📌 איך יוצרים:\n1. כנס ל-developers.facebook.com\n2. צור App חדש\n3. הוסף Facebook Login\n4. קבל Page Access Token\n\nאו /skip"),
    ("fb_page_id", "שלח <b>Facebook Page ID</b>:", "fb_page_id",
     "📌 נמצא ב-About של הדף, או דרך Graph API Explorer\nאו /skip"),
    ("ig_user_id", "שלח <b>Instagram User ID</b>:", "ig_user_id",
     "📌 נמצא דרך Graph API Explorer עם הטוקן של פייסבוק\nאו /skip"),
    ("greenapi_id", "שלח <b>Green API Instance ID</b>:", "greenapi_id",
     "📌 כנס ל-green-api.com → צור מופע חינמי → קבל Instance ID\nאו /skip"),
    ("greenapi_token", "שלח <b>Green API Token</b>:", "greenapi_token",
     "📌 נמצא בדף המופע ב-green-api.com\nאו /skip"),
    ("whatsapp_group", "שלח <b>WhatsApp Group ID</b>:", "whatsapp_group",
     "📌 פתח את הקבוצה → שלח /groups לבוט לאחר חיבור Green API\nאו /skip"),
    ("vimeo_token", "שלח <b>Vimeo API Token</b>:", "vimeo_token",
     "📌 כנס ל-developer.vimeo.com → My Apps → New App → Authentication → Generate Token\nאו /skip"),
    ("youtube_client", "שלח <b>YouTube Client ID</b>:", "youtube_client",
     "📌 כנס ל-console.cloud.google.com → APIs → YouTube Data API v3 → Credentials → OAuth Client ID\nאו /skip"),
    ("ga_property", "שלח <b>Google Analytics Property ID</b>:", "ga_property",
     "📌 כנס ל-analytics.google.com → Admin → Property Settings → Property ID\nאו /skip"),
]

def get_wizard_step(session):
    step_idx = session.get("step_idx", 0)
    steps = session.get("steps", [])
    if step_idx < len(steps):
        return steps[step_idx]
    return None

def start_new_client(chat_id):
    sessions[chat_id] = {
        "phase": "wizard",
        "step_idx": 0,
        "steps": WIZARD_STEPS,
        "data": {},
        "features": list(ALL_FEATURES.keys()),  # כל הפונקציות כברירת מחדל
    }
    step = WIZARD_STEPS[0]
    msg = "➕ <b>לקוח חדש</b>\n\nשלב 1/" + str(len(WIZARD_STEPS)) + "\n\n" + step[1]
    if step[3]:
        msg += "\n\n" + step[3]
    send(chat_id, msg)

def handle_wizard(chat_id, text):
    session = sessions.get(chat_id)
    if not session or session.get("phase") != "wizard":
        return False

    step_idx = session["step_idx"]
    steps = session["steps"]

    if step_idx >= len(steps):
        return False

    step = steps[step_idx]
    step_id, question, key, hint = step

    # שמור ערך
    if text == "/skip":
        session["data"][key] = ""
    else:
        if key == "price":
            try:
                session["data"][key] = int(text)
            except:
                send(chat_id, "⚠️ שלח מספר תקין (לדוגמה: 299)")
                return True
        elif key == "site_url":
            session["data"][key] = text.rstrip("/")
        else:
            session["data"][key] = text

    session["step_idx"] += 1
    next_idx = session["step_idx"]

    if next_idx < len(steps):
        next_step = steps[next_idx]
        progress = str(next_idx + 1) + "/" + str(len(steps))
        msg = "✅ נשמר!\n\nשלב " + progress + "\n\n" + next_step[1]
        if next_step[3]:
            msg += "\n\n" + next_step[3]
        if next_step[2] in ("channel_id", "gemini_key"):
            send(chat_id, msg, {
                "inline_keyboard": [[{"text": "⏭️ דלג", "callback_data": "wizard_skip"}]]
            })
        else:
            send(chat_id, msg)
    else:
        # סיום שאלון בסיסי – עבור לאופציונלי
        session["phase"] = "optional"
        session["step_idx"] = 0
        send(chat_id,
            "✅ <b>פרטים בסיסיים נשמרו!</b>\n\n"
            "עכשיו הגדרות אופציונליות לרשתות חברתיות.\n"
            "אפשר לדלג על כל מה שלא רלוונטי.", {
            "inline_keyboard": [
                [{"text": "➡️ המשך להגדרות רשתות", "callback_data": "wizard_optional"}],
                [{"text": "⏭️ דלג הכל – עבור לפונקציות", "callback_data": "wizard_features"}]
            ]
        })

    return True

def handle_optional(chat_id, text):
    session = sessions.get(chat_id)
    if not session or session.get("phase") != "optional":
        return False

    step_idx = session["step_idx"]
    if step_idx >= len(OPTIONAL_STEPS):
        return False

    step = OPTIONAL_STEPS[step_idx]
    step_id, question, key, hint = step

    session["data"][key] = "" if text == "/skip" else text
    session["step_idx"] += 1

    if session["step_idx"] < len(OPTIONAL_STEPS):
        next_step = OPTIONAL_STEPS[session["step_idx"]]
        msg = "✅ נשמר!\n\n" + next_step[1]
        if next_step[3]:
            msg += "\n\n" + next_step[3]
        send(chat_id, msg, {
            "inline_keyboard": [[{"text": "⏭️ דלג", "callback_data": "optional_skip"}]]
        })
    else:
        show_features_setup(chat_id)

    return True

def show_features_setup(chat_id):
    session = sessions.get(chat_id)
    if not session:
        return
    session["phase"] = "features"
    features = session.get("features", list(ALL_FEATURES.keys()))
    send(chat_id,
        "🔧 <b>בחר פונקציות</b>\n\n"
        "סמן את הפונקציות שהלקוח יקבל.\n"
        "כרגע: <b>כל הפונקציות מופעלות</b>\n\n"
        "לחץ על פונקציה להפעלה/כיבוי:", build_features_keyboard(features))

def build_features_keyboard(features):
    keyboard = []
    for group_name, group_features in FEATURE_GROUPS.items():
        keyboard.append([{"text": "─── " + group_name + " ───", "callback_data": "noop"}])
        row = []
        for feat_id in group_features:
            if feat_id in ALL_FEATURES:
                icon = "✅" if feat_id in features else "❌"
                row.append({"text": icon + " " + ALL_FEATURES[feat_id],
                           "callback_data": "sf_" + feat_id})
                if len(row) == 2:
                    keyboard.append(row)
                    row = []
        if row:
            keyboard.append(row)
    keyboard.append([
        {"text": "✅ הפעל הכל", "callback_data": "sf_all_on"},
        {"text": "❌ כבה הכל", "callback_data": "sf_all_off"}
    ])
    keyboard.append([{"text": "➡️ המשך לסיכום", "callback_data": "wizard_summary"}])
    return {"inline_keyboard": keyboard}

def show_wizard_summary(chat_id):
    session = sessions.get(chat_id)
    if not session:
        return
    session["phase"] = "summary"
    data = session["data"]
    features = session.get("features", [])
    features_text = "\n".join(["  ✅ " + ALL_FEATURES.get(f, f) for f in features])
    price = data.get("price", 0)

    msg = "<b>📋 סיכום לקוח חדש:</b>\n\n"
    msg += "👤 שם: <b>" + str(data.get("name","")) + "</b>\n"
    msg += "🌐 אתר: " + str(data.get("site_url","")) + "\n"
    msg += "🤖 בוט: " + ("✅ הוגדר" if data.get("bot_token") else "❌ חסר") + "\n"
    msg += "📢 ערוץ: " + ("✅ " + str(data.get("channel_id","")) if data.get("channel_id") else "❌ לא הוגדר") + "\n"
    msg += "💰 מחיר: <b>₪" + str(price) + "/חודש</b>\n"
    msg += "🤖 Gemini: " + ("✅" if data.get("gemini_key") else "❌") + "\n"
    msg += "📘 FB: " + ("✅" if data.get("fb_token") else "❌") + " | "
    msg += "📸 IG: " + ("✅" if data.get("ig_user_id") else "❌") + " | "
    msg += "💬 WA: " + ("✅" if data.get("greenapi_id") else "❌") + "\n"
    msg += "🎬 Vimeo: " + ("✅" if data.get("vimeo_token") else "❌") + "\n\n"
    msg += "<b>פונקציות (" + str(len(features)) + "):</b>\n" + features_text

    send(chat_id, msg, {
        "inline_keyboard": [
            [{"text": "🚀 צור לקוח ופתח בוט", "callback_data": "wizard_create"}],
            [{"text": "✏️ ערוך פרטים", "callback_data": "wizard_edit"},
             {"text": "🔧 ערוך פונקציות", "callback_data": "wizard_features_edit"}],
            [{"text": "❌ בטל", "callback_data": "wizard_cancel"}]
        ]
    })

def finalize_client(chat_id):
    session = sessions.get(chat_id)
    if not session:
        return
    data = session["data"]
    features = session.get("features", list(ALL_FEATURES.keys()))
    client_id = "client_" + str(int(time.time()))

    config = {
        "TELEGRAM_TOKEN": data.get("bot_token", ""),
        "WP_URL": data.get("site_url", "").rstrip("/") + "/wp-json/wp/v2",
        "WP_SITE_URL": data.get("site_url", ""),
        "WP_USER": data.get("wp_user", ""),
        "WP_PASSWORD": data.get("wp_password", ""),
        "CHANNEL_ID": data.get("channel_id", ""),
        "SITE_NAME": data.get("site_name", ""),
        "SUPER_ADMIN_ID": data.get("super_admin", ADMIN_ID),
        "GEMINI_API_KEY": data.get("gemini_key", ""),
        "FB_PAGE_TOKEN": data.get("fb_token", ""),
        "FB_PAGE_ID": data.get("fb_page_id", ""),
        "IG_USER_ID": data.get("ig_user_id", ""),
        "GREENAPI_ID": data.get("greenapi_id", ""),
        "GREENAPI_TOKEN": data.get("greenapi_token", ""),
        "WHATSAPP_GROUP_ID": data.get("whatsapp_group", ""),
        "VIMEO_TOKEN": data.get("vimeo_token", ""),
        "YOUTUBE_CLIENT_ID": data.get("youtube_client", ""),
        "GA_PROPERTY_ID": data.get("ga_property", ""),
        "FEATURES": get_features_env(features),
    }

    client = {
        "id": client_id,
        "name": data.get("name", ""),
        "created": datetime.now().strftime("%d/%m/%Y"),
        "active": True,
        "price": data.get("price", 0),
        "features": features,
        "config": config,
    }

    clients[client_id] = client
    save_clients(clients)
    del sessions[chat_id]

    msg_id = send(chat_id, "⏳ <b>יוצר בוט...</b>\n\n🔧 מגדיר שירות ב-Render")

    def _create():
        service_name = "bot-" + data.get("name","client").lower().replace(" ","-").replace('"',"")[:20]
        if RENDER_API_KEY:
            svc = render_create_service(service_name, config)
            if svc:
                client["render_service_id"] = svc.get("id", "")
                client["render_url"] = svc.get("serviceDetails", {}).get("url", "") or ""
                clients[client_id] = client
                save_clients(clients)
                edit_msg(chat_id, msg_id,
                    "✅ <b>הבוט נוצר בהצלחה!</b>\n\n"
                    "👤 " + client["name"] + "\n"
                    "🌐 " + client.get("render_url","") + "\n\n"
                    "⏳ הבוט מתחיל לפעול בעוד כמה דקות.\n\n"
                    "📋 <b>הצעד הבא:</b>\n"
                    "לך ל-BotFather → @" + data.get("name","") + "_bot\n"
                    "שלח /setwebhook (לא נדרש, הבוט עובד ב-polling)")
            else:
                edit_msg(chat_id, msg_id,
                    "⚠️ <b>לא הצלחתי ליצור ב-Render אוטומטית.</b>\n\n"
                    "תצור ידנית:\n"
                    "1. render.com → New Web Service\n"
                    "2. חבר ל-repo: " + BOT_TEMPLATE_REPO + "\n"
                    "3. הוסף env vars:")
                config_text = "\n".join([k + "=" + str(v) for k, v in config.items() if v])
                send(chat_id, "<code>" + config_text + "</code>")
        else:
            edit_msg(chat_id, msg_id,
                "✅ <b>לקוח נוצר!</b>\n\n"
                "⚠️ Render API לא מוגדר – תצור ידנית.\n\n"
                "📋 Config:")
            config_text = "\n".join([k + "=" + str(v) for k, v in config.items() if v])
            send(chat_id, "<code>" + config_text + "</code>")

        send(chat_id, "📌 <b>חשוב!</b> אין אפשרות ליצור בוט טלגרם אוטומטית –\n"
            "זה חייב להיעשות דרך @BotFather ידנית.\n"
            "הטוקן שהזנת כבר מוגדר.", {
            "inline_keyboard": [
                [{"text": "📋 הצג Config מלא", "callback_data": "show_config_" + client_id}],
                [{"text": "🔧 נהל פונקציות", "callback_data": "manage_features_" + client_id}],
                [{"text": "🏠 ראשי", "callback_data": "main"}]
            ]
        })

    threading.Thread(target=_create, daemon=True).start()

# ─── ניהול לקוח ─────────────────────────────────────────
def show_clients(chat_id):
    if not clients:
        send(chat_id, "📋 אין לקוחות.", {
            "inline_keyboard": [[{"text": "➕ לקוח חדש", "callback_data": "new_client"}]]
        })
        return
    keyboard = []
    for cid, c in clients.items():
        status = "🟢" if c.get("active") else "🔴"
        keyboard.append([{"text": status + " " + c["name"] + " – ₪" + str(c.get("price",0)) + "/חודש",
                         "callback_data": "client_" + cid}])
    keyboard.append([{"text": "🏠 חזור", "callback_data": "main"}])
    send(chat_id, "📋 <b>לקוחות (" + str(len(clients)) + "):</b>", {"inline_keyboard": keyboard})

def show_client(chat_id, client_id):
    c = clients.get(client_id)
    if not c:
        send(chat_id, "❌ לא נמצא")
        return
    status = "🟢 פעיל" if c.get("active") else "🔴 מושהה"
    render_line = "\n🌐 " + c["render_url"] if c.get("render_url") else ""
    feat_count = len(c.get("features", []))
    send(chat_id,
        "👤 <b>" + c["name"] + "</b>" + render_line + "\n"
        "💰 ₪" + str(c.get("price",0)) + "/חודש | "
        "📅 " + c.get("created","") + "\n"
        "סטטוס: " + status + "\n"
        "🔧 פונקציות: " + str(feat_count) + "/" + str(len(ALL_FEATURES)), {
        "inline_keyboard": [
            [{"text": "📋 Config", "callback_data": "show_config_" + client_id},
             {"text": "🔧 פונקציות", "callback_data": "manage_features_" + client_id}],
            [{"text": "📈 סטטוס", "callback_data": "status_" + client_id},
             {"text": "📋 לוגים", "callback_data": "logs_" + client_id}],
            [{"text": "🔑 עדכן מפתחות", "callback_data": "update_keys_" + client_id},
             {"text": "🔄 Restart", "callback_data": "redeploy_" + client_id}],
            [{"text": "⏸️ השהה" if c.get("active") else "▶️ הפעל",
              "callback_data": "toggle_client_" + client_id},
             {"text": "💰 שנה מחיר", "callback_data": "edit_price_" + client_id}],
            [{"text": "🗑️ מחק", "callback_data": "delete_client_" + client_id},
             {"text": "↩️ חזור", "callback_data": "list_clients"}]
        ]
    })

def show_config(chat_id, client_id):
    c = clients.get(client_id)
    if not c:
        return
    config = c.get("config", {})
    config_text = "\n".join([k + "=" + str(v) for k, v in config.items() if v])
    send(chat_id, "📋 <b>Config – " + c["name"] + "</b>\n\n<code>" + config_text + "</code>", {
        "inline_keyboard": [[{"text": "↩️ חזור", "callback_data": "client_" + client_id}]]
    })

def manage_features(chat_id, client_id):
    c = clients.get(client_id)
    if not c:
        return
    features = c.get("features", [])
    keyboard = []
    for group_name, group_features in FEATURE_GROUPS.items():
        keyboard.append([{"text": "─── " + group_name + " ───", "callback_data": "noop"}])
        row = []
        for feat_id in group_features:
            if feat_id in ALL_FEATURES:
                icon = "✅" if feat_id in features else "❌"
                row.append({"text": icon + " " + ALL_FEATURES[feat_id],
                           "callback_data": "mf_" + client_id + "_" + feat_id})
                if len(row) == 2:
                    keyboard.append(row)
                    row = []
        if row:
            keyboard.append(row)
    keyboard.append([
        {"text": "💾 שמור ועדכן בוט", "callback_data": "mf_save_" + client_id},
        {"text": "↩️ חזור", "callback_data": "client_" + client_id}
    ])
    send(chat_id, "🔧 <b>פונקציות – " + c["name"] + "</b>\n\nלחץ להפעלה/כיבוי:", {"inline_keyboard": keyboard})

# ─── Callbacks ───────────────────────────────────────────
def handle_callback(cb):
    chat_id = cb["message"]["chat"]["id"]
    user_id = str(cb["from"]["id"])
    data = cb["data"]
    answer_cb(cb["id"])

    if user_id != str(ADMIN_ID):
        return

    if data == "noop":
        return
    elif data == "main":
        show_main(chat_id)
    elif data == "new_client":
        start_new_client(chat_id)
    elif data == "list_clients":
        show_clients(chat_id)
    elif data == "wizard_skip":
        session = sessions.get(chat_id)
        if session:
            handle_wizard(chat_id, "/skip")
    elif data == "wizard_optional":
        session = sessions.get(chat_id)
        if session:
            session["phase"] = "optional"
            session["step_idx"] = 0
            step = OPTIONAL_STEPS[0]
            msg = step[1]
            if step[3]:
                msg += "\n\n" + step[3]
            send(chat_id, msg, {
                "inline_keyboard": [[{"text": "⏭️ דלג", "callback_data": "optional_skip"}]]
            })
    elif data == "optional_skip":
        session = sessions.get(chat_id)
        if session:
            handle_optional(chat_id, "/skip")
    elif data == "wizard_features" or data == "wizard_features_edit":
        session = sessions.get(chat_id)
        if session:
            session["phase"] = "features"
            show_features_setup(chat_id)
    elif data.startswith("sf_"):
        # toggle feature during setup
        feat_id = data[3:]
        session = sessions.get(chat_id)
        if not session:
            return
        if feat_id == "all_on":
            session["features"] = list(ALL_FEATURES.keys())
        elif feat_id == "all_off":
            session["features"] = []
        else:
            features = session.get("features", [])
            if feat_id in features:
                features.remove(feat_id)
            else:
                features.append(feat_id)
            session["features"] = features
        # עדכן keyboard
        cb_msg_id = cb["message"]["message_id"]
        edit_msg(chat_id, cb_msg_id,
            "🔧 <b>בחר פונקציות</b>\n\nמופעלות: <b>" + str(len(session.get("features",[]))) + "/" + str(len(ALL_FEATURES)) + "</b>",
            build_features_keyboard(session.get("features", [])))
    elif data == "wizard_summary":
        show_wizard_summary(chat_id)
    elif data == "wizard_create":
        finalize_client(chat_id)
    elif data == "wizard_cancel":
        if chat_id in sessions:
            del sessions[chat_id]
        send(chat_id, "❌ בוטל.", MAIN_MENU)
    elif data.startswith("client_"):
        show_client(chat_id, data[7:])
    elif data.startswith("show_config_"):
        show_config(chat_id, data[12:])
    elif data.startswith("manage_features_"):
        manage_features(chat_id, data[16:])
    elif data.startswith("mf_save_"):
        client_id = data[8:]
        c = clients.get(client_id)
        if c:
            service_id = c.get("render_service_id")
            if service_id and RENDER_API_KEY:
                msg_id = send(chat_id, "⏳ מעדכן ב-Render...")
                def _update(sid=service_id, feats=c["features"], m=msg_id):
                    ok = render_update_env_vars(sid, {"FEATURES": get_features_env(feats)})
                    if ok:
                        render_deploy(sid)
                        edit_msg(chat_id, m, "✅ פונקציות עודכנו ו-Deploy הופעל!")
                    else:
                        edit_msg(chat_id, m, "⚠️ עדכון נכשל – תעדכן ידנית ב-Render")
                threading.Thread(target=_update, daemon=True).start()
            else:
                send(chat_id, "✅ נשמר! (עדכן FEATURES ב-Render ידנית)")
    elif data.startswith("mf_"):
        parts = data[3:].split("_", 1)
        if len(parts) == 2:
            client_id, feat_id = parts
            c = clients.get(client_id)
            if c:
                features = list(c.get("features", []))
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
            new_status = not c.get("active", True)
            c["active"] = new_status
            save_clients(clients)
            service_id = c.get("render_service_id")
            if service_id and RENDER_API_KEY:
                def _toggle(sid=service_id, active=new_status, name=c["name"]):
                    if active:
                        ok = render_resume(sid)
                    else:
                        ok = render_suspend(sid)
                    status = ("✅ הופעל" if active else "⏸️ הושהה") if ok else "⚠️ נכשל"
                    send(chat_id, name + " – " + status)
                threading.Thread(target=_toggle, daemon=True).start()
            else:
                send(chat_id, "✅ עודכן (עצור/הפעל ידנית ב-Render)")
            show_client(chat_id, client_id)
    elif data.startswith("redeploy_"):
        client_id = data[9:]
        c = clients.get(client_id)
        if c:
            service_id = c.get("render_service_id")
            if service_id and RENDER_API_KEY:
                ok = render_deploy(service_id)
                send(chat_id, "✅ Deploy הופעל!" if ok else "❌ נכשל")
            else:
                send(chat_id, "⚠️ אין service_id – תעשה Deploy ידנית ב-Render")
    elif data.startswith("edit_price_"):
        client_id = data[11:]
        sessions[chat_id] = {"phase": "edit_price", "client_id": client_id}
        send(chat_id, "💰 שלח מחיר חדש בשקלים:")

    elif data.startswith("status_"):
        client_id = data[7:]
        c = clients.get(client_id)
        if not c:
            return
        msg_id = send(chat_id, "⏳ בודק סטטוס...")
        def _check(cid=client_id, m=msg_id):
            c = clients.get(cid)
            title = "📈 <b>סטטוס – " + c["name"] + "</b>"
            lines = [title + ""]
            # בדוק בוט טלגרם
            bot_token = c.get("config",{}).get("TELEGRAM_TOKEN","")
            if bot_token:
                alive = ping_bot(bot_token)
                lines.append("🤖 בוט טלגרם: " + ("✅ פעיל" if alive else "❌ לא מגיב"))
            # בדוק Render
            service_id = c.get("render_service_id","")
            if service_id and RENDER_API_KEY:
                status = render_get_service_status(service_id)
                status_map = {"live": "✅ פעיל", "suspended": "⏸️ מושהה",
                             "deploying": "🔄 בהכנה", "failed": "❌ נכשל"}
                lines.append("🖥️ Render: " + status_map.get(status, status))
            else:
                lines.append("🖥️ Render: ⚠️ לא מוגדר")
            # כתובת האתר
            site_url = c.get("config",{}).get("WP_SITE_URL","")
            if site_url:
                try:
                    resp = requests.get(site_url, timeout=5)
                    lines.append("🌐 אתר: " + ("✅ עולה" if resp.ok else "❌ לא עולה"))
                except:
                    lines.append("🌐 אתר: ❌ לא נגיש")
            edit_msg(chat_id, m, "\n".join(lines), {
                "inline_keyboard": [[{"text": "↩️ חזור", "callback_data": "client_" + cid}]]
            })
        threading.Thread(target=_check, daemon=True).start()

    elif data.startswith("logs_"):
        client_id = data[5:]
        c = clients.get(client_id)
        if not c:
            return
        service_id = c.get("render_service_id","")
        if not service_id or not RENDER_API_KEY:
            send(chat_id, "⚠️ אין Render service_id מוגדר ללקוח זה.")
            return
        msg_id = send(chat_id, "⏳ מושך לוגים...")
        def _logs(sid=service_id, m=msg_id, cid=client_id):
            logs = render_get_logs(sid)
            if logs:
                log_text = ""
                for log in logs[-15:]:
                    text = log.get("text","") if isinstance(log, dict) else str(log)
                    log_text += text[:100] + "\n"
                edit_msg(chat_id, m, "📋 <b>לוגים אחרונים:</b>\n\n<code>" + log_text[:3000] + "</code>", {
                    "inline_keyboard": [[{"text": "↩️ חזור", "callback_data": "client_" + cid}]]
                })
            else:
                edit_msg(chat_id, m, "📋 אין לוגים זמינים.", {
                    "inline_keyboard": [[{"text": "↩️ חזור", "callback_data": "client_" + cid}]]
                })
        threading.Thread(target=_logs, daemon=True).start()

    elif data.startswith("update_keys_"):
        client_id = data[12:]
        sessions[chat_id] = {"phase": "update_keys", "client_id": client_id, "new_keys": {}}
        send(chat_id,
            "🔑 <b>עדכון מפתחות API</b>\n\nבחר מה לעדכן:", {
            "inline_keyboard": [
                [{"text": "🤖 Gemini API Key", "callback_data": "uk_gemini_" + client_id}],
                [{"text": "📘 Facebook Token", "callback_data": "uk_fb_" + client_id}],
                [{"text": "💬 Green API", "callback_data": "uk_greenapi_" + client_id}],
                [{"text": "🎬 Vimeo Token", "callback_data": "uk_vimeo_" + client_id}],
                [{"text": "🔑 WP Password", "callback_data": "uk_wp_pass_" + client_id}],
                [{"text": "💾 שמור שינויים", "callback_data": "uk_save_" + client_id}],
                [{"text": "↩️ חזור", "callback_data": "client_" + client_id}]
            ]
        })

    elif data.startswith("uk_gemini_"):
        client_id = data[10:]
        sessions[chat_id] = {"phase": "input_key", "key": "GEMINI_API_KEY", "client_id": client_id}
        send(chat_id, "שלח את ה-Gemini API Key החדש:")
    elif data.startswith("uk_fb_"):
        client_id = data[6:]
        sessions[chat_id] = {"phase": "input_key", "key": "FB_PAGE_TOKEN", "client_id": client_id}
        send(chat_id, "שלח את ה-Facebook Token החדש:")
    elif data.startswith("uk_greenapi_"):
        client_id = data[12:]
        sessions[chat_id] = {"phase": "input_key", "key": "GREENAPI_TOKEN", "client_id": client_id}
        send(chat_id, "שלח את ה-Green API Token החדש:")
    elif data.startswith("uk_vimeo_"):
        client_id = data[9:]
        sessions[chat_id] = {"phase": "input_key", "key": "VIMEO_TOKEN", "client_id": client_id}
        send(chat_id, "שלח את ה-Vimeo Token החדש:")
    elif data.startswith("uk_wp_pass_"):
        client_id = data[11:]
        sessions[chat_id] = {"phase": "input_key", "key": "WP_PASSWORD", "client_id": client_id}
        send(chat_id, "שלח את סיסמת WordPress החדשה:")
    elif data.startswith("uk_save_"):
        client_id = data[8:]
        c = clients.get(client_id)
        session = sessions.get(chat_id, {})
        new_keys = session.get("new_keys", {})
        if not new_keys:
            send(chat_id, "⚠️ לא הוזנו מפתחות חדשים.")
            return
        # עדכן ב-config
        for k, v in new_keys.items():
            c["config"][k] = v
        save_clients(clients)
        # עדכן ב-Render
        service_id = c.get("render_service_id","")
        if service_id and RENDER_API_KEY:
            msg_id = send(chat_id, "⏳ מעדכן ב-Render...")
            def _upd(sid=service_id, keys=new_keys, m=msg_id, cid=client_id):
                ok = render_update_env_vars(sid, keys)
                if ok:
                    render_deploy(sid)
                    edit_msg(chat_id, m, "✅ מפתחות עודכנו ו-Deploy הופעל!")
                else:
                    edit_msg(chat_id, m, "⚠️ עדכון נכשל ב-Render")
                send(chat_id, "↩️", {"inline_keyboard": [[{"text": "חזור ללקוח", "callback_data": "client_" + cid}]]})
            threading.Thread(target=_upd, daemon=True).start()
        else:
            send(chat_id, "✅ נשמר מקומית. עדכן ב-Render ידנית.")
        if chat_id in sessions:
            del sessions[chat_id]


    elif data.startswith("delete_client_"):
        client_id = data[14:]
        c = clients.get(client_id)
        if c:
            send(chat_id, "⚠️ למחוק את <b>" + c["name"] + "</b>?", {
                "inline_keyboard": [
                    [{"text": "✅ כן", "callback_data": "confirm_delete_" + client_id},
                     {"text": "❌ ביטול", "callback_data": "client_" + client_id}]
                ]
            })
    elif data.startswith("confirm_delete_"):
        client_id = data[15:]
        name = clients.get(client_id, {}).get("name", "")
        if client_id in clients:
            del clients[client_id]
            save_clients(clients)
        send(chat_id, "🗑️ <b>" + name + "</b> נמחק.")
        show_clients(chat_id)

# ─── הודעות ─────────────────────────────────────────────
def handle_message(msg):
    chat_id = msg["chat"]["id"]
    user_id = str(msg["from"]["id"])
    text = msg.get("text", "")

    if user_id != str(ADMIN_ID):
        return

    # input_key session
    session = sessions.get(chat_id)
    if session and session.get("phase") == "input_key":
        key = session.get("key","")
        client_id = session.get("client_id","")
        c = clients.get(client_id)
        if c and key:
            session.setdefault("new_keys",{})[key] = text
            send(chat_id, "✅ " + key + " נשמר זמנית. לחץ 'שמור שינויים' לאחר כל העדכונים.", {
                "inline_keyboard": [
                    [{"text": "💾 שמור עכשיו", "callback_data": "uk_save_" + client_id}],
                    [{"text": "✏️ עדכן עוד מפתח", "callback_data": "update_keys_" + client_id}]
                ]
            })
            sessions[chat_id] = {"phase": "update_keys", "client_id": client_id, "new_keys": session.get("new_keys",{})}
        return

    # edit_price session
    session = sessions.get(chat_id)
    if session and session.get("phase") == "edit_price":
        try:
            clients[session["client_id"]]["price"] = int(text)
            save_clients(clients)
            send(chat_id, "✅ מחיר עודכן ל-₪" + text + "/חודש")
            show_client(chat_id, session["client_id"])
        except:
            send(chat_id, "⚠️ שלח מספר תקין")
        del sessions[chat_id]
        return

    # wizard
    if session and session.get("phase") == "wizard":
        handle_wizard(chat_id, text)
        return

    if session and session.get("phase") == "optional":
        handle_optional(chat_id, text)
        return

    if text == "/start":
        show_main(chat_id)
    elif text == "➕ לקוח חדש":
        start_new_client(chat_id)
    elif text == "📋 כל הלקוחות":
        show_clients(chat_id)
    elif text == "📊 סטטיסטיקות":
        total = len(clients)
        active = sum(1 for c in clients.values() if c.get("active"))
        revenue = sum(c.get("price", 0) for c in clients.values() if c.get("active"))
        send(chat_id,
            "📊 <b>סטטיסטיקות</b>\n\n"
            "👥 סה\"כ: <b>" + str(total) + "</b>\n"
            "🟢 פעילים: <b>" + str(active) + "</b>\n"
            "🔴 מושהים: <b>" + str(total - active) + "</b>\n"
            "💰 הכנסה חודשית: <b>₪" + str(revenue) + "</b>")
    else:
        show_main(chat_id)

# ─── init ────────────────────────────────────────────────
def init_chabad_client():
    if "client_chabad" in clients:
        return
    clients["client_chabad"] = {
        "id": "client_chabad",
        "name": "עדכוני חב\"ד",
        "created": datetime.now().strftime("%d/%m/%Y"),
        "active": True,
        "price": 0,
        "features": list(ALL_FEATURES.keys()),
        "is_owner": True,
        "render_url": "https://chabad-bot.onrender.com",
        "config": {
            "WP_SITE_URL": "https://chabadupdates.com",
            "SITE_NAME": "עדכוני חב\"ד",
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
                            print("callback שגיאה: " + str(e), flush=True)
        except Exception as e:
            print("שגיאה כללית: " + str(e), flush=True)
            time.sleep(5)

if __name__ == "__main__":
    main()
