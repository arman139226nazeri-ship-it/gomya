# gomyab.py
# اجرا محلی: python gomyab.py
# Railway: gunicorn gomyab:app

from flask import Flask, request, redirect, session, flash, render_template_string
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import sqlite3, re, os

app = Flask(__name__)
app.secret_key = "gomyab-gold-secret"
DB = "gomyab.db"
CATEGORIES = ["مدارک", "کیف", "موبایل", "کلید", "حیوان", "سایر"]

def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = db()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT,
        last_name TEXT,
        phone TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        created_at TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS posts(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        post_type TEXT NOT NULL,
        title TEXT NOT NULL,
        public_desc TEXT NOT NULL,
        category TEXT NOT NULL,
        city TEXT NOT NULL,
        area TEXT,
        secret_raw TEXT NOT NULL,
        secret_norm TEXT NOT NULL,
        status TEXT DEFAULT 'open',
        created_at TEXT NOT NULL
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS claims(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER NOT NULL,
        claimer_id INTEGER NOT NULL,
        answer TEXT NOT NULL,
        result TEXT NOT NULL,
        created_at TEXT NOT NULL
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS messages(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER NOT NULL,
        sender_id INTEGER NOT NULL,
        receiver_id INTEGER NOT NULL,
        text TEXT NOT NULL,
        created_at TEXT NOT NULL
    )""")
    conn.commit()
    conn.close()

def norm(t):
    t = (t or "").strip().lower().replace("ي", "ی").replace("ك", "ک")
    return re.sub(r"\s+", " ", t)

def user():
    if "user_id" not in session:
        return None
    conn = db()
    u = conn.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
    conn.close()
    return u

def has_pass(post_id, claimer_id):
    conn = db()
    row = conn.execute(
        """SELECT id FROM claims
           WHERE post_id=? AND claimer_id=? AND result='pass'
           ORDER BY id DESC LIMIT 1""",
        (post_id, claimer_id)
    ).fetchone()
    conn.close()
    return bool(row)

init_db()

BASE = r"""
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>گم‌یاب طلایی</title>
<style>
:root{--bg:#140f0a;--card:#1c160f;--line:#3a2e1d;--gold:#d4a017;--gold2:#f0d48a;--text:#f8f1df;--muted:#b8a88a}
*{box-sizing:border-box}
body{margin:0;font-family:Tahoma,sans-serif;background:radial-gradient(circle at top,#2a2115,#140f0a 55%);color:var(--text);min-height:100vh}
.wrap{max-width:880px;margin:0 auto;padding:16px}
.nav{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0}
.nav a,.btn{background:#2b2217;color:var(--gold2);text-decoration:none;border:1px solid #4a3b24;padding:11px 14px;border-radius:12px;display:inline-block;cursor:pointer}
.btn.primary{background:linear-gradient(135deg,#f0d48a,#b8860b);color:#1a1208;border:none}
.btn.green{background:#166534;color:#fff;border-color:#166534}
.btn.red{background:#7f1d1d;color:#fff;border-color:#7f1d1d}
.btn.gray{background:#3f3f46;color:#fff;border-color:#3f3f46}
.card{background:linear-gradient(180deg,#241c12,#1a140e);border:1px solid var(--line);border-radius:18px;padding:16px;margin-bottom:12px;box-shadow:0 10px 28px rgba(0,0,0,.25)}
input,select,textarea{width:100%;padding:12px;margin:6px 0 10px;border-radius:12px;border:1px solid #4a3b24;background:#120e09;color:var(--text)}
.flash{background:#3a2e1d;color:var(--gold2);padding:10px 12px;border-radius:12px;margin-bottom:10px}
.muted{color:var(--muted);font-size:13px;line-height:1.8}
.tag{display:inline-block;background:#3a2e1d;color:var(--gold2);padding:4px 10px;border-radius:999px;font-size:12px;margin:0 0 6px 4px}
.warn{background:#3b2a12;border:1px solid #92610a;color:#f0d48a;border-radius:12px;padding:12px;margin:8px 0;line-height:1.8}
.ok{background:#0f2e1d;border:1px solid #166534;color:#86efac;border-radius:12px;padding:12px;margin:8px 0}
.bad{background:#3b1212;border:1px solid #7f1d1d;color:#fecaca;border-radius:12px;padding:12px;margin:8px 0}
.msg{background:#120e09;border:1px solid #3a2e1d;padding:10px;border-radius:12px;margin:8px 0}
.me{background:#2b2217;border-color:#6b5428}
h1{color:var(--gold2);margin:0 0 6px}h2,h3{color:var(--gold);margin:0 0 8px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}
@media(max-width:700px){.grid{grid-template-columns:1fr}}
</style>
</head>
<body>
<div class="wrap">
  <div class="card">
    <h1>🔎 گم‌یاب طلایی</h1>
    <div class="muted">آگهی عمومی • راز مخفی • تأیید سیستم • چت پایدار • صندوق پیام</div>
  </div>
  <div class="nav">
    <a href="/">آگهی‌ها</a>
    <a href="/new">ثبت آگهی</a>
    <a href="/my">آگهی‌های من</a>
    <a href="/inbox">پیام‌های من</a>
    {% if u %}
      <a href="/logout">خروج</a>
      <span class="tag">{{u.first_name or 'کاربر'}} {{u.last_name or ''}}</span>
    {% else %}
      <a href="/login">ورود</a>
      <a href="/register">ثبت‌نام</a>
    {% endif %}
  </div>
  {% with messages = get_flashed_messages() %}
    {% for m in messages %}<div class="flash">{{m}}</div>{% endfor %}
  {% endwith %}
  {{body|safe}}
</div>
</body>
</html>
"""

def page(body):
    return render_template_string(BASE, body=body, u=user())

@app.route("/")
def index():
    q = request.args.get("q", "").strip()
    city = request.args.get("city", "").strip()
    category = request.args.get("category", "").strip()
    post_type = request.args.get("post_type", "").strip()
    sql = """SELECT posts.*, users.first_name, users.last_name FROM posts
             JOIN users ON users.id=posts.user_id WHERE posts.status='open'"""
    params = []
    if q:
        sql += " AND (posts.title LIKE ? OR posts.public_desc LIKE ? OR posts.area LIKE ?)"
        params += [f"%{q}%", f"%{q}%", f"%{q}%"]
    if city:
        sql += " AND posts.city LIKE ?"
        params.append(f"%{city}%")
    if category:
        sql += " AND posts.category=?"
        params.append(category)
    if post_type in ("lost", "found"):
        sql += " AND posts.post_type=?"
        params.append(post_type)
    sql += " ORDER BY posts.id DESC"
    conn = db()
    posts = conn.execute(sql, params).fetchall()
    conn.close()
    opts = "".join([f'<option value="{c}" {"selected" if category==c else ""}>{c}</option>' for c in CATEGORIES])
    cards = ""
    for p in posts:
        kind = "گم‌شده" if p["post_type"] == "lost" else "پیداشده"
        name = f'{(p["first_name"] or "")} {(p["last_name"] or "")}'.strip() or "کاربر"
        cards += f"""
        <div class="card">
          <span class="tag">{kind}</span><span class="tag">{p['category']}</span><span class="tag">{p['city']}</span>
          <h3><a href="/post/{p['id']}" style="color:#f0d48a;text-decoration:none">{p['title']}</a></h3>
          <div class="muted">{p['area'] or '-'} | {p['created_at']} | {name}</div>
          <p>{p['public_desc'][:150]}{'...' if len(p['public_desc'])>150 else ''}</p>
        </div>"""
    if not cards:
        cards = '<div class="card">آگهی بازی نیست.</div>'
    body = f"""
    <div class="card"><form method="get">
      <div class="grid">
        <input name="q" value="{q}" placeholder="جستجو">
        <input name="city" value="{city}" placeholder="شهر">
      </div>
      <div class="grid">
        <select name="category"><option value="">همه دسته‌ها</option>{opts}</select>
        <select name="post_type">
          <option value="">همه</option>
          <option value="lost" {"selected" if post_type=="lost" else ""}>گم‌شده</option>
          <option value="found" {"selected" if post_type=="found" else ""}>پیداشده</option>
        </select>
      </div>
      <button class="btn primary" type="submit">فیلتر</button>
    </form></div>{cards}"""
    return page(body)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        first = request.form.get("first_name", "").strip()
        last = request.form.get("last_name", "").strip()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "").strip()
        if not phone or not password:
            flash("موبایل و رمز لازم است")
            return redirect("/register")
        if not re.fullmatch(r"09\d{9}", phone):
            flash("شماره معتبر: 09xxxxxxxxx")
            return redirect("/register")
        conn = db()
        try:
            conn.execute(
                "INSERT INTO users(first_name,last_name,phone,password,created_at) VALUES(?,?,?,?,?)",
                (first, last, phone, generate_password_hash(password), datetime.now().strftime("%Y-%m-%d %H:%M"))
            )
            conn.commit()
            flash("ثبت‌نام موفق")
            return redirect("/login")
        except sqlite3.IntegrityError:
            flash("این موبایل قبلاً ثبت شده")
        finally:
            conn.close()
    body = """
    <div class="card"><h2>ثبت‌نام</h2>
      <div class="muted">فقط موبایل و رمز الزامی است.</div>
      <form method="post">
        <input name="first_name" placeholder="نام (اختیاری)">
        <input name="last_name" placeholder="فامیل (اختیاری)">
        <input name="phone" placeholder="موبایل 09xxxxxxxxx">
        <input name="password" type="password" placeholder="رمز">
        <button class="btn primary" type="submit">ثبت‌نام</button>
      </form></div>"""
    return page(body)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "").strip()
        conn = db()
        row = conn.execute("SELECT * FROM users WHERE phone=?", (phone,)).fetchone()
        conn.close()
        if row and check_password_hash(row["password"], password):
            session["user_id"] = row["id"]
            flash("ورود موفق")
            return redirect("/")
        flash("موبایل یا رمز اشتباه است")
    body = """
    <div class="card"><h2>ورود</h2>
      <form method="post">
        <input name="phone" placeholder="موبایل">
        <input name="password" type="password" placeholder="رمز">
        <button class="btn primary" type="submit">ورود</button>
      </form></div>"""
    return page(body)

@app.route("/logout")
def logout():
    session.clear()
    flash("خارج شدی")
    return redirect("/")

@app.route("/new", methods=["GET", "POST"])
def new_post():
    u = user()
    if not u:
        flash("اول وارد شو")
        return redirect("/login")
    if request.method == "POST":
        post_type = request.form.get("post_type")
        title = request.form.get("title", "").strip()
        public_desc = request.form.get("public_desc", "").strip()
        category = request.form.get("category", "").strip()
        city = request.form.get("city", "").strip()
        area = request.form.get("area", "").strip()
        secret = request.form.get("secret", "").strip()
        if post_type not in ("lost", "found") or not all([title, public_desc, category, city, secret]):
            flash("فیلدهای ضروری ناقص است")
            return redirect("/new")
        if len(secret) < 6:
            flash("راز شناسایی خیلی کوتاه است")
            return redirect("/new")
        conn = db()
        conn.execute(
            """INSERT INTO posts(user_id,post_type,title,public_desc,category,city,area,secret_raw,secret_norm,created_at)
               VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (u["id"], post_type, title, public_desc, category, city, area, secret, norm(secret),
             datetime.now().strftime("%Y-%m-%d %H:%M"))
        )
        conn.commit()
        conn.close()
        flash("آگهی ثبت شد. راز قفل شد و قابل تغییر نیست.")
        return redirect("/")
    cats = "".join([f"<option>{c}</option>" for c in CATEGORIES])
    body = f"""
    <div class="card"><h2>ثبت آگهی</h2>
      <div class="warn">توضیح عمومی برای همه است. راز شناسایی فقط در سیستم می‌ماند و بعد از ثبت تغییر نمی‌کند.</div>
      <form method="post">
        <select name="post_type"><option value="lost">گم‌شده</option><option value="found">پیداشده</option></select>
        <input name="title" placeholder="عنوان عمومی">
        <select name="category">{cats}</select>
        <input name="city" placeholder="شهر">
        <input name="area" placeholder="محله">
        <textarea name="public_desc" rows="4" placeholder="توضیح عمومی"></textarea>
        <textarea name="secret" rows="4" placeholder="راز شناسایی (مخفی)"></textarea>
        <button class="btn primary" type="submit">ثبت و قفل راز</button>
      </form></div>"""
    return page(body)

@app.route("/post/<int:post_id>", methods=["GET", "POST"])
def post_detail(post_id):
    u = user()
    conn = db()
    p = conn.execute(
        """SELECT posts.*, users.first_name, users.last_name FROM posts
           JOIN users ON users.id=posts.user_id WHERE posts.id=?""",
        (post_id,)
    ).fetchone()
    if not p:
        conn.close()
        flash("پیدا نشد")
        return redirect("/")

    claim_result = None
    already_passed = False
    if u and u["id"] != p["user_id"]:
        already_passed = has_pass(post_id, u["id"])

    if request.method == "POST" and u and u["id"] != p["user_id"] and p["status"] == "open" and not already_passed:
        answer = request.form.get("answer", "").strip()
        if answer:
            a = norm(answer)
            s = p["secret_norm"]
            ok = (a == s) or (len(a) >= 10 and a in s) or (len(s) >= 10 and s in a)
            result = "pass" if ok else "fail"
            conn.execute(
                "INSERT INTO claims(post_id,claimer_id,answer,result,created_at) VALUES(?,?,?,?,?)",
                (post_id, u["id"], answer, result, datetime.now().strftime("%Y-%m-%d %H:%M"))
            )
            conn.commit()
            claim_result = result
            if result == "pass":
                already_passed = True

    claims = []
    if u and u["id"] == p["user_id"]:
        claims = conn.execute(
            """SELECT c.*, u.phone, u.first_name, u.id as uid FROM claims c
               JOIN users u ON u.id=c.claimer_id
               WHERE c.post_id=? AND c.result='pass'
               AND c.id IN (
                   SELECT MAX(id) FROM claims WHERE post_id=? AND result='pass' GROUP BY claimer_id
               )
               ORDER BY c.id DESC""",
            (post_id, post_id)
        ).fetchall()
    conn.close()

    kind = "گم‌شده" if p["post_type"] == "lost" else "پیداشده"
    name = f'{(p["first_name"] or "")} {(p["last_name"] or "")}'.strip() or "کاربر"
    body = f"""
    <div class="card">
      <span class="tag">{kind}</span><span class="tag">{p['category']}</span><span class="tag">{p['city']}</span>
      <span class="tag">{"باز" if p["status"]=="open" else "بسته"}</span>
      <h2>{p["title"]}</h2>
      <div class="muted">محله: {p["area"] or "-"} | {p["created_at"]} | {name}</div>
      <p style="line-height:1.9">{p["public_desc"]}</p>
    </div>
    <div class="card">
      <h3>تأیید مالکیت</h3>
      <div class="muted">اگر یک‌بار تأیید شوی، دکمه چت برای همیشه روی این آگهی می‌ماند.</div>
    """
    if claim_result == "pass" or already_passed:
        body += """<div class="ok">✅ شناسایی شما برای این آگهی تأیید شده است.</div>"""
        if u and u["id"] != p["user_id"]:
            body += f'<a class="btn green" href="/chat/{post_id}/{p["user_id"]}">ورود به گفتگو</a> '
            body += f'<a class="btn primary" href="/inbox">پیام‌های من</a>'
    elif claim_result == "fail":
        body += """<div class="bad">❌ اطلاعات کافی/درست نبود.</div>"""

    if u and u["id"] != p["user_id"] and p["status"] == "open" and not already_passed:
        body += f"""
        <form method="post">
          <textarea name="answer" rows="4" placeholder="مشخصات دقیق برای شناسایی..."></textarea>
          <button class="btn primary" type="submit">بررسی توسط سیستم</button>
        </form>"""
    elif not u:
        body += '<div class="muted">برای بررسی، اول <a href="/login" style="color:#f0d48a">ورود</a> کن.</div>'
    elif u and u["id"] == p["user_id"]:
        body += f'<a class="btn red" href="/close/{post_id}">بستن آگهی</a>'
        body += '<h3 style="margin-top:14px">افراد تأییدشده</h3>'
        if claims:
            for c in claims:
                body += f"""<div class="card" style="box-shadow:none">
                  <b>{c['first_name'] or 'کاربر'}</b> | {c['phone']}
                  <div style="margin-top:8px"><a class="btn green" href="/chat/{post_id}/{c['uid']}">باز کردن چت</a></div>
                </div>"""
        else:
            body += '<div class="muted">هنوز کسی تأیید نشده.</div>'
    body += "</div>"
    return page(body)

@app.route("/chat/<int:post_id>/<int:other_id>", methods=["GET", "POST"])
def chat(post_id, other_id):
    u = user()
    if not u:
        return redirect("/login")
    conn = db()
    p = conn.execute("SELECT * FROM posts WHERE id=?", (post_id,)).fetchone()
    other = conn.execute("SELECT * FROM users WHERE id=?", (other_id,)).fetchone()
    if not p or not other:
        conn.close()
        flash("نامعتبر")
        return redirect("/")

    allowed = False
    if u["id"] == p["user_id"] and has_pass(post_id, other_id):
        allowed = True
    if u["id"] != p["user_id"] and has_pass(post_id, u["id"]) and other_id == p["user_id"]:
        allowed = True
    if not allowed:
        conn.close()
        flash("دسترسی چت ندارید")
        return redirect(f"/post/{post_id}")

    if request.method == "POST":
        text = request.form.get("text", "").strip()
        if text:
            conn.execute(
                "INSERT INTO messages(post_id,sender_id,receiver_id,text,created_at) VALUES(?,?,?,?,?)",
                (post_id, u["id"], other_id, text, datetime.now().strftime("%Y-%m-%d %H:%M"))
            )
            conn.commit()

    msgs = conn.execute(
        """SELECT messages.*, users.first_name FROM messages
           JOIN users ON users.id=messages.sender_id
           WHERE post_id=? AND ((sender_id=? AND receiver_id=?) OR (sender_id=? AND receiver_id=?))
           ORDER BY messages.id""",
        (post_id, u["id"], other_id, other_id, u["id"])
    ).fetchall()
    conn.close()

    html = ""
    for m in msgs:
        cls = "me" if m["sender_id"] == u["id"] else ""
        html += f'<div class="msg {cls}"><b>{m["first_name"] or "کاربر"}</b><div class="muted">{m["created_at"]}</div>{m["text"]}</div>'
    body = f"""
    <div class="card">
      <h2>گفتگو: {p['title']}</h2>
      <div class="warn">پیام‌ها ذخیره می‌مانند. از «پیام‌های من» هم برگرد.</div>
      {html or '<div class="muted">هنوز پیام نیست</div>'}
      <form method="post">
        <textarea name="text" rows="3" placeholder="پیام..."></textarea>
        <button class="btn primary" type="submit">ارسال</button>
      </form>
      <div style="margin-top:8px">
        <a class="btn gray" href="/post/{post_id}">صفحه آگهی</a>
        <a class="btn primary" href="/inbox">پیام‌های من</a>
      </div>
    </div>"""
    return page(body)

@app.route("/inbox")
def inbox():
    u = user()
    if not u:
        flash("اول وارد شو")
        return redirect("/login")
    conn = db()
    rows = conn.execute(
        """
        SELECT messages.post_id, posts.title,
               CASE WHEN messages.sender_id=? THEN messages.receiver_id ELSE messages.sender_id END AS other_id,
               users.first_name AS other_name, users.phone AS other_phone,
               MAX(messages.id) AS last_id
        FROM messages
        JOIN posts ON posts.id=messages.post_id
        JOIN users ON users.id = CASE WHEN messages.sender_id=? THEN messages.receiver_id ELSE messages.sender_id END
        WHERE messages.sender_id=? OR messages.receiver_id=?
        GROUP BY messages.post_id, other_id
        ORDER BY last_id DESC
        """,
        (u["id"], u["id"], u["id"], u["id"])
    ).fetchall()

    passes = conn.execute(
        """
        SELECT claims.post_id, posts.title, users.first_name, users.phone, users.id AS other_id
        FROM claims
        JOIN posts ON posts.id=claims.post_id
        JOIN users ON users.id=posts.user_id
        WHERE claims.claimer_id=? AND claims.result='pass'
        """,
        (u["id"],)
    ).fetchall()

    owner_passes = conn.execute(
        """
        SELECT claims.post_id, posts.title, users.first_name, users.phone, users.id AS other_id
        FROM claims
        JOIN posts ON posts.id=claims.post_id
        JOIN users ON users.id=claims.claimer_id
        WHERE posts.user_id=? AND claims.result='pass'
        """,
        (u["id"],)
    ).fetchall()
    conn.close()

    seen = set()
    items = ""
    for r in rows:
        key = (r["post_id"], r["other_id"])
        if key in seen:
            continue
        seen.add(key)
        items += f"""<div class="card"><b>{r['title']}</b>
          <div class="muted">با {r['other_name'] or 'کاربر'} | {r['other_phone']}</div>
          <a class="btn green" href="/chat/{r['post_id']}/{r['other_id']}">باز کردن چت</a></div>"""
    for r in list(passes) + list(owner_passes):
        key = (r["post_id"], r["other_id"])
        if key in seen:
            continue
        seen.add(key)
        items += f"""<div class="card"><b>{r['title']}</b>
          <div class="muted">با {r['first_name'] or 'کاربر'} | {r['phone']} (تأیید شده)</div>
          <a class="btn green" href="/chat/{r['post_id']}/{r['other_id']}">باز کردن چت</a></div>"""
    if not items:
        items = '<div class="card">گفتگویی نیست. اول باید شناسایی تأیید شود.</div>'
    return page(f"<h2>پیام‌های من</h2>{items}")

@app.route("/my")
def my_posts():
    u = user()
    if not u:
        return redirect("/login")
    conn = db()
    posts = conn.execute("SELECT * FROM posts WHERE user_id=? ORDER BY id DESC", (u["id"],)).fetchall()
    conn.close()
    items = ""
    for p in posts:
        items += f"""<div class="card"><span class="tag">{"باز" if p["status"]=="open" else "بسته"}</span>
        <h3><a href="/post/{p['id']}" style="color:#f0d48a;text-decoration:none">{p['title']}</a></h3>
        <div class="muted">راز قفل است</div></div>"""
    return page(f"<h2>آگهی‌های من</h2>{items or '<div class=\"card\">خالی</div>'}")

@app.route("/close/<int:post_id>")
def close_post(post_id):
    u = user()
    if not u:
        return redirect("/login")
    conn = db()
    p = conn.execute("SELECT * FROM posts WHERE id=?", (post_id,)).fetchone()
    if p and p["user_id"] == u["id"]:
        conn.execute("UPDATE posts SET status='closed' WHERE id=?", (post_id,))
        conn.commit()
        flash("بسته شد")
    conn.close()
    return redirect("/my")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("گم‌یاب طلایی: http://127.0.0.1:" + str(port))
    app.run(host="0.0.0.0", port=port, debug=False)