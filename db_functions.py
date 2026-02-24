# db_functions.py

import sqlite3
import random
import string
from datetime import datetime

DB_NAME = "database.db"


# =====================================================
# CONNECTION
# =====================================================

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


# =====================================================
# DATABASE INITIALIZATION
# =====================================================

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # USERS TABLE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            team_id TEXT,
            phone TEXT,
            bio TEXT,
            location TEXT,
            designation TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # TEAMS TABLE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id TEXT UNIQUE NOT NULL,
            department TEXT NOT NULL,
            password TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # TICKETS TABLE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            ticket_id TEXT PRIMARY KEY,
            title TEXT,
            description TEXT,
            department TEXT,
            priority TEXT,
            created_at TEXT,
            username TEXT,
            name TEXT,
            email TEXT,
            status TEXT DEFAULT 'Open',
            closure_reason TEXT,
            closed_by TEXT
        )
    """)

    # TICKET ASSIGNMENTS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ticket_assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id TEXT NOT NULL,
            team_id TEXT NOT NULL,
            assigned_by INTEGER,
            assigned_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ACTIVITY LOGS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id TEXT,
            action_type TEXT,
            performed_by TEXT,
            role TEXT,
            remarks TEXT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # SEED ADMIN
    cursor.execute("SELECT * FROM users WHERE role='admin'")
    if not cursor.fetchone():
        cursor.execute("""
            INSERT INTO users (name, username, email, password, role)
            VALUES (?, ?, ?, ?, ?)
        """, (
            "System Admin",
            "admin",
            "admin@resolvex.com",
            "admin123",
            "admin"
        ))

    conn.commit()
    conn.close()


# =====================================================
# USER FUNCTIONS
# =====================================================

def register_user(name, username, email, password):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (name, username, email, password, role)
        VALUES (?, ?, ?, ?, 'user')
    """, (name, username, email, password))
    conn.commit()
    conn.close()


def get_user_by_input(user_input):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM users
        WHERE username=? OR email=?
    """, (user_input, user_input))
    user = cursor.fetchone()
    conn.close()
    return user


def get_users_by_role(role):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE role=?", (role,))
    users = cursor.fetchall()
    conn.close()
    return users


def add_team_member(email, team_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE users
        SET role='team_member', team_id=?
        WHERE email=?
    """, (team_id, email))
    conn.commit()
    conn.close()


# =====================================================
# TEAM FUNCTIONS
# =====================================================

def create_team_with_auto_credentials(department):
    conn = get_connection()
    cursor = conn.cursor()

    prefix = department[:2].lower()

    cursor.execute(
        "SELECT COUNT(*) as count FROM teams WHERE department=?",
        (department,)
    )
    count = cursor.fetchone()["count"]
    next_number = count + 1

    team_id = f"{prefix}-{str(next_number).zfill(3)}"

    password = ''.join(random.choices(
        string.ascii_letters + string.digits, k=8
    ))

    cursor.execute("""
        INSERT INTO teams (team_id, department, password)
        VALUES (?, ?, ?)
    """, (team_id, department, password))

    conn.commit()
    conn.close()

    return team_id, password


def get_team_by_team_id(team_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM teams WHERE team_id=?", (team_id,))
    team = cursor.fetchone()
    conn.close()
    return team


def get_all_teams():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM teams")
    teams = cursor.fetchall()
    conn.close()
    return teams


# =====================================================
# TICKET FUNCTIONS
# =====================================================

def insert_ticket(ticket_data):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO tickets
        (ticket_id, title, description, department, priority,
         created_at, username, name, email, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        ticket_data["ticket_id"],
        ticket_data["title"],
        ticket_data["description"],
        ticket_data["department"],
        ticket_data["priority"],
        ticket_data["created_at"],
        ticket_data["username"],
        ticket_data["name"],
        ticket_data["email"],
        ticket_data["status"]
    ))
    conn.commit()
    conn.close()


def get_user_tickets(username):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT *
        FROM tickets
        WHERE username=?
        ORDER BY created_at DESC
    """, (username,))
    tickets = cursor.fetchall()
    conn.close()
    return tickets


def get_all_tickets():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            t.*,
            ta.team_id AS assigned_team_id,
            tm.department AS assigned_team_department
        FROM tickets t
        LEFT JOIN ticket_assignments ta 
            ON t.ticket_id = ta.ticket_id
        LEFT JOIN teams tm
            ON ta.team_id = tm.team_id
        ORDER BY t.created_at DESC
    """)

    tickets = cursor.fetchall()
    conn.close()
    return tickets

def get_ticket_by_id(ticket_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tickets WHERE ticket_id=?", (ticket_id,))
    ticket = cursor.fetchone()
    conn.close()
    return ticket


def update_ticket_status(ticket_id, new_status, closure_reason=None, closed_by=None):
    conn = get_connection()
    cursor = conn.cursor()

    if closure_reason:
        cursor.execute("""
            UPDATE tickets
            SET status=?, closure_reason=?, closed_by=?
            WHERE ticket_id=?
        """, (new_status, closure_reason, closed_by, ticket_id))
    else:
        cursor.execute("""
            UPDATE tickets
            SET status=?
            WHERE ticket_id=?
        """, (new_status, ticket_id))

    conn.commit()
    conn.close()


# ================= USER DASHBOARD HELPERS =================

def get_status_counts_for_user(username):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT status, COUNT(*) as count
        FROM tickets
        WHERE username=?
        GROUP BY status
    """, (username,))
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_resolved_tickets_for_user(username):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ticket_id, title, created_at
        FROM tickets
        WHERE username=? AND status='Resolved'
        ORDER BY created_at DESC
    """, (username,))
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_recent_tickets_for_user(username):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ticket_id, title, status, created_at
        FROM tickets
        WHERE username=?
        ORDER BY created_at DESC
        LIMIT 5
    """, (username,))
    rows = cursor.fetchall()
    conn.close()
    return rows

# =====================================================
# DASHBOARD ANALYTICS FUNCTIONS
# =====================================================

def get_status_distribution():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT status, COUNT(*) as count
        FROM tickets
        GROUP BY status
    """)

    rows = cursor.fetchall()
    conn.close()

    # 🔥 Convert Row objects to normal dict
    return [dict(row) for row in rows]


def get_department_distribution():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT department, COUNT(*) as count
        FROM tickets
        GROUP BY department
    """)

    rows = cursor.fetchall()
    conn.close()

    # 🔥 Convert Row objects to normal dict
    return [dict(row) for row in rows]

# =====================================================
# ASSIGNMENT FUNCTIONS
# =====================================================

def assign_ticket_to_team(ticket_id, team_id, assigned_by):
    conn = get_connection()
    cursor = conn.cursor()

    # Remove previous assignment (if exists)
    cursor.execute("""
        DELETE FROM ticket_assignments
        WHERE ticket_id=?
    """, (ticket_id,))

    # Insert new assignment
    cursor.execute("""
        INSERT INTO ticket_assignments (ticket_id, team_id, assigned_by)
        VALUES (?, ?, ?)
    """, (ticket_id, team_id, assigned_by))

    conn.commit()
    conn.close()
def get_ticket_by_id(ticket_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            t.*,
            ta.team_id AS assigned_team_id,
            tm.department AS assigned_team_department
        FROM tickets t
        LEFT JOIN ticket_assignments ta 
            ON t.ticket_id = ta.ticket_id
        LEFT JOIN teams tm
            ON ta.team_id = tm.team_id
        WHERE t.ticket_id=?
    """, (ticket_id,))

    ticket = cursor.fetchone()
    conn.close()
    return ticket
def get_filtered_tickets(
    role,
    username=None,
    team_id=None,
    search=None,
    status=None,
    priority=None,
    department=None,
    sort=None
):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT 
            t.*,
            ta.team_id AS assigned_team_id,
            tm.department AS assigned_team_department
        FROM tickets t
        LEFT JOIN ticket_assignments ta 
            ON t.ticket_id = ta.ticket_id
        LEFT JOIN teams tm
            ON ta.team_id = tm.team_id
        WHERE 1=1
    """

    params = []

    # ================= ROLE RESTRICTION =================

    if role == "user":
        query += " AND t.username = ?"
        params.append(username)

    elif role in ["team_admin", "team_member"]:
        query += """
            AND t.ticket_id IN (
                SELECT ticket_id FROM ticket_assignments WHERE team_id = ?
            )
        """
        params.append(team_id)

    # Admin sees all → no restriction

    # ================= SEARCH =================

    if search:
        query += """
            AND (
                t.title LIKE ?
                OR t.ticket_id LIKE ?
                OR t.username LIKE ?
            )
        """
        params.extend([f"%{search}%"] * 3)

    # ================= FILTERS =================

    if status:
        query += " AND t.status = ?"
        params.append(status)

    if priority:
        query += " AND t.priority = ?"
        params.append(priority)

    if department:
        query += " AND t.department = ?"
        params.append(department)

    if role == "admin" and team_id:
        query += """
            AND t.ticket_id IN (
                SELECT ticket_id FROM ticket_assignments WHERE team_id = ?
            )
        """
        params.append(team_id)

    # ================= SORTING =================

    if sort == "newest":
        query += " ORDER BY t.created_at DESC"

    elif sort == "oldest":
        query += " ORDER BY t.created_at ASC"

    elif sort == "priority":
        query += """
            ORDER BY 
                CASE t.priority
                    WHEN 'High' THEN 1
                    WHEN 'Medium' THEN 2
                    WHEN 'Low' THEN 3
                END
        """

    elif sort == "status":
        query += " ORDER BY t.status ASC"

    else:
        query += " ORDER BY t.created_at DESC"

    cursor.execute(query, params)
    tickets = cursor.fetchall()
    conn.close()

    return tickets

def get_team_tickets(team_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT t.*
        FROM tickets t
        JOIN ticket_assignments ta ON t.ticket_id = ta.ticket_id
        WHERE ta.team_id=?
        ORDER BY t.created_at DESC
    """, (team_id,))
    tickets = cursor.fetchall()
    conn.close()
    return tickets


# =====================================================
# KPI FUNCTIONS
# =====================================================

def get_team_kpis(team_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT status, COUNT(*) as count
        FROM tickets t
        JOIN ticket_assignments ta ON t.ticket_id = ta.ticket_id
        WHERE ta.team_id=?
        GROUP BY status
    """, (team_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_total_ticket_count():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM tickets")
    count = cursor.fetchone()["count"]
    conn.close()
    return count


def get_assigned_ticket_count():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM ticket_assignments")
    count = cursor.fetchone()["count"]
    conn.close()
    return count


def get_unassigned_ticket_count():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) as count
        FROM tickets
        WHERE ticket_id NOT IN (SELECT ticket_id FROM ticket_assignments)
    """)
    count = cursor.fetchone()["count"]
    conn.close()
    return count


def get_high_priority_unassigned():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) as count
        FROM tickets
        WHERE priority='High'
        AND ticket_id NOT IN (SELECT ticket_id FROM ticket_assignments)
    """)
    count = cursor.fetchone()["count"]
    conn.close()
    return count


# =====================================================
# ACTIVITY LOGGING
# =====================================================

def log_activity(ticket_id, action_type, performed_by, role, remarks):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO activity_logs
        (ticket_id, action_type, performed_by, role, remarks)
        VALUES (?, ?, ?, ?, ?)
    """, (ticket_id, action_type, performed_by, role, remarks))
    conn.commit()
    conn.close()


def get_team_activity(team_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT *
        FROM activity_logs
        WHERE ticket_id IN (
            SELECT ticket_id FROM ticket_assignments WHERE team_id=?
        )
        ORDER BY timestamp DESC
        LIMIT 20
    """, (team_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_system_activity():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT *
        FROM activity_logs
        ORDER BY timestamp DESC
        LIMIT 20
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows
def get_user_by_id(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE id=?", (user_id,))
    user = cursor.fetchone()

    conn.close()
    return user
def update_profile_details(user_id, phone, bio, location, designation):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE users
        SET phone=?, bio=?, location=?, designation=?
        WHERE id=?
    """, (phone, bio, location, designation, user_id))

    conn.commit()
    conn.close()