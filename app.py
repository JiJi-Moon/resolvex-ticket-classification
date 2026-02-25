from flask import Flask, render_template, request, redirect, url_for, flash, session
import uuid
import re
import pickle
import torch
from datetime import datetime
from transformers import BertTokenizerFast, BertForSequenceClassification
from keybert import KeyBERT

# ✅ IMPORT DB LAYER
from db_functions import *

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY")

# ✅ INITIALIZE DATABASE
init_db()

DEPARTMENTS = [
    "Technical Support",
    "Returns and Exchanges",
    "Billing and Payments",
    "Sales and Pre-Sales",
    "Service Outages and Maintenance",
    "Product Support",
    "IT Support",
    "Customer Service",
    "Human Resources",
    "General Inquiry"
]

# ======================================
# WORKFLOW TRANSITION RULES
# ======================================

ALLOWED_TRANSITIONS = {
    "Open": ["In Progress", "On Hold", "Resolved", "Closed"],
    "In Progress": ["On Hold", "Resolved"],
    "On Hold": ["In Progress"],
    "Resolved": ["Closed", "Reopened"],
    "Reopened": ["In Progress"],
    "Closed": []
}

DIRECT_CLOSE_REASONS = [
    "Duplicate Ticket",
    "Invalid Ticket",
    "Spam",
    "Other"
]

# ======================================
# LOAD AI MODELS
# ======================================

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

kw_model = KeyBERT(model="all-MiniLM-L6-v2")

dept_tokenizer = BertTokenizerFast.from_pretrained("./ticket_classification_model")
dept_model = BertForSequenceClassification.from_pretrained(
    "./ticket_classification_model"
).to(device)
dept_model.eval()

with open("./ticket_classification_model/label_encoder.pkl", "rb") as f:
    le_dept = pickle.load(f)

with open("./ticket_priority_model/priority_model.pkl", "rb") as f:
    priority_model = pickle.load(f)

with open("./ticket_priority_model/priority_vectorizer.pkl", "rb") as f:
    tfidf_priority = pickle.load(f)

with open("./ticket_priority_model/priority_label_encoder.pkl", "rb") as f:
    le_priority = pickle.load(f)

# ======================================
# HELPER FUNCTIONS
# ======================================

def validate_transition(current_status, new_status, role):
    if new_status not in ALLOWED_TRANSITIONS.get(current_status, []):
        return False

    if role == "admin":
        if current_status == "Resolved" and new_status == "Closed":
            return False
        return True

    if role == "user":
        if current_status == "Resolved" and new_status in ["Closed", "Reopened"]:
            return True
        return False

    return False


def strip_email_noise(text):
    text = text.lower().strip()
    greetings = ["dear customer support team", "dear support team", "hello", "hi"]
    for g in greetings:
        if text.startswith(g):
            text = text[len(g):].strip(" ,.\n")
    return text


def generate_title(text):
    keywords = kw_model.extract_keywords(
        text,
        keyphrase_ngram_range=(2, 4),
        stop_words="english",
        top_n=1
    )
    return keywords[0][0].title() if keywords else "General Support Issue"


def generate_description(email_body):
    text = strip_email_noise(email_body)
    text = re.sub(r"\s+", " ", text)
    return text.capitalize()


def predict_department(text):
    clean = strip_email_noise(text)

    inputs = dept_tokenizer(
        clean,
        return_tensors="pt",
        truncation=True,
        padding=True,
        max_length=128
    ).to(device)

    with torch.no_grad():
        outputs = dept_model(**inputs)

    pred = torch.argmax(outputs.logits, dim=1).item()
    return le_dept.inverse_transform([pred])[0]


HIGH_PRIORITY_WORDS = [
    "outage", "offline", "down", "blocked",
    "failure", "cannot access", "urgent", "critical"
]


def predict_priority(text):
    text_lower = text.lower()

    if any(w in text_lower for w in HIGH_PRIORITY_WORDS):
        return "High"

    clean = re.sub(r"[^a-z0-9 ]", " ", text_lower)
    clean = re.sub(r"\s+", " ", clean)

    vec = tfidf_priority.transform([clean])
    pred = priority_model.predict(vec)
    return le_priority.inverse_transform(pred)[0]

# ======================================
# ROUTES
# ======================================

@app.route("/")
def home():
    return render_template(
        "home.html",
        role=session.get("role"),
        username=session.get("username")
    )

# ================= REGISTER =================

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        try:
            register_user(name, username, email, password)
            flash("Registration Successful! Please Login.")
            return redirect(url_for("login"))
        except:
            flash("Username or Email already exists!")
            return redirect(url_for("register"))

    return render_template("register.html")

# ================= LOGIN =================

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user_input = request.form["user_input"]
        password = request.form["password"]

        session.clear()

        # 🔹 First check if this is a Team Admin login
        team = get_team_by_team_id(user_input)

        if team and team["password"] == password:
            session["role"] = "team_admin"
            session["team_id"] = team["team_id"]
            session["username"] = team["team_id"]
            return redirect(url_for("dashboard"))

        # 🔹 Otherwise check normal user login
        user = get_user_by_input(user_input)

        if user and user["password"] == password:
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]
            session["team_id"] = user["team_id"]
            return redirect(url_for("dashboard"))

        flash("Invalid Credentials!")

    return render_template("login.html")

# ================= DASHBOARD =================

@app.route("/dashboard")
def dashboard():

    if "role" not in session:
        return redirect(url_for("login"))

    role = session["role"]

    # ================= USER DASHBOARD =================
    if role == "user":
        username = session["username"]

        rows = get_status_counts_for_user(username)
        resolved_tickets = get_resolved_tickets_for_user(username)
        recent_tickets = get_recent_tickets_for_user(username)

        counts = {
            "Total": 0,
            "Open": 0,
            "In Progress": 0,
            "On Hold": 0,
            "Resolved": 0,
            "Reopened": 0,
            "Closed": 0
        }

        for row in rows:
            counts[row["status"]] = row["count"]
            counts["Total"] += row["count"]

        return render_template(
            "dashboard.html",
            role=role,
            username=username,
            counts=counts,
            resolved_tickets=resolved_tickets,
            recent_tickets=recent_tickets
        )

   # ================= ADMIN DASHBOARD =================
    elif role == "admin":

        total_tickets = get_total_ticket_count()
        assigned = get_assigned_ticket_count()
        unassigned = get_unassigned_ticket_count()
        high_priority_unassigned = get_high_priority_unassigned()

        activities = get_system_activity()

        # 🔥 NEW: Chart Data
        status_data = get_status_distribution()
        department_data = get_department_distribution()

        return render_template(
            "dashboard.html",
            role=role,
            total_tickets=total_tickets,
            assigned=assigned,
            unassigned=unassigned,
            high_priority_unassigned=high_priority_unassigned,
            activities=activities,
            status_data=status_data,
            department_data=department_data
        )
    # ================= TEAM DASHBOARD =================
    elif role in ["team_admin", "team_member"]:
        team_id = session["team_id"]

        kpis = get_team_kpis(team_id)
        activities = get_team_activity(team_id)

        return render_template(
            "dashboard.html",
            role=role,
            team_id=team_id,
            kpis=kpis,
            activities=activities
        )

# ================= CREATE TICKET =================

@app.route("/create_ticket", methods=["GET", "POST"])
def create_ticket():

    if session.get("role") != "user":
        return redirect(url_for("home"))

    ticket = None

    if request.method == "POST":
        email_body = request.form["description"]

        user = get_user_by_input(session["username"])

        ticket = {
            "ticket_id": str(uuid.uuid4())[:8],
            "title": generate_title(email_body),
            "description": generate_description(email_body),
            "department": predict_department(email_body),
            "priority": predict_priority(email_body),
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "username": user["username"],
            "name": user["name"],
            "email": user["email"],
            "status": "Open"
        }

        insert_ticket(ticket)

    return render_template("create_ticket.html", ticket=ticket)

# ================= VIEW TICKETS =================

@app.route("/view_tickets")
def view_tickets():

    if "role" not in session:
        return redirect(url_for("login"))

    role = session["role"]

    # 🔎 GET SEARCH + FILTER + SORT PARAMETERS
    search = request.args.get("search", "").strip()
    status_filter = request.args.get("status", "")
    priority_filter = request.args.get("priority", "")
    department_filter = request.args.get("department", "")
    team_filter = request.args.get("team_id", "")
    sort_option = request.args.get("sort", "")

    # 🔹 Admin
    if role == "admin":
        tickets = get_filtered_tickets(
            role=role,
            search=search,
            status=status_filter,
            priority=priority_filter,
            department=department_filter,
            team_id=team_filter,
            sort=sort_option
        )
        teams = get_all_teams()

        return render_template(
            "view_tickets.html",
            tickets=tickets,
            role=role,
            teams=teams,
            allowed_transitions=ALLOWED_TRANSITIONS,
            direct_close_reasons=DIRECT_CLOSE_REASONS
        )

    # 🔹 Team
    elif role in ["team_admin", "team_member"]:
        tickets = get_filtered_tickets(
            role=role,
            team_id=session["team_id"],
            search=search,
            status=status_filter,
            priority=priority_filter,
            department=department_filter,
            sort=sort_option
        )

    # 🔹 User
    else:
        tickets = get_filtered_tickets(
            role=role,
            username=session["username"],
            search=search,
            status=status_filter,
            priority=priority_filter,
            sort=sort_option
        )

    return render_template(
        "view_tickets.html",
        tickets=tickets,
        role=role,
        allowed_transitions=ALLOWED_TRANSITIONS,
        direct_close_reasons=DIRECT_CLOSE_REASONS
    )
# ================= PROFILE =================
@app.route("/profile", methods=["GET", "POST"])
def profile():

    if "role" not in session:
        return redirect(url_for("login"))

    user = get_user_by_input(session["username"])

    if request.method == "POST":

        phone = request.form.get("phone")
        bio = request.form.get("bio")
        location = request.form.get("location")
        designation = request.form.get("designation")

        update_profile_details(
            user["id"],
            phone,
            bio,
            location,
            designation
        )

        flash("Profile updated successfully.", "success")
        return redirect(url_for("profile"))

    return render_template(
        "profile.html",
        user=user
    )
# ================= CREATE TEAM =================
@app.route("/create_team", methods=["POST"])
def create_team_route():

    if session.get("role") != "admin":
        return redirect(url_for("login"))

    team_name = request.form["team_name"]

    try:
        create_team(team_name)
    except:
        flash("Team already exists!")

    return redirect(url_for("dashboard"))

# ================= PROMOTE USER =================
@app.route("/promote_user", methods=["POST"])
def promote_user_route():

    if session.get("role") != "admin":
        return redirect(url_for("login"))

    user_id = request.form["user_id"]
    team_id = request.form["team_id"]

    promote_user_to_team(user_id, team_id)

    return redirect(url_for("dashboard"))
# ================= UPDATE STATUS =================

@app.route("/update_status/<ticket_id>", methods=["POST"])
def update_status(ticket_id):

    if session.get("role") not in ["team_admin", "team_member"]:
        return redirect(url_for("login"))

    new_status = request.form.get("status")
    closure_reason = request.form.get("closure_reason")

    ticket = get_ticket_by_id(ticket_id)

    if not ticket:
        return redirect(url_for("view_tickets"))

    current_status = ticket["status"]

    if new_status not in ALLOWED_TRANSITIONS.get(current_status, []):
        flash("Invalid status transition.")
        return redirect(url_for("view_tickets"))

    performer = session["username"]

    update_ticket_status(ticket_id, new_status, closure_reason, performer)

    log_activity(
        ticket_id=ticket_id,
        action_type="Status Updated",
        performed_by=performer,
        role=session["role"],
        remarks=f"Changed to {new_status}"
    )

    return redirect(url_for("view_tickets"))

# ================= REGISTER TEAM =================
@app.route("/register_team", methods=["GET", "POST"])
def register_team():

    if session.get("role") != "admin":
        return redirect("/dashboard")

    if request.method == "POST":
        department = request.form["department"]

        if department not in DEPARTMENTS:
            flash("Invalid department selected.", "error")
            return redirect("/register_team")

        team_id, password = create_team_with_auto_credentials(department)

        flash(f"Team Created! ID: {team_id} | Password: {password}", "success")
        return redirect("/team_management")

    return render_template(
        "register_team.html",
        departments=DEPARTMENTS
    )
# ================= ASSIGN TICKET =================
@app.route("/assign_ticket", methods=["POST"])
def assign_ticket():

    if session.get("role") != "admin":
        return redirect(url_for("login"))

    ticket_id = request.form["ticket_id"]
    team_id = request.form["team_id"]

    assign_ticket_to_team(ticket_id, team_id, session["user_id"])

    log_activity(
        ticket_id=ticket_id,
        action_type="Ticket Assigned",
        performed_by=session["username"],
        role="admin",
        remarks=f"Assigned to {team_id}"
    )

    flash("Ticket assigned successfully.")
    return redirect(url_for("view_tickets"))
# ================= ADD TEAM MEMBER =================
@app.route("/team/add_member", methods=["GET", "POST"])
def add_team_member_route():

    if session.get("role") != "team_admin":
        return redirect(url_for("login"))

    if request.method == "POST":
        email = request.form["email"]
        team_id = session["team_id"]

        add_team_member(email, team_id)

        log_activity(
            ticket_id=None,
            action_type="Member Added",
            performed_by=session["username"],
            role="team_admin",
            remarks=f"Added member with email {email}"
        )

        flash("Team member added successfully.")
        return redirect(url_for("dashboard"))

    return render_template("add_team_member.html")
# ================= TEAM MANAGEMENT =================
@app.route("/team_management")
def team_management():

    if session.get("role") != "admin":
        return redirect(url_for("login"))

    teams = get_all_teams()

    return render_template(
        "team_management.html",
        teams=teams
    )
# ================= CONFIRM RESOLUTION =================

@app.route("/confirm_resolution/<ticket_id>", methods=["POST"])
def confirm_resolution(ticket_id):

    if session.get("role") != "user":
        return redirect(url_for("login"))

    action = request.form["action"]

    ticket = get_ticket_by_id(ticket_id)

    if not ticket or ticket["username"] != session["username"]:
        return redirect(url_for("view_tickets"))

    if ticket["status"] != "Resolved":
        return redirect(url_for("view_tickets"))

    if action == "confirm":
        update_ticket_status(ticket_id, "Closed", None, "user")
    elif action == "reopen":
        update_ticket_status(ticket_id, "Reopened")

    return redirect(url_for("view_tickets"))

# ================= STATIC PAGES =================

@app.route('/about')
def about():
    return render_template("about.html")

@app.route('/architecture')
def architecture():
    return render_template("architecture.html")

@app.route('/features')
def features():
    return render_template("features.html")

@app.route('/contact')
def contact():
    return render_template("contact.html")

# ================= LOGOUT =================

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully!")
    return redirect(url_for("home"))

if __name__ == "__main__":

    app.run(host="0.0.0.0", port=5000)

