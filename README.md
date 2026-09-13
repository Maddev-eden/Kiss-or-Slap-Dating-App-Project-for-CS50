# Kiss or Slap


#### Video Demo:  <https://youtu.be/Y4YoiIgoHq4?si=5ZvWFAponXNiB75m>

#### Description:

**Kiss or Slap** is an interactive web-based matchmaking and ranking application built with **Flask** and **SQLite**. It combines classic dating app mechanics with gamification elements such as Elo ratings, virtual currencies, and a boost shop.

---

## 🚀 Key Features

* **Matchmaking & Action System (Kiss / Slap):**
  * Browse recommended user profiles.
  * **Kiss**: Express interest and grant *Love Potion* currency to the recipient.
  * **Slap**: Reject a profile and grant *Dark Elixir* currency to the target.
  * **Matches**: When interest is mutual, a private conversation is unlocked.

* **Elo Rating & Bucket System:**
  * Dynamic Elo score system updated based on interactions.
  * Automatic recalculation of tier categories (*Buckets*) by gender for balanced matchmaking.

* **Boost Shop:**
  * **Temporary Elo Boost**: +150 Elo rating for 24 hours.
  * **Permanent Elo Boost**: +50 permanent Elo score.
  * **Anti-Slap Shield**: Blocks up to 5 incoming Slaps without rating loss.
  * **Double-Edged Mode**: Doubles both Elo gains and losses for 24 hours.

* **Real-time Messaging:**
  * Private direct messaging between matched users.

* **Admin Dashboard:**
  * Comprehensive management interface to search, filter, and sort users by Elo rating, currencies (*Love* / *Dark*), gender, and ranks.

## 🔐 Admin Dashboard & Authentication Logic

The administrative dashboard can be accessed directly by navigating to the `/admin` URL path (e.g., `http://127.0.0.1:5000/admin`). This panel displays a comprehensive list of all registered users stored in the SQLite database, along with their associated emails, names, scores, and active boosts. For testing and demonstration purposes, user credentials follow a simple predictable convention: a user's password consists of the first letter of their first name repeated three times (in lowercased). For instance, if a user's name is **Eden**, their password is **`eee`**, and if their name is **Alice**, their password is **`aaa`**. By opening the `/admin` page, you can easily view any user's email address and combine it with this password pattern to log into their account on the application.

---

## 🏗️ General Application Structure & Database Architecture

The overall architecture relies on a centralized Flask back-end that connects directly to the `data.db` SQLite database using Flask-SQLAlchemy. User profiles, authentication credentials, interactive history (Kisses and Slaps), and active item boosts are all synchronized in real time. Pages across the application—including the main card deck, matchmaking views, user settings, and the administrative dashboard—dynamically query and render this data via Jinja2 templates, ensuring seamless data flow across the entire platform.

---

## 🛠️ Tech Stack

* **Back-end:** Python 3, Flask, Flask-SQLAlchemy, Werkzeug
* **Database:** SQLite (`data.db`)
* **Front-end:** HTML5, CSS3, Jinja2, FontAwesome

---

## 📂 Project Structure

```text
project/
├── app.py                 # Core Flask application & API routes
├── data.db                # SQLite database
├── requirements.txt       # Project dependencies
├── static/                # Static assets (styles, logos, images)
│   ├── logo.png
│   ├── styles.css
│   └── uploads/           # User profile picture uploads
└── templates/             # Jinja2 HTML templates
    ├── account.html
    ├── admin.html
    ├── boost.html
    ├── bucket_refresh.html
    ├── cards.html
    ├── edit_setting.html
    ├── error.html
    ├── index.html
    ├── kiss.html
    ├── login.html
    ├── messages.html
    ├── profile.html
    ├── register.html
    ├── sidebar.html
    └── top.html
```

---

## ⚙️ Installation & Setup

### 1. Clone the repository and navigate to the project directory:
```bash
cd project
```

### 2. Install required dependencies:
```bash
pip install -r requirements.txt
```

### 3. Run the application:
```bash
python app.py
```

The application will be accessible at `http://127.0.0.1:5000/`.
