import os
import sqlite3
import secrets

import psycopg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
SQLITE_DATABASE_NAME = "softlove.db"


# ============================================================
# Подключение к базе
# ============================================================

def get_connection():
    """
    Если DATABASE_URL существует — используем PostgreSQL.
    Иначе используем локальный SQLite.
    """

    if DATABASE_URL:
        return psycopg.connect(DATABASE_URL)

    connection = sqlite3.connect(SQLITE_DATABASE_NAME)
    connection.row_factory = sqlite3.Row
    return connection


def is_postgres():
    return bool(DATABASE_URL)


# ============================================================
# Инициализация базы
# ============================================================

def init_database():
    connection = get_connection()
    cursor = connection.cursor()

    if is_postgres():
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS invitations (
                id SERIAL PRIMARY KEY,
                public_token TEXT UNIQUE,
                creator_chat_id BIGINT,
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
                id SERIAL PRIMARY KEY,
                invitation_id INTEGER NOT NULL,
                emoji TEXT NOT NULL,
                title TEXT NOT NULL,
                sort_order INTEGER NOT NULL,
                FOREIGN KEY (invitation_id)
                    REFERENCES invitations(id)
                    ON DELETE CASCADE
            )
        """)

    else:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS invitations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                public_token TEXT UNIQUE,
                creator_chat_id INTEGER,
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

        # Для старой локальной базы:
        # если creator_chat_id ещё не существует — добавляем его.
        try:
            cursor.execute(
                "ALTER TABLE invitations ADD COLUMN creator_chat_id INTEGER"
            )
        except sqlite3.OperationalError:
            pass

    connection.commit()
    connection.close()


# ============================================================
# Создание приглашения
# ============================================================

def create_invitation(
    recipient_name,
    sender_name,
    personal_message,
    photo_file_id,
    date_mode,
    creator_chat_id,
):
    connection = get_connection()
    cursor = connection.cursor()

    public_token = secrets.token_urlsafe(16)

    if is_postgres():
        cursor.execute("""
            INSERT INTO invitations (
                public_token,
                creator_chat_id,
                recipient_name,
                sender_name,
                personal_message,
                photo_file_id,
                date_mode
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            public_token,
            creator_chat_id,
            recipient_name,
            sender_name,
            personal_message,
            photo_file_id,
            date_mode,
        ))

        invitation_id = cursor.fetchone()[0]

    else:
        cursor.execute("""
            INSERT INTO invitations (
                public_token,
                creator_chat_id,
                recipient_name,
                sender_name,
                personal_message,
                photo_file_id,
                date_mode
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            public_token,
            creator_chat_id,
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


# ============================================================
# Добавление варианта свидания
# ============================================================

def add_option(
    invitation_id,
    emoji,
    title,
    sort_order,
):
    connection = get_connection()
    cursor = connection.cursor()

    if is_postgres():
        cursor.execute("""
            INSERT INTO date_options (
                invitation_id,
                emoji,
                title,
                sort_order
            )
            VALUES (%s, %s, %s, %s)
        """, (
            invitation_id,
            emoji,
            title,
            sort_order,
        ))

    else:
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


# ============================================================
# Получение приглашения по ID
# ============================================================

def get_invitation(invitation_id):
    connection = get_connection()
    cursor = connection.cursor()

    if is_postgres():
        cursor.execute("""
            SELECT *
            FROM invitations
            WHERE id = %s
        """, (invitation_id,))

        row = cursor.fetchone()

        if row is None:
            connection.close()
            return None

        columns = [column.name for column in cursor.description]
        result = dict(zip(columns, row))

    else:
        cursor.execute("""
            SELECT *
            FROM invitations
            WHERE id = ?
        """, (invitation_id,))

        row = cursor.fetchone()

        if row is None:
            connection.close()
            return None

        result = dict(row)

    connection.close()
    return result


# ============================================================
# Получение приглашения по публичному токену
# ============================================================

def get_invitation_by_token(public_token):
    connection = get_connection()
    cursor = connection.cursor()

    if is_postgres():
        cursor.execute("""
            SELECT *
            FROM invitations
            WHERE public_token = %s
        """, (public_token,))

        row = cursor.fetchone()

        if row is None:
            connection.close()
            return None

        columns = [column.name for column in cursor.description]
        result = dict(zip(columns, row))

    else:
        cursor.execute("""
            SELECT *
            FROM invitations
            WHERE public_token = ?
        """, (public_token,))

        row = cursor.fetchone()

        if row is None:
            connection.close()
            return None

        result = dict(row)

    connection.close()
    return result


# ============================================================
# Получение вариантов свидания
# ============================================================

def get_options(invitation_id):
    connection = get_connection()
    cursor = connection.cursor()

    if is_postgres():
        cursor.execute("""
            SELECT *
            FROM date_options
            WHERE invitation_id = %s
            ORDER BY sort_order
        """, (invitation_id,))

        rows = cursor.fetchall()

        columns = [column.name for column in cursor.description]
        result = [
            dict(zip(columns, row))
            for row in rows
        ]

    else:
        cursor.execute("""
            SELECT *
            FROM date_options
            WHERE invitation_id = ?
            ORDER BY sort_order
        """, (invitation_id,))

        rows = cursor.fetchall()

        result = [dict(row) for row in rows]

    connection.close()
    return result


# ============================================================
# Сохранение выбора получателя
# ============================================================

def save_invitation_choice(
    invitation_id,
    selected_option,
    selected_date,
    selected_time,
):
    connection = get_connection()
    cursor = connection.cursor()

    if is_postgres():
        cursor.execute("""
            UPDATE invitations
            SET
                selected_option = %s,
                selected_date = %s,
                selected_time = %s,
                status = 'selected'
            WHERE id = %s
        """, (
            selected_option,
            selected_date,
            selected_time,
            invitation_id,
        ))

    else:
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


# ============================================================
# Сохранение даты и времени, назначенных создателем
# ============================================================

def save_assigned_datetime(
    invitation_id,
    selected_date,
    selected_time,
):
    connection = get_connection()
    cursor = connection.cursor()

    if is_postgres():
        cursor.execute("""
            UPDATE invitations
            SET
                selected_date = %s,
                selected_time = %s
            WHERE id = %s
        """, (
            selected_date,
            selected_time,
            invitation_id,
        ))

    else:
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