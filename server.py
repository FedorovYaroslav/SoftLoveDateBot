from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

import io
import os
import json
import subprocess

from dotenv import load_dotenv

from database import (
    get_invitation_by_token,
    get_options,
    save_invitation_choice,
)


# =========================
# НАСТРОЙКИ
# =========================

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError(
        "BOT_TOKEN не найден в .env"
    )


app = FastAPI()


# =========================
# TELEGRAM
# =========================

TELEGRAM_IP = "149.154.166.110"

TELEGRAM_HOST = "api.telegram.org"


# =========================
# ЗАПРОС К TELEGRAM API
# =========================

def telegram_request(path):

    url = (
        f"https://{TELEGRAM_HOST}"
        f"{path}"
    )

    command = [
        "curl",
        "--silent",
        "--show-error",
        "--location",

        # Не ждать соединение бесконечно
        "--connect-timeout",
        "10",

        # Не ждать ответ бесконечно
        "--max-time",
        "30",

        # Используем рабочий IP Telegram
        "--resolve",
        f"{TELEGRAM_HOST}:443:{TELEGRAM_IP}",

        url,
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        timeout=35,
    )

    if result.returncode != 0:

        error_text = result.stderr.decode(
            "utf-8",
            errors="replace",
        )

        raise RuntimeError(
            error_text
        )

    return 200, result.stdout


# =========================
# ПРИГЛАШЕНИЕ
# =========================

@app.get(
    "/api/invitation/{public_token}"
)
def get_invitation_data(
    public_token: str
):

    invitation = get_invitation_by_token(
        public_token
    )

    if invitation is None:

        raise HTTPException(
            status_code=404,
            detail="Приглашение не найдено",
        )

    options = get_options(
        invitation["id"]
    )

    return {
        "id": invitation["id"],

        "recipient_name":
            invitation["recipient_name"],

        "sender_name":
            invitation["sender_name"],

        "personal_message":
            invitation["personal_message"],

        "photo_file_id":
            invitation["photo_file_id"],

        "date_mode":
            invitation["date_mode"],

        "options": [
            {
                "id": option["id"],
                "emoji": option["emoji"],
                "title": option["title"],
            }
            for option in options
        ],
    }


# =========================
# СОХРАНЕНИЕ ВЫБОРА
# =========================

@app.post(
    "/api/invitation/{invitation_id}/choice"
)
def save_choice(
    invitation_id: int,
    data: dict,
):

    selected_option = data.get(
        "selected_option"
    )

    selected_date = data.get(
        "selected_date"
    )

    selected_time = data.get(
        "selected_time"
    )

    if not selected_option:

        raise HTTPException(
            status_code=400,
            detail="Не выбран вариант свидания",
        )

    save_invitation_choice(
        invitation_id=invitation_id,
        selected_option=selected_option,
        selected_date=selected_date,
        selected_time=selected_time,
    )

    return {
        "ok": True,
        "message": "Выбор сохранён",
    }


# =========================
# ФОТО
# =========================

@app.get(
    "/api/photo/{file_id}"
)
def get_photo(
    file_id: str
):

    if not BOT_TOKEN:

        raise HTTPException(
            status_code=500,
            detail="BOT_TOKEN не найден",
        )

    # =====================
    # 1. Получаем путь файла
    # =====================

    try:

        status, body = telegram_request(
            f"/bot{BOT_TOKEN}/getFile"
            f"?file_id={file_id}"
        )

    except Exception as error:

        raise HTTPException(
            status_code=502,
            detail=(
                "Не удалось связаться "
                f"с Telegram: {error}"
            ),
        )

    if status != 200:

        raise HTTPException(
            status_code=502,
            detail=(
                "Telegram API вернул "
                f"HTTP {status}"
            ),
        )

    try:

        data = json.loads(
            body.decode("utf-8")
        )

    except Exception:

        raise HTTPException(
            status_code=502,
            detail=(
                "Telegram вернул "
                "неверный ответ"
            ),
        )

    if not data.get("ok"):

        raise HTTPException(
            status_code=404,
            detail=(
                "Telegram не нашёл "
                "этот файл"
            ),
        )

    file_path = data[
        "result"
    ]["file_path"]

    # =====================
    # 2. Скачиваем фото
    # =====================

    try:

        status, photo_data = (
            telegram_request(
                f"/file/bot"
                f"{BOT_TOKEN}/"
                f"{file_path}"
            )
        )

    except Exception as error:

        raise HTTPException(
            status_code=502,
            detail=(
                "Не удалось скачать "
                f"фото: {error}"
            ),
        )

    if status != 200:

        raise HTTPException(
            status_code=502,
            detail=(
                "Не удалось скачать "
                f"фото. HTTP {status}"
            ),
        )

    # =====================
    # 3. Возвращаем фото
    # =====================

    return StreamingResponse(
        io.BytesIO(photo_data),
        media_type="image/jpeg",
    )


# =========================
# ВЕБ-САЙТ
# =========================

app.mount(
    "/",
    StaticFiles(
        directory="web",
        html=True,
    ),
    name="web",
)