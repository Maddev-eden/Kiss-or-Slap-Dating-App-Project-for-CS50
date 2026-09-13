import os
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path
from uuid import uuid4

from flask import Flask, flash, redirect, render_template, request, send_from_directory, session, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

# Configuration des dossiers templates et static pour PyInstaller

app = Flask(__name__)

app.config["SECRET_KEY"] = "development-only-change-me"
DATABASE_PATH = Path(__file__).with_name("data.db")
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DATABASE_PATH}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

UPLOAD_FOLDER = Path(app.static_folder) / "uploads"
UPLOAD_FOLDER.mkdir(exist_ok=True)
ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}
CURRENT_USER_ID = 1



def rows(sql, params=None):
	result = db.session.execute(text(sql), params or {})
	return [dict(row) for row in result.mappings()]


def media_url(filename):
	if not filename:
		return url_for("static", filename="logo.png")
	return url_for("uploaded_image", filename=filename)


def current_user_id():
	return session.get("user_id", CURRENT_USER_ID)


def login_required(view):
	@wraps(view)
	def wrapped_view(*args, **kwargs):
		if "user_id" not in session:
			return redirect(url_for("login", next=request.path))
		return view(*args, **kwargs)
	return wrapped_view


@app.context_processor
def shared_navigation():
	return {
		"nav_items": [
			{"key": "home", "label": "Home", "href": url_for("home"), "icon": "fa-house"},
			{"key": "top", "label": "Top", "href": url_for("top"), "icon": "fa-trophy"},
			{"key": "boost", "label": "Boost", "href": url_for("boost"), "icon": "fa-bolt"},
			{"key": "messages", "label": "Messages", "href": url_for("messages"), "icon": "fa-comment-dots"},
			{"key": "account", "label": "Account", "href": url_for("account"), "icon": "fa-user"},
		],
		"logout_url": url_for("logout"),
		"logo_url": url_for("static", filename="logo.png"),
		"media_url": media_url,
	}


@app.get("/media/<path:filename>")
def uploaded_image(filename):
	return send_from_directory(app.static_folder, filename)



















@app.get("/")
@login_required
def home():
    cards = rows("""
            SELECT id, name, age, location, image_url AS image, kisses, slaps
            FROM users
            WHERE id <> :user_id
			AND sex <> (SELECT sex FROM users WHERE id = :user_id)
            AND bucket = (SELECT bucket FROM users WHERE id = :user_id)
            ORDER BY id
        """, {"user_id": current_user_id()})
    for card in cards:
        card["kisses"] = f"{card['kisses']:,}"
        card["slaps"] = f"{card['slaps']:,}"
    return render_template("cards.html", active_page="home", cards=cards)
            #AND id NOT IN (SELECT receiver_id FROM kiss WHERE sender_id = :user_id)
            #AND id NOT IN (SELECT receiver_id FROM slap WHERE sender_id = :user_id)

def static_page(filename):
	return redirect(url_for("static", filename=filename))



























order_type = "kisses"

@app.route("/top", methods=["GET", "POST"])
@login_required
def top():
    # 1. Traitement du formulaire POST (redirection avec le filtre dans l'URL)
    if request.method == "POST":
        order_type = request.form.get("order_type", "kisses")
        return redirect(url_for("top", order_type=order_type))

    # 2. Récupération du filtre depuis l'URL (?order_type=...)
    order_type = request.args.get("order_type", "kisses")

    # Sécurité (Whitelisting) : autorise "kisses", "slaps", "elo"
    if order_type not in ["kisses", "slaps", "elo"]:
        order_type = "kisses"

    # Calcul de l'Elo temporaire actif (uniquement si non expiré)
    # Pour "elo", on additionne 'elo' + 'elo_temp'
    order_column = """
        (elo + CASE
            WHEN temp_boost_expires IS NOT NULL AND temp_boost_expires > CURRENT_TIMESTAMP
            THEN COALESCE(elo_temp, 0)
            ELSE 0
        END)
    """ if order_type == "elo" else order_type

    # Récupération sécurisée du classement
    ordered = rows(f"""
        SELECT name, age, location, image_url AS image, kisses, slaps, elo,
               CASE
                   WHEN temp_boost_expires IS NOT NULL AND temp_boost_expires > CURRENT_TIMESTAMP
                   THEN COALESCE(elo_temp, 0)
                   ELSE 0
               END AS active_elo_temp,
               (elo + CASE
                   WHEN temp_boost_expires IS NOT NULL AND temp_boost_expires > CURRENT_TIMESTAMP
                   THEN COALESCE(elo_temp, 0)
                   ELSE 0
               END) AS effective_elo
        FROM users ORDER BY {order_column} DESC
    """)

    # Construction du Podium (Top 3)
    podium = []
    for i, user in enumerate(ordered[:3]):
        val = user["effective_elo"] if order_type == "elo" else user[order_type]
        formatted_val = f"{val:,}" if isinstance(val, (int, float)) else str(val)
        podium.append({
            "rank": i + 1,
            "name": user["name"],
            "image": user["image"],
            "value": formatted_val
        })

    # Construction du Classement (Reste des utilisateurs)
    leaderboard = []
    for index, user in enumerate(ordered[3:], start=4):
        val = user["effective_elo"] if order_type == "elo" else user[order_type]
        formatted_val = f"{val:,}" if isinstance(val, (int, float)) else str(val)
        leaderboard.append({
            "rank": index,
            "name": user["name"],
            "location": user["location"],
            "age": user["age"],
            "image": user["image"],
            "kisses": f"{user['kisses']:,}",
            "slaps": f"{user['slaps']:,}",
            "elo": user["effective_elo"],  # Elo total (base + temp actif)
            "value": formatted_val
        })

    return render_template(
        "top.html",
        active_page="top",
        podium=podium,
        leaderboard=leaderboard,
        current_order=order_type
    )































@app.get("/boost")
@login_required
def boost():
    boosts = rows("""
        SELECT id, icon, title, description, resource_type AS type, price, action
        FROM boosts ORDER BY id
    """)
    profile = rows("""
        SELECT name, bucket, elo, image_url AS image, dark, love,
               elo_temp, temp_boost_expires, shield_charges, double_edge_expires
        FROM users WHERE id = :user_id
    """, {"user_id": current_user_id()})[0]

    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    # Vérification du statut de chaque boost
    elo_temp_active = bool(
        profile.get("temp_boost_expires") and profile["temp_boost_expires"] > now_str
    )
    shield_active = bool(
        profile.get("shield_charges") and profile["shield_charges"] > 0
    )
    double_edge_active = bool(
        profile.get("double_edge_expires") and profile["double_edge_expires"] > now_str
    )

    # Calcul de l'Elo affiché (ajoute +150 si le boost temp est actif)
    display_elo = profile["elo"] + (profile["elo_temp"] if elo_temp_active else 0)

    # Dictionnaire des états des boosts
    active_boosts = {
        "elo_temp": elo_temp_active,
        "temp_expires": profile.get("temp_boost_expires"),
        "shield_charges": profile.get("shield_charges") or 0,
        "double_edge": double_edge_active,
        "double_edge_expires": profile.get("double_edge_expires")
    }

    return render_template(
        "boost.html",
        profile_name=profile["name"],
        active_page="boost",
        boosts=boosts,
        profile_image=profile["image"],
        potions=profile["love"],
        elixirs=profile["dark"],
        elo=display_elo,
        bucket=profile["bucket"],
        active_boosts=active_boosts
    )





@app.get("/messages")
@login_required
def messages():
    user_id = current_user_id()
    matches = rows("""
        SELECT distinct u.id AS user_id, u.name, u.bucket, u.image_url AS image
        FROM matches m
        JOIN users u ON u.id = CASE WHEN m.sender_id = :current_user THEN m.receiver_id ELSE m.sender_id END
        WHERE m.sender_id = :current_user OR m.receiver_id = :current_user
        ORDER BY m.id
    """, {"current_user": user_id})
    conversations = rows("""
        SELECT c.id, u.id AS contact_id, u.name, u.bucket, u.image_url AS image,
        c.last_message AS message, c.last_message_time AS time, c.unread,
        c.is_online AS online, COUNT(m.id) AS message_count
        FROM conversations c
        JOIN users u ON u.id = CASE WHEN c.sender_id = :current_user THEN c.receiver_id ELSE c.sender_id END
        LEFT JOIN messages m ON m.conversation_id = c.id
        WHERE c.sender_id = :current_user OR c.receiver_id = :current_user
        GROUP BY c.id, u.id
        HAVING NOT EXISTS (
            SELECT 1
            FROM conversations newer
            LEFT JOIN messages newer_messages ON newer_messages.conversation_id = newer.id
            WHERE ((newer.sender_id = :current_user AND newer.receiver_id = u.id)
                OR (newer.sender_id = u.id AND newer.receiver_id = :current_user))
            GROUP BY newer.id
            HAVING COUNT(newer_messages.id) > COUNT(m.id)
                OR (COUNT(newer_messages.id) = COUNT(m.id) AND newer.id > c.id)
        )
        ORDER BY c.last_message_time DESC, c.id DESC
    """, {"current_user": user_id})

    selected_id = request.args.get("conversation_id", type=int)
    selected = None
    if selected_id is not None:
        selected = next((item for item in conversations if item["id"] == selected_id), None)

    chat_messages = []
    if selected:
        chat_messages = rows("""
            SELECT sender_id, receiver_id, body, sent_at
            FROM messages WHERE conversation_id = :conversation_id ORDER BY id
        """, {"conversation_id": selected["id"]})

    return render_template(
        "messages.html",
        active_page="messages",
        matches=matches,
        conversations=conversations,
        selected_conversation=selected,
        chat_messages=chat_messages,
        current_user_id=user_id
    )

























@app.post("/messages/<int:conversation_id>/send")
@login_required
def send_message(conversation_id):
	user_id = current_user_id()
	conversation = rows("""
		SELECT id, sender_id, receiver_id FROM conversations
		WHERE id = :conversation_id
		AND (sender_id = :user_id OR receiver_id = :user_id)
	""", {"conversation_id": conversation_id, "user_id": user_id})
	if not conversation:
		return render_template("error.html", error_code=403, error_title="Conversation unavailable"), 403

	conversation = conversation[0]
	receiver_id = conversation["receiver_id"] if conversation["sender_id"] == user_id else conversation["sender_id"]
	body = request.form.get("body", "").strip()
	if body:
		db.session.execute(text("""
			INSERT INTO messages (conversation_id, sender_id, receiver_id, sender, body, sent_at)
			VALUES (:conversation_id, :sender_id, :receiver_id, :sender, :body, CURRENT_TIMESTAMP)
		"""), {"conversation_id": conversation_id, "sender_id": user_id, "receiver_id": receiver_id, "sender": "me", "body": body})
		db.session.execute(text("""
			UPDATE conversations SET last_message = :body, last_message_time = CURRENT_TIMESTAMP
			WHERE id = :conversation_id
		"""), {"body": body, "conversation_id": conversation_id})
		db.session.commit()
	return redirect(url_for("messages", conversation_id=conversation_id))















@app.get("/profile/<int:user_id>")
@login_required
def profile(user_id):
    user = rows("""
        SELECT id, name, age, location, image_url AS image, profile_handle,
               kisses, slaps, elo, bucket,
               (elo + CASE
                   WHEN temp_boost_expires IS NOT NULL AND temp_boost_expires > CURRENT_TIMESTAMP
                   THEN COALESCE(elo_temp, 0)
                   ELSE 0
               END) AS effective_elo
        FROM users WHERE id = :user_id
    """, {"user_id": user_id})
    if not user:
        return render_template("error.html", error_code=404, error_title="Profile not found"), 404

    profile_data = user[0]
    # On met à jour le champ elo pour qu'il affiche la somme dynamique
    profile_data["elo"] = profile_data["effective_elo"]

    viewer_id = current_user_id()
    is_match = bool(rows("""
        SELECT id FROM matches
        WHERE status = 'matched'
        AND ((sender_id = :viewer_id AND receiver_id = :profile_id)
        OR (sender_id = :profile_id AND receiver_id = :viewer_id))
    """, {"viewer_id": viewer_id, "profile_id": user_id}))

    return render_template("profile.html", active_page="messages", user=profile_data, is_match=is_match)














@app.post("/profile/<int:user_id>/message")
@login_required
def send_profile_message(user_id):
	viewer_id = current_user_id()
	if not rows("""
		SELECT id FROM matches
		WHERE status = 'matched'
		AND ((sender_id = :viewer_id AND receiver_id = :profile_id)
		OR (sender_id = :profile_id AND receiver_id = :viewer_id))
	""", {"viewer_id": viewer_id, "profile_id": user_id}):
		return render_template("error.html", error_code=403, error_title="Match required", error_message="You can only message users after matching."), 403

	body = request.form.get("body", "").strip()
	if not body:
		return redirect(url_for("profile", user_id=user_id))

	conversation = rows("""
		SELECT id FROM conversations
		WHERE (sender_id = :viewer_id AND receiver_id = :profile_id)
		OR (sender_id = :profile_id AND receiver_id = :viewer_id)
		ORDER BY id LIMIT 1
	""", {"viewer_id": viewer_id, "profile_id": user_id})
	if conversation:
		conversation_id = conversation[0]["id"]
	else:
		contact = rows("SELECT name, image_url FROM users WHERE id = :user_id", {"user_id": user_id})[0]
		inserted = db.session.execute(text("""
			INSERT INTO conversations (sender_id, receiver_id, name, image_url, last_message, last_message_time, unread, is_online)
			VALUES (:sender_id, :receiver_id, :name, :image_url, :last_message, :last_message_time, 0, 0)
		"""), {"sender_id": viewer_id, "receiver_id": user_id, "name": contact["name"], "image_url": contact["image_url"], "last_message": body, "last_message_time": "now"})
		conversation_id = inserted.lastrowid

	db.session.execute(text("""
			INSERT INTO messages (conversation_id, sender_id, receiver_id, sender, body, sent_at)
			VALUES (:conversation_id, :sender_id, :receiver_id, :sender, :body, CURRENT_TIMESTAMP)
	"""), {"conversation_id": conversation_id, "sender_id": viewer_id, "receiver_id": user_id, "sender": "me", "body": body})
	db.session.execute(text("UPDATE conversations SET last_message = :body, last_message_time = CURRENT_TIMESTAMP WHERE id = :conversation_id"), {"body": body, "conversation_id": conversation_id})
	db.session.commit()
	# FIX: was `redirect(url_for("messages"))`, which lost the conversation
	# context and (combined with the bug above) hid the message just sent.
	return redirect(url_for("messages", conversation_id=conversation_id))







from datetime import datetime, timedelta










from pathlib import Path
from uuid import uuid4
from functools import wraps
from datetime import datetime, timedelta

from flask import Flask, redirect, render_template, request, send_from_directory, session, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

# ... (gardez tout le début jusqu'à la route @app.get("/account"))

@app.get("/account")
@login_required
def account():
    user_id = current_user_id()
    user_data = rows("SELECT * FROM users WHERE id = :user_id", {"user_id": user_id})
    if not user_data:
        return render_template("error.html", error_code=404, error_title="User not found"), 404

    user = user_data[0]
    settings = [
        {"title": "Name", "description": user.get("name"), "action": "Edit", "target_url": url_for("edit_setting", setting_type="name")},
        {"title": "Password", "description": "••••••••", "action": "Edit", "target_url": url_for("edit_setting", setting_type="password")},
        {"title": "Location", "description": user.get("location"), "action": "Edit", "target_url": url_for("edit_setting", setting_type="location")},
        {"title": "Profile Handle", "description": user.get("profile_handle"), "action": "Edit", "target_url": url_for("edit_setting", setting_type="profile_handle")},
        {"title": "Profile Image", "description": "Update picture", "action": "Edit", "target_url": url_for("edit_setting", setting_type="image")},
    ]

    return render_template(
        "account.html",
        active_page="account",
        profile_name=user.get("name"),
        profile_handle=user.get("profile_handle"),
        profile_image=user.get("image_url"),
        kisses=user.get("kisses", 0),
        slaps=user.get("slaps", 0),
        bucket=user.get("bucket", "unclassed"),
        settings=settings
    )


# --- ROUTE MANQUANTE À AJOUTER ICI ---

DB_COLUMNS = {
    "name": {"col": "name", "type": "text", "title": "Name"},
    "password": {"col": "password_hash", "type": "password", "title": "Password"},
    "location": {"col": "location", "type": "text", "title": "Location"},
    "profile_handle": {"col": "profile_handle", "type": "text", "title": "Profile Handle"},
    "image": {"col": "image_url", "type": "file", "title": "Profile Image"}
}

@app.route("/account/edit/<setting_type>", methods=["GET", "POST"])
@login_required
def edit_setting(setting_type):
    if setting_type not in DB_COLUMNS:
        flash("Setting not found.", "danger")
        return redirect(url_for("account"))

    field_info = DB_COLUMNS[setting_type]
    user_id = current_user_id()

    user_data = rows("SELECT * FROM users WHERE id = :user_id", {"user_id": user_id})
    if not user_data:
        return render_template("error.html", error_code=404, error_title="User not found"), 404

    user = user_data[0]

    if request.method == "POST":
        if field_info["type"] == "file":
            file = request.files.get("value")
            if file and file.filename != "":
                filename = secure_filename(file.filename)
                extension = Path(filename).suffix.lower().lstrip(".")

                if extension in ALLOWED_IMAGE_EXTENSIONS:
                    stored_name = f"{uuid4().hex}.{extension}"
                    file.save(UPLOAD_FOLDER / stored_name)
                    image_path = f"uploads/{stored_name}"

                    db.session.execute(
                        text("UPDATE users SET image_url = :val WHERE id = :user_id"),
                        {"val": image_path, "user_id": user_id}
                    )
                    db.session.commit()
                    flash("Profile image updated!", "success")
                    return redirect(url_for("account"))
                else:
                    flash("Invalid image format.", "danger")
        else:
            new_value = request.form.get("value", "").strip()
            if new_value:
                if setting_type == "password":
                    new_value = generate_password_hash(new_value)

                col_name = field_info["col"]
                db.session.execute(
                    text(f"UPDATE users SET {col_name} = :val WHERE id = :user_id"),
                    {"val": new_value, "user_id": user_id}
                )
                db.session.commit()
                flash(f"{field_info['title']} updated!", "success")
                return redirect(url_for("account"))

    current_value = user.get(field_info["col"], "") if setting_type != "password" else ""

    return render_template(
        "edit_setting.html",
        setting_type=setting_type,
        field_info=field_info,
        current_value=current_value
    )















@app.get("/logout")
def logout():
	session.clear()
	return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
	if request.method == "POST":
		email = request.form.get("email", "").strip().lower()
		password = request.form.get("password", "")
		user = rows("SELECT id, password_hash FROM users WHERE email = :email", {"email": email})
		if not user or not user[0]["password_hash"] or not check_password_hash(user[0]["password_hash"], password):
			return render_template("login.html", error="Email or password is incorrect."), 401
		session.clear()
		session["user_id"] = user[0]["id"]
		next_url = request.args.get("next") or url_for("home")
		return redirect(next_url if next_url.startswith("/") else url_for("home"))
	return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
	if request.method == "POST":
		name = request.form.get("name", "").strip()
		email = request.form.get("email", "").strip().lower()
		sex = request.form.get("sex", "X").upper()
		password = request.form.get("password", "")
		try:
			age = int(request.form.get("age", "0"))
		except ValueError:
			age = 0
		if not name or not email or len(password) < 1 or not 18 <= age <= 99:
			return render_template("register.html", error="Complete all fields. Password must contain at least 8 characters."), 400
		if rows("SELECT id FROM users WHERE email = :email", {"email": email}):
			return render_template("register.html", error="This email is already registered."), 409
		image = request.files.get("image")
		filename = secure_filename(image.filename) if image else ""
		extension = Path(filename).suffix.lower().lstrip(".")
		if not image or not filename or extension not in ALLOWED_IMAGE_EXTENSIONS:
			return render_template("register.html", error="Please choose a valid image file."), 400

		stored_name = f"{uuid4().hex}.{extension}"
		image.save(UPLOAD_FOLDER / stored_name)
		inserted = db.session.execute(text("""
			INSERT INTO users (name,age ,sex ,location, image_url, email, password_hash, profile_handle)
			VALUES (:name,:age ,:sex ,:location, :image_url, :email, :password_hash, :profile_handle)
		"""), {
			"name": name,
			"age": age,
			"sex": sex,
			"location": request.form["city"].strip(),
			"image_url": f"uploads/{stored_name}",
			"email": email,
			"password_hash": generate_password_hash(password),
			"profile_handle": f"@{secure_filename(name).lower()}",
		})
		db.session.commit()
		session["user_id"] = inserted.lastrowid
		return redirect(url_for("home"))
	return render_template("register.html")


@app.errorhandler(404)
def page_not_found(error):
	return render_template("error.html", error_code=404), 404












@app.route("/action/<int:user_id>", methods=["POST"])
@login_required
def handle_action(user_id):
    action_type = request.form.get("action")  # Récupère 'kiss' ou 'slap'
    current_user = current_user_id()

    if action_type == "kiss":
        # Mettre à jour les Kisses et ajouter 100 Love à l'utilisateur ciblé (receiver)
        db.session.execute(
            text("UPDATE users SET kisses = kisses + 1, love = COALESCE(love, 0) + 100 WHERE id = :id"),
            {"id": user_id}
        )
        db.session.execute(
            text("""
                INSERT INTO kiss (sender_id, receiver_id)
                VALUES (:sender, :receiver)
            """),
            {"sender": current_user, "receiver": user_id}
        )

    elif action_type == "slap":
        # Mettre à jour les Slaps et ajouter 100 Dark à l'utilisateur ciblé (receiver)
        db.session.execute(
            text("UPDATE users SET slaps = slaps + 1, dark = COALESCE(dark, 0) + 100 WHERE id = :id"),
            {"id": user_id}
        )
        db.session.execute(
            text("""
                INSERT INTO slap (sender_id, receiver_id)
                VALUES (:sender, :receiver)
            """),
            {"sender": current_user, "receiver": user_id}
        )

    db.session.commit()

    return redirect(url_for("home"))




@app.get("/kiss")
@login_required
def kiss():
    kiss_users = rows("""
        SELECT
            u.id,
            u.name,
            u.age,
            u.location,
            u.image_url AS image,
            u.kisses,
            u.slaps
        FROM kiss k
        JOIN users u ON k.sender_id = u.id
        WHERE k.receiver_id = :receiver_id
        ORDER BY k.created_at DESC
    """, {"receiver_id": current_user_id()})

    for user in kiss_users:
        user["kisses"] = f"{user['kisses']:,}"
        user["slaps"] = f"{user['slaps']:,}"

    return render_template(
        "kiss.html",
        active_page="kisses",
        kisses=kiss_users
    )








@app.post("/match/<int:user_id>")
@login_required
def match_action(user_id):
    action = request.form.get("action")
    current_id = current_user_id()

    # 0. Récupérer l'état des boosts des deux utilisateurs
    current_user_data = rows("SELECT shield_charges, double_edge_expires FROM users WHERE id = :id", {"id": current_id})[0]
    target_user_data = rows("SELECT shield_charges, double_edge_expires FROM users WHERE id = :id", {"id": user_id})[0]

    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    # Vérification si le mode Double Tranchant est actif pour le current_user
    current_double_edge = bool(
        current_user_data.get("double_edge_expires") and current_user_data["double_edge_expires"] > now_str
    )

    if action == "match":
        target_user = rows("""
            SELECT name, image_url
            FROM users
            WHERE id = :target_id
        """, {"target_id": user_id})

        if target_user:
            target_name = target_user[0]["name"]
            target_img = target_user[0]["image_url"]

            db.session.execute(text("""
                DELETE FROM kiss
                WHERE sender_id = :target_id AND receiver_id = :current_id
            """), {"current_id": current_id, "target_id": user_id})

            db.session.execute(text("""
                INSERT INTO matches (sender_id, receiver_id, name, image_url, status, created_at)
                VALUES (:target_id, :current_id, :name, :image_url, 'matched', DATETIME('now'))
            """), {
                "current_id": current_id,
                "target_id": user_id,
                "name": target_name,
                "image_url": target_img
            })

            # Ajout de 1 Kiss et 100 Love à la personne ayant envoyé le kiss initial
            db.session.execute(text("""
                UPDATE users
                SET kisses = kisses + 1,
                    love = COALESCE(love, 0) + 100
                WHERE id = :target_id
            """), {"target_id": user_id})

            # Gain Elo de base (+15). Doublé à +30 si Mode Double Tranchant actif
            elo_gain = 30 if current_double_edge else 15
            db.session.execute(text("""
                UPDATE users
                SET elo = elo + :gain
                WHERE id IN (:current_id, :target_id)
            """), {"gain": elo_gain, "current_id": current_id, "target_id": user_id})

    elif action == "reject":
        db.session.execute(text("""
            DELETE FROM kiss
            WHERE sender_id = :target_id AND receiver_id = :current_id
        """), {"current_id": current_id, "target_id": user_id})

        # --- GESTION DU BOUCLIER ANTI-SLAP ---
        target_shields = target_user_data.get("shield_charges") or 0
        if target_shields > 0:
            # Le bouclier de la cible absorbe la défaite : il perd 1 charge et ne subit ni Slap, ni perte d'Elo, ni gain de Dark
            db.session.execute(text("""
                UPDATE users
                SET shield_charges = shield_charges - 1
                WHERE id = :target_id
            """), {"target_id": user_id})
        else:
            # Perte d'Elo, ajout de +1 Slap et +100 Dark à la personne rejetée
            elo_loss = 60 if current_double_edge else 30
            db.session.execute(text("""
                UPDATE users
                SET slaps = slaps + 1,
                    dark = COALESCE(dark, 0) + 100,
                    elo = MAX(0, elo - :loss)
                WHERE id = :target_id
            """), {"loss": elo_loss, "target_id": user_id})

        # Elo bonus attribué à la personne qui rejette (+5 standard, +10 sous Double Tranchant)
        rejecter_gain = 10 if current_double_edge else 5
        db.session.execute(text("""
            UPDATE users
            SET elo = elo + :gain
            WHERE id = :current_id
        """), {"gain": rejecter_gain, "current_id": current_id})

    db.session.commit()
    return redirect(url_for("kiss"))



























@app.get("/api/refresh-bucket")
@login_required
def bucket():
    from flask import current_app
    # On utilise l'instance globale 'db' définie en haut du fichier
    globals()["db"].session.execute(text("""
        WITH ranked_users AS (
            SELECT id, NTILE(3) OVER (
                PARTITION BY sex
                ORDER BY (
                    elo + CASE
                        WHEN elo_temp IS NOT NULL
                             AND temp_boost_expires IS NOT NULL
                             AND temp_boost_expires > DATETIME('now')
                        THEN elo_temp
                        ELSE 0
                    END
                ) DESC
            ) AS new_bucket
            FROM users
        )
        UPDATE users
        SET bucket = ranked_users.new_bucket
        FROM ranked_users
        WHERE users.id = ranked_users.id
    """))

    globals()["db"].session.commit()
    return {"status": "success", "message": "Buckets updated relative to each gender category"}














#import os
#import sqlite3
#from flask import g

#BASE_DIR = os.path.dirname(os.path.abspath(__file__))
#DATABASE_PATH = os.path.join(BASE_DIR, "data.db")

#def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


#@app.teardown_appcontext
#def close_db(error):
    db = g.pop("db", None)
    if db is not None:
        db.close()











# Assure-toi d'importer tes fonctions de gestion d'utilisateur et de DB
# ex: current_user_id(), get_db_connection()


from datetime import datetime, timedelta


@app.route("/boost/elo-temp", methods=["POST"])
@login_required
def boost_elo_temp():
    user_id = current_user_id()
    cost = 500
    user = rows("SELECT love FROM users WHERE id = :id", {"id": user_id})

    if user and user[0]["love"] >= cost:
        expires_at = (datetime.utcnow() + timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
        db.session.execute(
            text("UPDATE users SET love = love - :cost, elo_temp = 150, temp_boost_expires = :expires WHERE id = :id"),
            {"cost": cost, "expires": expires_at, "id": user_id}
        )
        db.session.commit()
    else:
        flash("Not enough Love Potion.", "danger")

    return redirect(url_for("boost"))


@app.route("/boost/elo-perm", methods=["POST"])
@login_required
def boost_elo_perm():
    user_id = current_user_id()
    cost = 1200
    user = rows("SELECT love FROM users WHERE id = :id", {"id": user_id})

    if user and user[0]["love"] >= cost:
        db.session.execute(
            text("UPDATE users SET love = love - :cost, elo = elo + 50 WHERE id = :id"),
            {"cost": cost, "id": user_id}
        )
        db.session.commit()
    else:
        flash("Not enough Love Potion.", "danger")

    return redirect(url_for("boost"))


@app.route("/boost/shield-slaps", methods=["POST"])
@login_required
def shield_slaps():
    user_id = current_user_id()
    cost = 400
    user = rows("SELECT dark FROM users WHERE id = :id", {"id": user_id})

    if user and user[0]["dark"] >= cost:
        db.session.execute(
            text("UPDATE users SET dark = dark - :cost, shield_charges = COALESCE(shield_charges, 0) + 5 WHERE id = :id"),
            {"cost": cost, "id": user_id}
        )
        db.session.commit()
    else:
        flash("Not enough Dark Elixir.", "danger")

    return redirect(url_for("boost"))


@app.route("/boost/double-edge", methods=["POST"])
@login_required
def double_edge():
    user_id = current_user_id()
    cost = 750
    user = rows("SELECT dark FROM users WHERE id = :id", {"id": user_id})

    if user and user[0]["dark"] >= cost:
        expires_at = (datetime.utcnow() + timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
        db.session.execute(
            text("UPDATE users SET dark = dark - :cost, double_edge_expires = :expires WHERE id = :id"),
            {"cost": cost, "expires": expires_at, "id": user_id}
        )
        db.session.commit()
    else:
        flash("Not enough Dark Elixir.", "danger")

    return redirect(url_for("boost"))



















@app.route("/admin")
@login_required
def admin_panel():
    search_query = request.args.get("search", "").strip()
    sex_filter = request.args.get("sex", "")
    bucket_filter = request.args.get("bucket", "")
    min_elo = request.args.get("min_elo", "")
    max_elo = request.args.get("max_elo", "")
    min_love = request.args.get("min_love", "")
    max_love = request.args.get("max_love", "")
    min_dark = request.args.get("min_dark", "")
    max_dark = request.args.get("max_dark", "")
    sort_by = request.args.get("sort_by", "id")
    order = request.args.get("order", "ASC")

    query = "SELECT * FROM users WHERE 1=1"
    params = {}

    if search_query:
        query += " AND (name LIKE :term OR email LIKE :term OR location LIKE :term OR profile_handle LIKE :term)"
        params["term"] = f"%{search_query}%"

    if sex_filter:
        query += " AND sex = :sex"
        params["sex"] = sex_filter

    if bucket_filter:
        query += " AND bucket = :bucket"
        params["bucket"] = int(bucket_filter)

    if min_elo:
        query += " AND elo >= :min_elo"
        params["min_elo"] = int(min_elo)

    if max_elo:
        query += " AND elo <= :max_elo"
        params["max_elo"] = int(max_elo)

    if min_love:
        query += " AND love >= :min_love"
        params["min_love"] = int(min_love)

    if max_love:
        query += " AND love <= :max_love"
        params["max_love"] = int(max_love)

    if min_dark:
        query += " AND dark >= :min_dark"
        params["min_dark"] = int(min_dark)

    if max_dark:
        query += " AND dark <= :max_dark"
        params["max_dark"] = int(max_dark)

    allowed_sorts = ["id", "name", "age", "location", "kisses", "slaps", "elo", "bucket", "love", "dark"]
    if sort_by not in allowed_sorts:
        sort_by = "id"

    if order.upper() not in ["ASC", "DESC"]:
        order = "ASC"

    query += f" ORDER BY {sort_by} {order}"

    users = rows(query, params)
    columns = list(users[0].keys()) if users else []

    return render_template(
        "admin.html",
        users=users,
        columns=columns,
        search_query=search_query,
        sex_filter=sex_filter,
        bucket_filter=bucket_filter,
        min_elo=min_elo,
        max_elo=max_elo,
        min_love=min_love,
        max_love=max_love,
        min_dark=min_dark,
        max_dark=max_dark,
        sort_by=sort_by,
        order=order,
        total_results=len(users),
    )




# --- LANCEMENT ET COMPATIBILITÉ PYINSTALLER ---





if __name__ == "__main__":
	app.run(debug=True)
