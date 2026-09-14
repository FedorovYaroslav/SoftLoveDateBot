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
    get_invitation,
    get_options,
    save_invitation_choice,
)


load_dotenv()


BOT_TOKEN = os.getenv("BOT_TOKEN")


if not BOT_TOKEN:
    raise ValueError(
        "BOT_TOKEN не найден в .env"
    )


app = FastAPI()


TELEGRAM_IP = "149.154.166.110"
TELEGRAM_HOST = "api.telegram.org"


# ==========================================
# ЗАПРОСЫ К TELEGRAM API
# ==========================================

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
        "--connect-timeout",
        "10",
        "--max-time",
        "30",
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


def send_telegram_message(chat_id, text):
    import urllib.parse

    encoded_text = urllib.parse.quote(text)

    status, body = telegram_request(
        f"/bot{BOT_TOKEN}/sendMessage"
        f"?chat_id={chat_id}"
        f"&text={encoded_text}"
    )

    if status != 200:
        raise RuntimeError(
            f"Telegram sendMessage вернул HTTP {status}"
        )

    data = json.loads(
        body.decode("utf-8")
    )

    if not data.get("ok"):
        raise RuntimeError(
            f"Telegram не отправил сообщение: {data}"
        )

# ==========================================
# ПОЛУЧИТЬ ПРИГЛАШЕНИЕ
# ==========================================

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

        "id":
            invitation["id"],

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

        # ==================================
        # НАЗНАЧЕННАЯ ДАТА И ВРЕМЯ
        # ==================================

        "selected_date":
            invitation["selected_date"],

        "selected_time":
            invitation["selected_time"],

        # ==================================
        # ВАРИАНТЫ СВИДАНИЯ
        # ==================================

        "options": [

            {
                "id":
                    option["id"],

                "emoji":
                    option["emoji"],

                "title":
                    option["title"],
            }

            for option in options
        ],
    }


# ==========================================
# СОХРАНИТЬ ВЫБОР ПОЛУЧАТЕЛЯ
# ==========================================

@app.post("/api/invitation/{invitation_id}/choice")
def save_choice(invitation_id: int, data: dict):
    selected_option = data.get("selected_option")
    selected_date = data.get("selected_date")
    selected_time = data.get("selected_time")

    if not selected_option:
        raise HTTPException(
            status_code=400,
            detail="Не выбран вариант свидания"
        )

    invitation = get_invitation(invitation_id)

    if invitation is None:
        raise HTTPException(
            status_code=404,
            detail="Приглашение не найдено"
        )

    save_invitation_choice(
        invitation_id=invitation_id,
        selected_option=selected_option,
        selected_date=selected_date,
        selected_time=selected_time,
    )

    creator_chat_id = invitation["creator_chat_id"]

    if creator_chat_id:
        recipient_name = invitation["recipient_name"]

        message_text = (
            f"💌 {recipient_name} выбрала свидание!\n\n"
            f"✨ {selected_option}\n"
        )

        if selected_date:
            message_text += (
                f"📅 Дата: {selected_date}\n"
            )

        if selected_time:
            message_text += (
                f"⏰ Время: {selected_time}\n"
            )

        try:
            send_telegram_message(
                creator_chat_id,
                message_text,
            )
        except Exception as error:
            print(
                "⚠️ Не удалось отправить "
                f"уведомление создателю: {error}"
            )

    return {
        "ok": True,
        "message": "Выбор сохранён",
    }


# ==========================================
# ПОЛУЧИТЬ ФОТОГРАФИЮ ИЗ TELEGRAM
# ==========================================

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


    # --------------------------------------
    # Получаем путь к файлу
    # --------------------------------------

    try:

        status, body = telegram_request(

            f"/bot{BOT_TOKEN}"
            f"/getFile"
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


    # --------------------------------------
    # Разбираем ответ Telegram
    # --------------------------------------

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
    ][
        "file_path"
    ]


    # --------------------------------------
    # Скачиваем фотографию
    # --------------------------------------

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


    # --------------------------------------
    # Отдаём фотографию браузеру
    # --------------------------------------

    return StreamingResponse(

        io.BytesIO(
            photo_data
        ),

        media_type="image/jpeg",
    )


# ==========================================
# WEB APP
# ==========================================

app.mount(

    "/",

    StaticFiles(
        directory="web",
        html=True,
    ),

    name="web",
)