from flask import Flask, render_template, request, redirect, url_for, session, jsonify, make_response
import psycopg2, os, re, uuid, pandas as pd, sys, matplotlib
from psycopg2 import pool, errors
from datetime import datetime ;from flask_sqlalchemy import SQLAlchemy
from streamlit import context
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import io, base64
import os, matplotlib
import seaborn as sns
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import dns.resolver
import logging
logging.basicConfig(level=logging.DEBUG)
import logging
logging.basicConfig(level=logging.DEBUG)

from flask import make_response
# Point Flask to "Desktop" instead of "templates"
app = Flask(__name__,
            template_folder=os.path.join(os.path.dirname(__file__),
                                         "C:\\Users\\Administrator\\Desktop\\Year 4\\4.2\\project 3 4\\Tajirisha Codespace\\Desktop\\"))
app.secret_key = "tajirisha_secret"
#BASE OF EVERYTHING IS HERE

#END BASE

sns.set_theme(style="whitegrid", palette="viridis")
sender_email = os.getenv("EMAIL_USER")       # e.g., your Gmail address
sender_password = "mblioqnacjybdmif"    # e.g., your Gmail app password

def domain_has_mx(domain):
    try:
        dns.resolver.resolve(domain, 'MX')
        return True
    except Exception:
        return False

def send_nudge_email(to_email, subject, goals=None, context=None):
    """
    Send a personalized nudge email via Gmail SMTP.
    Handles savings goals and password change separately.
    """
    if not sender_email or not sender_password:
        raise ValueError("Email credentials not set in environment variables.")

    # Case A: Password change context
    if context == "password_change":
        body = (
            "Hello!\n\n"
            "This is a quick confirmation that your password has been updated successfully.\n\n"
            "🔒 Security tips:\n"
            "- Avoid reusing old passwords.\n"
            "- Keep your new password private.\n"
            "- Consider enabling two-factor authentication if available.\n\n"
            "Thank you for keeping your account secure!"
        )

    # Case B: No savings goals yet
    elif not goals:
        subject = "Set Your First Savings Goal Today!"
        body = (
            "Hello!\n\n"
            "It looks like you haven’t set any savings goals yet. "
            "Creating your first goal is a powerful step toward building financial confidence and momentum.\n\n"
            "✨ Why start now?\n"
            "- Goals give you a clear target to work toward.\n"
            "- Even small milestones (like an Emergency Fund) help you stay consistent.\n"
            "- Tracking progress keeps you motivated and accountable.\n\n"
            "💡 Tip: Begin with something simple and achievable, such as:\n"
            "- Emergency Fund (e.g., save 10,000 by December)\n"
            "- Education Fund\n"
            "- A personal purchase (like a laptop or phone)\n\n"
            "👉 Click here to create your first goal: http://127.0.0.1:5000/create-goal\n\n"
            "Take the first step today — your future self will thank you!"
        )

    # Case C: Goals exist
    else:
        body_lines = []
        recommendations = []
        for category, current, target, deadline in goals:
            progress = round((current / target) * 100, 1)
            body_lines.append(
                f"Goal '{category}': {progress}% complete ({current}/{target}). Deadline: {deadline}"
            )

            if progress < 50:
                recommendations.append(f"Consider increasing your monthly savings for '{category}' to accelerate progress.")
            elif 50 <= progress < 90:
                recommendations.append(f"You're on track with '{category}'. A small boost could help you finish sooner.")
            else:
                recommendations.append(f"Excellent work on '{category}'! Stay consistent to reach 100%.")

        body = (
            "Hello!\n\nHere’s your current savings progress:\n\n"
            + "\n".join(body_lines)
            + "\n\nRecommendations:\n"
            + "\n".join(recommendations)
            + "\n\nKeep going — you’re making great strides!"
        )

    # Create and send the email
    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.set_debuglevel(1)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        print(f"Nudge email sent successfully to {to_email}.")
    except Exception as e:
        print("Error sending nudge email:", e)

def is_valid_email(email):
    # Basic regex for email format
    pattern = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
    if not re.match(pattern, email):
        return False

    # Block common fake/test domains
    blocked_domains = {"example.com", "test.com", "fake.com"}
    domain = email.split("@")[-1].lower()
    if domain in blocked_domains:
        return False

    return True
print("EMAIL_USER:", os.getenv("EMAIL_USER"))
print("Email_pASS length:",  "mblioqnacjybdmif")


# Add parent directory to path so we can import cvs module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))



# ---------------- DATABASE CONNECTION POOL ---------------- #
db_pool = psycopg2.pool.SimpleConnectionPool(
    minconn=1,
    maxconn=20,
    dbname="tajirisha_db",
    user="postgres",          # your postgres username
    password="4959@SU",       # replace with your actual password
    host="localhost",
    port="5432"
)

# ---------------- PASSWORD VALIDATION ---------------- #
def is_strong_password(password):
    """Validates that a password is strong."""
    return (
        len(password) >= 8 and
        re.search(r"[A-Z]", password) and
        re.search(r"[a-z]", password) and
        re.search(r"[0-9]", password) and
        re.search(r"[^A-Za-z0-9]", password)
    )

# ---------------- TEARDOWN LOGIC ---------------- #
@app.teardown_appcontext
def close_connection(exception):
    """Return any checked-out connections to the pool at the end of each request."""
    try:
        conn = getattr(session, "_db_conn", None)
        if conn:
            db_pool.putconn(conn)
            session._db_conn = None
    except Exception:
        pass

def get_conn():
    """Borrow a connection from the pool, ensuring it's alive."""
    conn = db_pool.getconn()
    try:
        # Run a simple test query to check if connection is alive
        with conn.cursor() as cur:
            cur.execute("SELECT 1;")
    except Exception:
        # If the connection is broken, discard and replace it
        db_pool.putconn(conn, close=True)
        conn = db_pool.getconn()
    # Store connection in session for teardown
    session._db_conn = conn
    return conn
#---------------- END OF DB SETUP ---------------- #
#----------------HELPER FUNCTIONS----------------#
def log_event(user_id, portfolio_id, event_type, description):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO "EventLogs" (event_id, user_id, portfolio_id, event_type, description, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (str(uuid.uuid4()), user_id, portfolio_id, event_type, description, datetime.now()))
        conn.commit()
        cur.close()
    finally:
        db_pool.putconn(conn)
#---------------- END OF HELPER FUNCTIONS ----------------#
# ---------------- ROUTES ---------------- #
@app.route("/")
def home():
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT user_id
                FROM "Users"
                WHERE email=%s AND password_hash = crypt(%s, password_hash)
            """, (email, password))
            user = cur.fetchone()
            cur.close()
            conn.commit()
        except Exception as e:
            conn.rollback()
            print("Error during login:", e)
            return render_template("Desktop_Login.html", error="Login failed. Please try again.", register=False)

        if user:
            session["user_id"] = user[0]

            # Check if portfolio exists
            conn = get_conn()
            try:
                cur = conn.cursor()
                cur.execute("""SELECT portfolio_id FROM "Portfolios" WHERE user_id=%s""", (session["user_id"],))
                portfolio_row = cur.fetchone()
                cur.close()
                conn.commit()
            finally:
                db_pool.putconn(conn)
            
            portfolio_id = portfolio_row[0] if portfolio_row else None
            log_event(session["user_id"], portfolio_id, "Login", "User logged in successfully")

            if portfolio_row:
                return redirect(url_for("dashboard"))
            else:
                return redirect(url_for("onboarding_step1"))
        else:
            log_event(None, None, "FailedLogin", f"Failed login attempt with email: {email}")
            return render_template("Desktop_Login.html", error="Invalid email or password.", register=False)

    return render_template("Desktop_Login.html", register=False)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        year = request.form["year_of_study"]
        university = request.form["university"]


        if not is_strong_password(password):
            return render_template(
                "Desktop_Login.html",
                error="Password must be at least 8 characters and include uppercase, lowercase, number, and special character.",
                register=True
            )
        if not is_valid_email(email):
            return render_template("Desktop_Login.html", error="Please use a valid email address.", register=True)
        domain = email.split("@")[-1].lower()
        if not domain_has_mx(domain):
            return render_template("Desktop_Login.html", error="Email domain is not valid or cannot receive mail.")


        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO "Users" (user_id, email, password_hash, year_of_study, university)
                VALUES (gen_random_uuid(), %s, crypt(%s, gen_salt('bf')), %s, %s)
                RETURNING user_id
            """, (email, password, year, university))
            new_user_id = cur.fetchone()[0]
            conn.commit()
            cur.close()

            # Store user in session and redirect to onboarding step 1
            session["user_id"] = new_user_id
            log_event(new_user_id, None, "Registration",
                    f"User registered with {request.form['university']}, Year {year}")

            return redirect(url_for("onboarding_step1"))

        except errors.UniqueViolation:
            conn.rollback()
            # Friendly message instead of crash
            return render_template(
                "Desktop_Login.html",
                error="This email is already registered. Please log in instead.",
                register=True
            )
        except Exception as e:
            conn.rollback()
            print("Error during registration:", e)
            return render_template(
                "Desktop_Login.html",
                error="Registration failed. Please try again.",
                register=True
            )
        finally:
            db_pool.putconn(conn)

    return render_template("Desktop_Login.html", register=True)


@app.route("/onboarding", methods=["GET", "POST"])
def onboarding_step1():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        # Collect form data
        name = request.form["name"]
        balance = request.form["balance"]
        goal_category = request.form["goal_category"]
        goal_target = request.form["goal_target"]
        goal_deadline = request.form["goal_deadline"]
        risk_level = request.form["risk_level"]

        conn = get_conn()
        try:
            cur = conn.cursor()

            # ✅ Update user name once during onboarding
            cur.execute("""
                UPDATE "Users"
                SET name = %s
                WHERE user_id = %s
            """, (name, session["user_id"]))

            # Create portfolio
            cur.execute("""
                INSERT INTO "Portfolios" (portfolio_id, user_id, balance)
                VALUES (gen_random_uuid(), %s, %s)
                RETURNING portfolio_id
            """, (session["user_id"], balance))
            portfolio_id = cur.fetchone()[0]

            # Create savings goal
            cur.execute("""
                INSERT INTO "SavingsGoal" (goal_id, portfolio_id, target_amount, deadline, category, progress)
                VALUES (gen_random_uuid(), %s, %s, %s, %s, 0.00)
            """, (portfolio_id, goal_target, goal_deadline, goal_category))

            # Create simulation preference
            cur.execute("""
                INSERT INTO "Simulation" (simulation_id, portfolio_id, scenario_type, risk_level, amount, expected_return)
                VALUES (gen_random_uuid(), %s, %s, %s, %s, %s)
            """, (portfolio_id, "Custom", risk_level, 0.00, 0.00))

            conn.commit()
            cur.close()

            # Store portfolio_id in session for later steps
            session["portfolio_id"] = portfolio_id

            return redirect(url_for("onboarding_step2"))

        except Exception as e:
            print("Error in onboarding route:", e)
            conn.rollback()
            return render_template("Onboarding.html", error="Something went wrong, please try again.")
        finally:
            db_pool.putconn(conn)

    return render_template("Onboarding.html")


@app.route("/onboarding2", methods=["GET", "POST"])
def onboarding_step2():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        income = request.form["income"]
        expenses = []
        for i in range(1, 4):
            category = request.form.get(f"expense_category_{i}")
            amount = request.form.get(f"expense_amount_{i}")
            if category and amount:
                expenses.append((category, amount))
        savings_percent = request.form.get("savings_percent")

        conn = get_conn()
        try:
            cur = conn.cursor()
            # Get portfolio_id
            cur.execute("""SELECT portfolio_id FROM "Portfolios" WHERE user_id=%s""", (session["user_id"],))
            portfolio_id = cur.fetchone()[0]

            # Insert income + expenses
            for category, amount in expenses:
                cur.execute("""
                    INSERT INTO "Budget" (budget_id, portfolio_id, income, expense_category, expense_amount)
                    VALUES (gen_random_uuid(), %s, %s, %s, %s)
                """, (portfolio_id, income, category, amount))

            conn.commit()
            cur.close()
        finally:
            db_pool.putconn(conn)

        return redirect(url_for("onboarding_step3"))

    return render_template("Onboarding2.html")


@app.route("/onboarding3", methods=["GET", "POST"])
def onboarding_step3():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        topic = request.form["topic"]
        difficulty = request.form["difficulty"]
        engagement = request.form["engagement"]
        avatar_url = request.form.get("avatar_url")  # safe access

        # Debug logs
        logging.debug("=== Onboarding Step 3 Debug ===")
        logging.debug("User ID: %s", session["user_id"])
        logging.debug("Topic: %s", topic)
        logging.debug("Difficulty: %s", difficulty)
        logging.debug("Engagement: %s", engagement)
        logging.debug("Avatar URL captured: %s", avatar_url)

        conn = get_conn()
        try:
            cur = conn.cursor()

            # Insert into UserContentAccess
            cur.execute("""
                INSERT INTO "UserContentAccess" (access_id, user_id, content_id)
                SELECT gen_random_uuid(), %s, content_id
                FROM "LiteracyContent"
                WHERE topic=%s AND difficulty=%s
                LIMIT 1
            """, (session["user_id"], topic, difficulty))

            # Insert into Nudge
            cur.execute("""
                INSERT INTO "Nudge" (nudge_id, portfolio_id, message, trigger_condition, delivered_at, response_status)
                SELECT gen_random_uuid(), p.portfolio_id, %s, %s, CURRENT_TIMESTAMP, %s
                FROM "Portfolios" p WHERE p.user_id=%s
            """, ("Welcome to Tajirisha!", engagement, "pending", session["user_id"]))

            # Update chosen avatar if provided
            if avatar_url:
                logging.debug("Updating avatar in DB...")
                cur.execute("""
                    UPDATE "Users"
                    SET avatar_url = %s
                    WHERE user_id = %s
                """, (avatar_url, session["user_id"]))
            else:
                logging.debug("No avatar selected — skipping update.")

            conn.commit()
            cur.close()
            
            # ✅ Query email directly from Users table
            cur = conn.cursor()
            cur.execute("""SELECT email FROM "Users" WHERE user_id=%s""", (session["user_id"],))
            user_email_row= cur.fetchone()
            cur.close()
            # ✅ Trigger nudge email after final onboarding step
            if user_email_row:
                user_email = user_email_row[0]
                cur = conn.cursor()
                cur.execute("""
                    SELECT category, progress, target_amount, deadline
                    FROM "SavingsGoal"
                    WHERE portfolio_id IN (
                        SELECT portfolio_id FROM "Portfolios" WHERE user_id = %s
                    )
                """, (session["user_id"],))
                goals = cur.fetchall()
                cur.close()

                formatted_goals = []
                for category, progress, target, deadline in goals:
                    current = round((progress / 100) * target, 2) if progress is not None else 0
                    formatted_goals.append((category, current, target, deadline))

                send_nudge_email(
                    to_email=user_email,
                    subject="Your Savings Progress Update",
                    goals=formatted_goals
                )

        finally:
            db_pool.putconn(conn)

        logging.debug("=== Onboarding Step 3 Complete ===")
        return redirect(url_for("dashboard"))

    return render_template("Onboarding3.html")



@app.route("/dashboard")
def dashboard():
    print("Dashboard session user_id:", session.get("user_id"))
    # Require login
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_conn()
    try:
        cur = conn.cursor()

        # User info (include avatar_url!)
        cur.execute("""
            SELECT email, year_of_study, name, avatar_url, university
            FROM "Users"
            WHERE user_id=%s::uuid
        """, (session["user_id"],))
        user_row = cur.fetchone()

        if not user_row:
            cur.close()
            conn.commit()
            return redirect(url_for("login"))

        # Use name if available, otherwise fallback to email prefix
        name = user_row[2] if user_row[2] else user_row[0].split("@")[0].title()

        # Fetch portfolio_id from database if not in session
        if "portfolio_id" not in session:
            cur.execute("""SELECT portfolio_id FROM "Portfolios" WHERE user_id=%s""", (session["user_id"],))
            portfolio_row = cur.fetchone()
            if portfolio_row:
                session["portfolio_id"] = portfolio_row[0]
            else:
                cur.close()
                conn.commit()
                return redirect(url_for("onboarding_step1"))

        portfolio_id = session["portfolio_id"]

        # Portfolio balance
        cur.execute("""SELECT balance FROM "Portfolios" WHERE portfolio_id = %s""", (portfolio_id,))
        balance = cur.fetchone()[0]

        # Current savings goal
        cur.execute("""
            SELECT category, target_amount, progress, deadline
            FROM "SavingsGoal"
            WHERE portfolio_id=%s
            ORDER BY deadline
            LIMIT 1
        """, (portfolio_id,))
        goal_row = cur.fetchone()

        # Simulations
        cur.execute("""
            SELECT scenario_type, risk_level, amount, expected_return
            FROM "Simulation"
            WHERE portfolio_id=%s
        """, (portfolio_id,))
        simulations = cur.fetchall()

        # Budget totals
        cur.execute("""
            SELECT COALESCE(SUM(expense_amount), 0), COALESCE(MAX(income), 0)
            FROM "Budget"
            WHERE portfolio_id = %s
        """, (portfolio_id,))
        budget_row = cur.fetchone()
        total_expenses = float(budget_row[0]) if budget_row and budget_row[0] is not None else 0.0
        income_value = float(budget_row[1]) if budget_row and budget_row[1] is not None else 0.0
        leftover_funds = float(balance) - total_expenses

        cur.close()
        conn.commit()
    finally:
        db_pool.putconn(conn)

    goal_deadline = goal_row[3] if goal_row else None
    goal_deadline_str = goal_deadline.strftime("%B %Y") if goal_deadline else None

    # Build user_data dictionary
    user_data = {
        "name": name,
        "year": user_row[1],
        "balance": balance,
        "goal": goal_row[0] if goal_row else None,
        "goal_amount": goal_row[1] if goal_row else None,
        "goal_progress": goal_row[2] if goal_row else None,
        "goal_deadline": goal_row[3] if goal_row else None,
        "goal_deadline_str": goal_deadline_str,
        "simulations": simulations,
        "avatar_url": user_row[3],
        "university": user_row[4]
    }

    # Add budget summary values
    user_data["total_expenses"] = total_expenses
    user_data["leftover_funds"] = leftover_funds

    logging.debug("Dashboard user_data: %s", user_data)

    # ✅ Capture success message from redirect
    success_message = request.args.get("success")

    # Disable caching
    response = make_response(render_template(
        "Desktop_Dashboard.html",
        user=user_data,
        success=success_message
    ))
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

#-----------MORE ROUTES-------------#
@app.route("/savings", methods=["GET", "POST"])
def savings():
    # Require login
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_conn()
    try:
        cur = conn.cursor()

        # Fetch portfolio_id from database if not in session
        if "portfolio_id" not in session:
            cur.execute("""SELECT portfolio_id FROM "Portfolios" WHERE user_id=%s""", (session["user_id"],))
            portfolio_row = cur.fetchone()
            if portfolio_row:
                session["portfolio_id"] = portfolio_row[0]
            else:
                cur.close()
                return redirect(url_for("onboarding_step1"))

        if request.method == "POST":
            action = request.form.get("action")

            if action == "update_balance":
                new_balance = float(request.form.get("new_balance", 0))
                cur.execute("""UPDATE "Portfolios" SET balance = %s WHERE portfolio_id = %s""",
                            (new_balance, session["portfolio_id"]))
                conn.commit()
                cur.close()
                if new_balance < 1000:  # example threshold
                    orchestrate_nudge(
                    session["portfolio_id"],
                    "low_balance",
                    {"balance": new_balance}
                )
                    send_nudge_email(
                    session["user_email"],
                    "Low Balance Alert",
                    f"Your balance has dropped to {new_balance} KSh. Consider adjusting your spending."
                )

                return redirect(url_for("savings"))

            elif action == "delete":
                goal_id = request.form.get("goal_id")
                cur.execute("""DELETE FROM "SavingsGoal" WHERE goal_id = %s""", (goal_id,))
                conn.commit()
                cur.close()
                return redirect(url_for("savings"))

            else:
                target_amount = request.form.get("target_amount")
                goal_category = request.form.get("goal_category")
                deadline = request.form.get("deadline")

                cur.execute("""
                    INSERT INTO "SavingsGoal" (goal_id, portfolio_id, target_amount, deadline, category, progress)
                    VALUES (gen_random_uuid(), %s, %s, %s, %s, 0.00)
                """, (session["portfolio_id"], target_amount, deadline, goal_category))
                conn.commit()
                cur.close()
                return redirect(url_for("savings"))

        # Fetch portfolio balance
        cur.execute("""SELECT balance FROM "Portfolios" WHERE portfolio_id = %s""",
                    (session["portfolio_id"],))
        portfolio_balance = cur.fetchone()[0]

        # Fetch all goals
        cur.execute("""
            SELECT goal_id, category, target_amount, deadline, progress
            FROM "SavingsGoal"
            WHERE portfolio_id = %s
        """, (session["portfolio_id"],))
        rows = cur.fetchall()

        goals_list = []
        total_target = 0

        for goal_id, category, target_amount, deadline, progress in rows:
            calc_progress = (portfolio_balance / target_amount * 100) if target_amount > 0 else 0
            goals_list.append({
                "goal_id": goal_id,
                "category": category,
                "target_amount": target_amount,
                "deadline": deadline,
                "progress": round(calc_progress, 2)
            })
            total_target += target_amount

        overall_progress = (portfolio_balance / total_target * 100) if total_target > 0 else 0

        cur.close()

        # Disable caching
        response = make_response(render_template(
            "Desktop_SavingsPlanner.html",
            goals=goals_list,
            portfolio_balance=portfolio_balance,
            total_target=total_target,
            overall_progress=overall_progress
        ))
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    except Exception as e:
        print("Error in savings route:", e)
        response = make_response(render_template(
            "Desktop_SavingsPlanner.html",
            goals=[],
            portfolio_balance=0,
            total_target=0,
            overall_progress=0
        ))
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    finally:
        db_pool.putconn(conn)

#----MORE Routes----#
# Configure database BEFORE initializing SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:4959%40SU@localhost:5432/tajirisha_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

#CLASS DEFINITIONS
# Simulation model
class Simulation(db.Model):
    __tablename__ = "Simulation"
    simulation_id = db.Column(db.String, primary_key=True)
    portfolio_id = db.Column(db.String, nullable=False)
    scenario_type = db.Column(db.String(100))
    risk_level = db.Column(db.Integer)
    amount = db.Column(db.Numeric(12,2))
    expected_return = db.Column(db.Numeric(5,2))

class Users(db.Model):
    __tablename__ = "Users"

    user_id = db.Column(db.String, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    year_of_study = db.Column(db.Integer, nullable=False)

    # New fields you added
    name = db.Column(db.String(255))
    university = db.Column(db.String(255))
    avatar_url = db.Column(db.Text)
    level = db.Column(db.Integer)

    posts = db.relationship("CommunityPost", backref="user", lazy=True)

class CommunityPost(db.Model):
    __tablename__ = "CommunityPost"

    post_id = db.Column(db.String, primary_key=True)
    user_id = db.Column(db.String, db.ForeignKey("Users.user_id"), nullable=False)
    parent_post_id = db.Column(db.String, db.ForeignKey("CommunityPost.post_id"), nullable=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now())

class CommunityLike(db.Model):
    __tablename__ = "CommunityLike"
    like_id = db.Column(db.String, primary_key=True)  # or UUID if you prefer consistency
    post_id = db.Column(db.Uuid, db.ForeignKey("CommunityPost.post_id"), nullable=False)
    user_id = db.Column(db.Uuid, db.ForeignKey("Users.user_id"), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now())

class CommunityComment(db.Model):
    __tablename__ = "CommunityComment"
    comment_id = db.Column(db.String, primary_key=True)  # or UUID
    post_id = db.Column(db.Uuid, db.ForeignKey("CommunityPost.post_id"), nullable=False)
    user_id = db.Column(db.Uuid, db.ForeignKey("Users.user_id"), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now())



#END OF CLASS DEFINITIONS
# --- Plotting utilities ---

def get_base64_image(fig):
    """Helper to convert a Matplotlib/Seaborn figure to base64."""
    buf = io.BytesIO()
    plt.tight_layout()
    fig.savefig(buf, format="png", dpi=100) # dpi=100 keeps it crisp but light
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    return f"data:image/png;base64,{encoded}"

def plot_projection(projection_df, scenario):
    # Create the figure
    fig, ax = plt.subplots(figsize=(10, 5))
    
    # Seaborn lineplot with nice markers and styling
    sns.lineplot(
        data=projection_df, 
        x='Month', 
        y='Projected_Value', 
        marker='o', 
        linewidth=2.5,
        ax=ax
    )
    
    ax.set_title(f"{scenario.upper()} Projection", fontsize=14, pad=15)
    ax.set_xlabel("Month", fontweight='bold')
    ax.set_ylabel("Value (KES)", fontweight='bold')
    plt.xticks(rotation=45)
    
    return get_base64_image(fig)

def plot_history(history_df, scenario, year):
    year_df = history_df[history_df['Year'] == year]
    fig, ax = plt.subplots(figsize=(10, 5))
    
    # Seaborn used for more professional 'Historical' feel
    sns.lineplot(
        data=year_df, 
        x='Month', 
        y='Value', 
        marker='s', # Square markers for history to differentiate from projection
        color='teal',
        ax=ax
    )
    
    ax.set_title(f"{scenario.upper()} Historical Performance ({year})", fontsize=14, pad=15)
    ax.set_xlabel("Month", fontweight='bold')
    ax.set_ylabel("Value (KES)", fontweight='bold')
    plt.xticks(rotation=45)
    
    return get_base64_image(fig)

@app.route('/simulation', methods=['GET', 'POST'])
def simulation():
    # Require login
    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == 'POST':
        from cvs.test_split_baseregression import run_simulation

        scenario_type = request.form['scenario_type']
        risk_level = int(request.form['risk_level'])
        amount = float(request.form['amount'])
        portfolio_id = request.form.get('portfolio_id', session.get("portfolio_id"))
        duration = int(request.form.get('duration', 12))

        # Run simulation
        projection, history = run_simulation(
            portfolio_id=portfolio_id,
            amount=amount,
            scenario=scenario_type,
            duration=duration,
            start_year=None,
            risk_level=risk_level
        )

        expected_return = round(float(projection['Projected_Return_%'].mean()), 2)
        estimated_value = round(float(projection['Projected_Value'].iloc[-1]), 2)

        # Save to DB
        sim = Simulation(
            simulation_id=str(uuid.uuid4()),
            portfolio_id=portfolio_id,
            scenario_type=scenario_type,
            risk_level=risk_level,
            amount=amount,
            expected_return=expected_return
        )
        db.session.add(sim)
        db.session.commit()

        # ✅ Log the simulation run
        log_event(session["user_id"], portfolio_id, "SimulationRun",
                  f"Ran {scenario_type} simulation with risk {risk_level}, amount {amount}, expected return {expected_return}%")

        # Build history tables + graphs only for valid years
        history_years = []
        history_tables = {}
        history_graphs = {}
        if history is not None and not history.empty:
            valid_years = sorted(
                history.groupby('Year').filter(lambda g: g['Actual_Return_%'].notna().any())['Year'].unique()
            )
            history_years = [int(yr) for yr in valid_years]
            for yr in history_years:
                year_df = history[history['Year'] == yr]
                history_tables[str(yr)] = year_df.to_html(classes="table table-striped", index=False)
                history_graphs[str(yr)] = plot_history(history, scenario_type, yr)

        # Projection graph
        projection_img = plot_projection(projection, scenario_type)
        history_img = history_graphs.get(str(history_years[0])) if history_years else None

        # Disable caching
        response = make_response(render_template(
            "Desktop_Simulation.html",
            scenario_type=scenario_type,
            amount=amount,
            expected_return=expected_return,
            risk_profile="Low" if risk_level <= 3 else "Moderate" if risk_level <= 7 else "High",
            estimated_value=estimated_value,
            duration=duration,
            projection_table=projection.to_html(classes="table table-striped", index=False),
            history_table=history_tables.get(str(history_years[0])) if history_years else None,
            history_years=history_years,
            history_tables=history_tables,
            history_graphs=history_graphs,
            projection_img=projection_img,
            history_img=history_img
        ))
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    # GET request → safe defaults
    response = make_response(render_template(
        "Desktop_Simulation.html",
        scenario_type=None,
        amount=None,
        expected_return=None,
        risk_profile=None,
        estimated_value=None,
        duration=None,
        projection_table=None,
        history_table=None,
        history_years=[],
        history_tables={},
        history_graphs={},
        projection_img=None,
        history_img=None
    ))
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.route("/budget", methods=["GET", "POST"])
def budget():
    # Require login
    if "user_id" not in session:
        return redirect(url_for("login"))

    now = datetime.now()
    current_month = now.strftime("%B")
    current_year = now.year

    conn = get_conn()
    try:
        cur = conn.cursor()

        if request.method == "POST":
            action = request.form.get("action")

            if action == "delete":
                budget_id = request.form.get("budget_id")
                cur.execute("""DELETE FROM "Budget" WHERE budget_id = %s""", (budget_id,))
                conn.commit()
                return redirect(url_for("budget"))

            elif action == "add":
                income = request.form.get("income")
                expense_name = request.form.get("expense_name")
                amount = request.form.get("amount")
                notes = request.form.get("notes")

                cur.execute("""
                    INSERT INTO "Budget" (budget_id, portfolio_id, income, expense_category, expense_amount)
                    VALUES (gen_random_uuid(), %s, %s, %s, %s)
                """, (session["portfolio_id"], income, expense_name, amount))
                conn.commit()
                return redirect(url_for("budget"))

        # --- Fetch portfolio balance ---
        cur.execute("""SELECT balance FROM "Portfolios" WHERE portfolio_id = %s""",
                    (session["portfolio_id"],))
        portfolio_balance = cur.fetchone()[0]

        # --- Fetch all budget rows ---
        cur.execute("""
            SELECT budget_id, income, expense_category, expense_amount
            FROM "Budget"
            WHERE portfolio_id = %s
        """, (session["portfolio_id"],))
        rows = cur.fetchall()

        # Build expenses list + calculate totals
        expenses = []
        total_expenses = 0
        income_value = 0
        for budget_id, income, category, amount in rows:
            expenses.append({
                "id": budget_id,
                "category": category,
                "amount": amount,
                "notes": ""  # optional, if you later add notes column
            })
            total_expenses += amount
            income_value = income  # last income value (or aggregate if you prefer)

        leftover_funds = portfolio_balance - total_expenses

        cur.close()

        #  Disable caching
        response = make_response(render_template(
            "Desktop_Budget_Creation.html",
            current_month=current_month,
            current_year=current_year,
            portfolio_balance=portfolio_balance,
            expenses=expenses,
            total_expenses=total_expenses,
            leftover_funds=leftover_funds,
            income=income_value
        ))
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    except Exception as e:
        print("Error in budget route:", e)
        response = make_response(render_template(
            "Desktop_Budget_Creation.html",
            current_month=current_month,
            current_year=current_year,
            portfolio_balance=0,
            expenses=[],
            total_expenses=0,
            leftover_funds=0,
            income=0
        ))
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    finally:
        db_pool.putconn(conn)

@app.route("/lessons")
def lessons():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT avatar_url
            FROM "Users"
            WHERE user_id = %s
        """, (session["user_id"],))
        row = cur.fetchone()
        cur.close()
    finally:
        db_pool.putconn(conn)

    user = {"avatar_url": row[0] if row and row[0] else None}

    response = make_response(render_template("Desktop_Lessons.html", user=user))
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.route("/api/lesson-progress", methods=["GET"])
def get_lesson_progress():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401

    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT content_id, score, streak, completed
            FROM "UserContentAccess"
            WHERE user_id = %s
        """, (session["user_id"],))
        rows = cur.fetchall()
        cur.close()
    finally:
        db_pool.putconn(conn)

    # Convert to dict keyed by content_id
    progress = {row[0]: {"score": row[1], "streak": row[2], "completed": row[3]} for row in rows}

    return jsonify(progress)


@app.route("/community", methods=["GET", "POST"])
def community():
    # Require login
    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        content = request.form.get("content")
        user_id = session.get("user_id")
        portfolio_id = session.get("portfolio_id")  # ✅ make sure portfolio_id is in session

        if content and user_id:
            post = CommunityPost(
                post_id=str(uuid.uuid4()),
                user_id=user_id,
                content=content
            )
            db.session.add(post)
            db.session.commit()

            # ✅ Log the community post event
            log_event(user_id, portfolio_id, "CommunityPost",
                      f"Posted in community: {content[:50]}...")

    # Fetch posts
    posts = CommunityPost.query.order_by(CommunityPost.created_at.desc()).limit(20).all()
    current_user = Users.query.get(session.get("user_id"))

    # Disable caching
    response = make_response(render_template("Desktop_Community.html",
                                             posts=posts,
                                             current_user=current_user))
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.route("/settings", methods=["GET", "POST"])
def settings():
    if "user_id" not in session:
        return redirect(url_for("login"))

    # Fetch current user info
    current_user = None
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT user_id, name, email, university, year_of_study, avatar_url
            FROM "Users"
            WHERE user_id=%s
        """, (session["user_id"],))
        row = cur.fetchone()
        cur.close()
        if row:
            current_user = {
                "id": row[0],
                "name": row[1],
                "email": row[2],
                "university": row[3],
                "year_of_study": row[4],
                "avatar_url": row[5]
            }
    finally:
        db_pool.putconn(conn)

    if request.method == "POST":
        action = request.form.get("action")

        if action == "password":
            # ... password change logic ...

            log_event(session["user_id"], session.get("portfolio_id"),
                      "PasswordChange", "User changed their password")

            # ✅ Send a nudge email once
            user_email = current_user["email"]
            if user_email:
                send_nudge_email(
                    to_email=user_email,
                    subject="Your Password Was Updated Successfully",
                    context="password_change"
                )

            # Redirect to dashboard instead of settings
            return redirect(url_for("dashboard",
                                    success="✅ Password updated successfully! A confirmation email has been sent."
    ))

        elif action == "profile":
            university = request.form["university"]
            year = request.form["year_of_study"]

            conn = get_conn()
            try:
                cur = conn.cursor()
                cur.execute("""
                    UPDATE "Users"
                    SET university=%s, year_of_study=%s
                    WHERE user_id=%s
                """, (university, year, session["user_id"]))
                conn.commit()
                cur.close()
            finally:
                db_pool.putconn(conn)

            log_event(session["user_id"], session.get("portfolio_id"),
                      "ProfileUpdate", f"Updated profile: University={university}, Year={year}")

            current_user["university"] = university
            current_user["year_of_study"] = year

            return redirect(url_for("settings", success="Profile updated successfully!"))

        elif action == "avatar":
            avatar_url = request.form["avatar_url"]

            conn = get_conn()
            try:
                cur = conn.cursor()
                cur.execute("""
                    UPDATE "Users"
                    SET avatar_url=%s
                    WHERE user_id=%s
                """, (avatar_url, session["user_id"]))
                conn.commit()
                cur.close()
            finally:
                db_pool.putconn(conn)

            log_event(session["user_id"], session.get("portfolio_id"),
                      "ProfileUpdate", f"Updated avatar to {avatar_url}")

            current_user["avatar_url"] = avatar_url

            return redirect(url_for("settings", success="Avatar updated successfully!"))

        elif action == "delete":
            conn = get_conn()
            try:
                cur = conn.cursor()
                cur.execute("""
                    DELETE FROM "Users"
                    WHERE user_id = %s
                """, (session["user_id"],))
                conn.commit()
                cur.close()
            finally:
                db_pool.putconn(conn)

            # Clear session so user is logged out
            user_id = session.get("user_id")  # capture before clearing
            portfolio_id = session.get("portfolio_id")

            session.clear()

            log_event(user_id, portfolio_id,
                      "AccountDeletion", "User deleted their account")

            return redirect(url_for("login"))

    # GET request → render settings page with user info
    success_message = request.args.get("success")
    response = make_response(render_template(
        "Desktop_Settings.html",
        user=current_user,
        success=success_message
    ))
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.route("/logout")
def logout():
    # Capture user_id and portfolio_id before clearing session
    user_id = session.get("user_id")
    portfolio_id = session.get("portfolio_id")

    # ✅ Log the logout event if user was logged in
    if user_id:
        log_event(user_id, portfolio_id, "Logout", "User logged out")

    # Clear session
    session.clear()

    # Redirect to login with cache disabled
    response = make_response(redirect(url_for("login")))
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response
#LOGS#
@app.route("/logs", methods=["GET", "POST"])
def logs():
    if "user_id" not in session:
        return redirect(url_for("login"))

    event_type_filter = request.args.get("event_type", "")
    date_filter = request.args.get("date", "")

    conn = get_conn()
    try:
        cur = conn.cursor()

        query = """
            SELECT event_type, description, created_at
            FROM "EventLogs"
            WHERE user_id = %s
        """
        params = [session["user_id"]]

        if event_type_filter:
            query += " AND event_type = %s"
            params.append(event_type_filter)

        if date_filter:
            query += " AND DATE(created_at) = %s"
            params.append(date_filter)

        query += " ORDER BY created_at DESC LIMIT 100"
        cur.execute(query, tuple(params))
        logs = cur.fetchall()
        cur.close()
    finally:
        db_pool.putconn(conn)

    formatted_logs = [
        {
            "event_type": row[0],
            "description": row[1],
            "created_at": row[2].strftime("%d %B %Y, %H:%M:%S")
        }
        for row in logs
    ]

    response = make_response(render_template("Desktop_Logs.html",
                                             logs=formatted_logs,
                                             event_type_filter=event_type_filter,
                                             date_filter=date_filter))
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response
#LOGS DOWNLOAD#
#
@app.route("/logs/download")
def download_logs():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT event_type, description, created_at
            FROM "EventLogs"
            WHERE user_id = %s
            ORDER BY created_at DESC
        """, (session["user_id"],))
        logs = cur.fetchall()
        cur.close()
    finally:
        db_pool.putconn(conn)

    # Convert logs to CSV
    import csv
    from io import StringIO
    from flask import Response

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Event Type", "Description", "Timestamp"])
    for row in logs:
        writer.writerow([row[0], row[1], row[2].strftime("%d %B %Y, %H:%M:%S")])

    response = Response(output.getvalue(), mimetype="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=event_logs.csv"
    return response
#LOGS END#
#Nudge Orchestrator#
@app.route("/nudges", methods=["GET"])
def nudges():
    if "user_id" not in session:
        return redirect(url_for("login"))

    portfolio_id = session.get("portfolio_id")

    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT nudge_id, message, trigger_condition, delivered_at, response_status
            FROM "Nudge"
            WHERE portfolio_id=%s
            ORDER BY delivered_at DESC
            LIMIT 10
        """, (portfolio_id,))
        rows = cur.fetchall()
        cur.close()
    finally:
        db_pool.putconn(conn)

    nudges = [
        {
            "id": row[0],
            "message": row[1],
            "trigger": row[2],
            "delivered_at": row[3].strftime("%d %B %Y, %H:%M:%S") if row[3] else None,
            "response": row[4]
        }
        for row in rows
    ]

    response = make_response(render_template("Desktop_Nudges.html", nudges=nudges))
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.route("/respond_nudge/<uuid:nudge_id>", methods=["POST"])
def respond_nudge(nudge_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    response_value = request.form.get("response")  # "accepted" or "dismissed"

    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE "Nudge"
            SET response_status=%s
            WHERE nudge_id=%s AND portfolio_id=%s
        """, (response_value, str(nudge_id), session.get("portfolio_id")))
        conn.commit()
        cur.close()
    finally:
        db_pool.putconn(conn)

    # ✅ Log the response event
    log_event(session["user_id"], session.get("portfolio_id"), "NudgeResponse",
              f"Nudge {nudge_id} marked as {response_value}")

    return redirect(url_for("nudges"))

def generate_nudge_message(trigger_condition, context=None):
    """
    Map trigger conditions to tailored messages.
    """
    if trigger_condition == "low_balance":
        return f"Your balance is down to {context.get('balance')} KSh. Consider adjusting your spending."
    elif trigger_condition == "goal_deadline":
        return f"Your savings goal deadline is approaching on {context.get('deadline')}. Keep saving!"
    elif trigger_condition == "high_risk":
        return "Your risk level is high. Diversify to protect your portfolio."
    elif trigger_condition == "welcome":
        return "Welcome to Tajirisha! Start tracking your financial journey today."
    else:
        return "Keep tracking your financial journey!"


def orchestrate_nudge(portfolio_id, trigger_condition, context=None):
    """
    Create and store a nudge in the Nudge table.
    """
    message = generate_nudge_message(trigger_condition, context or {})

    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO "Nudge" (nudge_id, portfolio_id, message, trigger_condition, delivered_at, response_status)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            str(uuid.uuid4()),
            portfolio_id,
            message,
            trigger_condition,
            datetime.now(),
            "active"
        ))
        conn.commit()
        cur.close()
    finally:
        db_pool.putconn(conn)

@app.route("/nudge/acknowledge/<uuid:nudge_id>", methods=["POST"])
def acknowledge_nudge(nudge_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE "Nudge"
            SET response_status = 'acknowledged'
            WHERE nudge_id = %s
        """, (str(nudge_id),))
        conn.commit()
        cur.close()
    finally:
        db_pool.putconn(conn)

    return redirect(url_for("dashboard"))


@app.route("/nudge/dismiss/<uuid:nudge_id>", methods=["POST"])
def dismiss_nudge(nudge_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE "Nudge"
            SET response_status = 'dismissed'
            WHERE nudge_id = %s
        """, (str(nudge_id),))
        conn.commit()
        cur.close()
    finally:
        db_pool.putconn(conn)

    return redirect(url_for("dashboard"))
def log_failed_email_db(email, reason):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO "FailedEmails" (email, reason)
            VALUES (%s, %s)
        """, (email, reason))
        conn.commit()
        cur.close()
    finally:
        db_pool.putconn(conn)

@app.route("/test-email")
def test_email():
    try:
        send_nudge_email(
            to_email="elkanahomari100@gmail.com",
            subject="Tajirisha Email Test",
            body="Hello! This is a test email from Tajirisha."
        )
        return "✅ Test email sent successfully!"
    except Exception as e:
        return f"❌ Failed to send email: {e}"@app.route("/test-email")

@app.route("/nudge-email/<email>")
def nudge_email_by_email(email):
    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()

        # Step 1: Find the user's UUID
        cur.execute('SELECT user_id FROM "Users" WHERE email = %s', (email,))
        row = cur.fetchone()
        if not row:
            cur.close()
            return f"No user found with email {email}."
        user_id = row[0]

        # Step 2: Fetch goals linked to this user
        cur.execute("""
            SELECT category, progress, target_amount, deadline
            FROM "SavingsGoal"
            WHERE portfolio_id IN (
                SELECT portfolio_id
                FROM "Portfolios"
                WHERE user_id = %s
            )
        """, (user_id,))
        goals = cur.fetchall()
        cur.close()

        # Step 3: Format goals if any
        formatted_goals = []
        for category, progress, target, deadline in goals:
            current = round((progress / 100) * target, 2) if progress is not None else 0
            formatted_goals.append((category, current, target, deadline))

        # ✅ Always call send_nudge_email, even if no goals
        send_nudge_email(
            to_email=email,
            subject="Your Savings Progress Update",
            goals=formatted_goals
        )

        if not formatted_goals:
            return f"Nudge email sent with motivational message (no goals found) for {email}."
        else:
            return f"Nudge email sent with progress update for {email}."

    except Exception as e:
        return f"Error fetching goals or sending email: {e}"
    finally:
        if conn:
            db_pool.putconn(conn)
def comma_format(value):
    try:
        return "{:,}".format(int(value))
    except (ValueError, TypeError):
        return value
app.jinja_env.filters['comma'] = comma_format
#Nudge Orchestrator#
# ---------------- MAIN ---------------- #
if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    context = (
        "C:/Users/Administrator/Desktop/Year 4/4.2/project 3 4/Tajirisha Codespace/Desktop/localhost.cert.pem",
        "C:/Users/Administrator/Desktop/Year 4/4.2/project 3 4/Tajirisha Codespace/Desktop/localhost.key.pem"
    )

    app.run(host="localhost", port=5000, ssl_context=context, debug=True)
    