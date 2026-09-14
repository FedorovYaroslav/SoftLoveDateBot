import sqlite3
import secrets


DATABASE_NAME = "softlove.db"


def get_connection():
    connection = sqlite3.connect(DATABASE_NAME)
    connection.row_factory = sqlite3.Row
    return connection


def init_database():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invitations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            public_token TEXT UNIQUE,
            recipient_name TEXT NOT NULL,
            sender_name TEXT NOT NULL,
            personal_message TEXT,
            photo_file_id TEXT,
            date_mode TEXT NOT NULL,
            selected_option TEXT,
            selected_date TEXT,
            selected_time TEXT,
            status TEXT NOT NULL DEFAULT 'created',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS date_options (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invitation_id INTEGER NOT NULL,
            emoji TEXT NOT NULL,
            title TEXT NOT NULL,
            sort_order INTEGER NOT NULL,
            FOREIGN KEY (invitation_id)
                REFERENCES invitations(id)
        )
    """)

    connection.commit()
    connection.close()


def create_invitation(
    recipient_name,
    sender_name,
    personal_message,
    photo_file_id,
    date_mode,
):
    connection = get_connection()
    cursor = connection.cursor()

    public_token = secrets.token_urlsafe(16)

    cursor.execute("""
        INSERT INTO invitations (
            public_token,
            recipient_name,
            sender_name,
            personal_message,
            photo_file_id,
            date_mode
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        public_token,
        recipient_name,
        sender_name,
        personal_message,
        photo_file_id,
        date_mode,
    ))

    invitation_id = cursor.lastrowid

    connection.commit()
    connection.close()

    return invitation_id, public_token


def add_option(
    invitation_id,
    emoji,
    title,
    sort_order,
):
    connection = get_connection()
    cursor = connection.cursor()

    if isinstance(invitation_id, tuple):
        invitation_id = invitation_id[0]

    invitation_id = int(invitation_id)

    cursor.execute("""
        INSERT INTO date_options (
            invitation_id,
            emoji,
            title,
            sort_order
        )
        VALUES (?, ?, ?, ?)
    """, (
        invitation_id,
        emoji,
        title,
        sort_order,
    ))

    connection.commit()
    connection.close()


def get_invitation(invitation_id):
    connection = get_connection()
    cursor = connection.cursor()

    if isinstance(invitation_id, tuple):
        invitation_id = invitation_id[0]

    invitation_id = int(invitation_id)

    cursor.execute("""
        SELECT *
        FROM invitations
        WHERE id = ?
    """, (invitation_id,))

    invitation = cursor.fetchone()

    connection.close()

    return invitation


def get_invitation_by_token(public_token):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT *
        FROM invitations
        WHERE public_token = ?
    """, (public_token,))

    invitation = cursor.fetchone()

    connection.close()

    return invitation


def get_options(invitation_id):
    connection = get_connection()
    cursor = connection.cursor()

    if isinstance(invitation_id, tuple):
        invitation_id = invitation_id[0]

    invitation_id = int(invitation_id)

    cursor.execute("""
        SELECT *
        FROM date_options
        WHERE invitation_id = ?
        ORDER BY sort_order
    """, (invitation_id,))

    options = cursor.fetchall()

    connection.close()

    return options


def save_invitation_choice(
    invitation_id,
    selected_option,
    selected_date,
    selected_time,
):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE invitations
        SET
            selected_option = ?,
            selected_date = ?,
            selected_time = ?,
            status = 'selected'
        WHERE id = ?
    """, (
        selected_option,
        selected_date,
        selected_time,
        invitation_id,
    ))

    connection.commit()
    connection.close()


def save_assigned_datetime(
    invitation_id,
    selected_date,
    selected_time,
):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE invitations
        SET
            selected_date = ?,
            selected_time = ?
        WHERE id = ?
    """, (
        selected_date,
        selected_time,
        invitation_id,
    ))

    connection.commit()
    connection.close()