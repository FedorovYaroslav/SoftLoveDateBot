import asyncio
import os
import socket
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from dotenv import load_dotenv

from database import (
    create_invitation,
    add_option,
    save_assigned_datetime,
)


# ==========================================
# TELEGRAM: ПРИНУДИТЕЛЬНО ИСПОЛЬЗУЕМ IPv4
# ==========================================

_original_getaddrinfo = socket.getaddrinfo


def telegram_ipv4_only(host, port, *args, **kwargs):
    results = _original_getaddrinfo(
        host,
        port,
        *args,
        **kwargs,
    )

    return [
        result
        for result in results
        if result[0] == socket.AF_INET
    ]


socket.getaddrinfo = telegram_ipv4_only


# ==========================================
# НАСТРОЙКИ
# ==========================================

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError(
        "Не найден BOT_TOKEN в файле .env"
    )


dp = Dispatcher()


# ==========================================
# СОСТОЯНИЯ
# ==========================================

class Invitation(StatesGroup):
    recipient_name = State()
    sender_name = State()

    date_options = State()
    editing_option = State()
    adding_option = State()

    personal_message = State()
    photo = State()

    date_mode = State()

    assigned_date = State()
    assigned_time = State()


# ==========================================
# ГОТОВЫЕ ВАРИАНТЫ СВИДАНИЯ
# ==========================================

DEFAULT_OPTIONS = [
    {
        "id": "coffee",
        "emoji": "☕",
        "title": "Выпить кофе",
    },
    {
        "id": "dinner",
        "emoji": "🍷",
        "title": "Сходить на ужин",
    },
    {
        "id": "cinema",
        "emoji": "🎬",
        "title": "Сходить в кино",
    },
    {
        "id": "walk",
        "emoji": "🌳",
        "title": "Погулять вместе",
    },
    {
        "id": "exhibition",
        "emoji": "🎨",
        "title": "Сходить на выставку",
    },
]


# ==========================================
# КЛАВИАТУРЫ
# ==========================================

main_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="💌 Создать приглашение",
                callback_data="create_invitation",
            )
        ]
    ]
)


def options_keyboard(options):
    buttons = []

    for index, option in enumerate(options):
        buttons.append(
            [
                InlineKeyboardButton(
                    text=(
                        f"{option['emoji']} "
                        f"{option['title']}"
                    ),
                    callback_data=(
                        f"select_option:{index}"
                    ),
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text="➕ Добавить свой вариант",
                callback_data="add_custom_option",
            )
        ]
    )

    buttons.append(
        [
            InlineKeyboardButton(
                text="➡️ Готово",
                callback_data="options_done",
            )
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=buttons
    )


def edit_option_keyboard(index):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✏️ Изменить",
                    callback_data=(
                        f"edit_option:{index}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗑 Удалить",
                    callback_data=(
                        f"delete_option:{index}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="back_to_options",
                )
            ],
        ]
    )


photo_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📷 Добавить фото",
                callback_data="add_photo",
            )
        ],
        [
            InlineKeyboardButton(
                text="Пропустить →",
                callback_data="skip_photo",
            )
        ],
    ]
)


date_mode_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="❤️ Я назначу дату и время",
                callback_data="date_mode:sender",
            )
        ],
        [
            InlineKeyboardButton(
                text="💌 Пусть выберет получатель",
                callback_data="date_mode:recipient",
            )
        ],
    ]
)


# ==========================================
# START
# ==========================================

@dp.message(CommandStart())
async def start_handler(message: Message):
    await message.answer(
        "💌 Привет!\n\n"
        "Я помогу тебе создать красивое "
        "приглашение на свидание ❤️\n\n"
        "Это займёт всего пару минут.",
        reply_markup=main_keyboard,
    )


# ==========================================
# НАЧАЛО СОЗДАНИЯ
# ==========================================

@dp.callback_query(
    F.data == "create_invitation"
)
async def create_invitation_handler(
    callback: CallbackQuery,
    state: FSMContext,
):
    await state.set_state(
        Invitation.recipient_name
    )
    await state.update_data(
        creator_chat_id=callback.from_user.id
    )
    await callback.message.answer(
        "❤️ Как зовут человека, "
        "которого ты хочешь пригласить?"
    )

    await callback.answer()


# ==========================================
# ИМЯ ПОЛУЧАТЕЛЯ
# ==========================================

@dp.message(Invitation.recipient_name)
async def recipient_name_handler(
    message: Message,
    state: FSMContext,
):
    await state.update_data(
        recipient_name=message.text
    )

    await state.set_state(
        Invitation.sender_name
    )

    await message.answer(
        "Прекрасно ❤️\n\n"
        "Как тебя зовут?"
    )


# ==========================================
# ИМЯ ОТПРАВИТЕЛЯ
# ==========================================

@dp.message(Invitation.sender_name)
async def sender_name_handler(
    message: Message,
    state: FSMContext,
):
    options = [
        option.copy()
        for option in DEFAULT_OPTIONS
    ]

    await state.update_data(
        sender_name=message.text,
        options=options,
    )

    await state.set_state(
        Invitation.date_options
    )

    await message.answer(
        "Отлично ❤️\n\n"
        "Теперь выбери идеи для свидания.\n\n"
        "Ты можешь:\n"
        "• выбрать готовую идею\n"
        "• изменить её\n"
        "• удалить\n"
        "• добавить свою",
        reply_markup=options_keyboard(
            options
        ),
    )


# ==========================================
# ВЫБОР ВАРИАНТА
# ==========================================

@dp.callback_query(
    Invitation.date_options,
    F.data.startswith("select_option:")
)
async def select_option(
    callback: CallbackQuery,
    state: FSMContext,
):
    index = int(
        callback.data.split(":")[1]
    )

    data = await state.get_data()

    options = data.get(
        "options",
        []
    )

    if index >= len(options):
        await callback.answer(
            "Этот вариант больше недоступен."
        )
        return

    option = options[index]

    await callback.message.edit_text(
        f"{option['emoji']} "
        f"{option['title']}\n\n"
        "Что хочешь сделать "
        "с этим вариантом?",
        reply_markup=edit_option_keyboard(
            index
        ),
    )

    await callback.answer()


# ==========================================
# РЕДАКТИРОВАНИЕ
# ==========================================

@dp.callback_query(
    F.data.startswith("edit_option:")
)
async def edit_option(
    callback: CallbackQuery,
    state: FSMContext,
):
    index = int(
        callback.data.split(":")[1]
    )

    await state.update_data(
        editing_index=index
    )

    await state.set_state(
        Invitation.editing_option
    )

    await callback.message.answer(
        "✏️ Напиши новое название "
        "этого варианта."
    )

    await callback.answer()


@dp.message(Invitation.editing_option)
async def save_edited_option(
    message: Message,
    state: FSMContext,
):
    data = await state.get_data()

    options = data.get(
        "options",
        []
    )

    index = data.get(
        "editing_index"
    )

    if (
        index is not None
        and index < len(options)
    ):
        options[index]["title"] = (
            message.text
        )

    await state.update_data(
        options=options
    )

    await state.set_state(
        Invitation.date_options
    )

    await message.answer(
        "✅ Готово! Вариант изменён.",
        reply_markup=options_keyboard(
            options
        ),
    )


# ==========================================
# УДАЛЕНИЕ
# ==========================================

@dp.callback_query(
    F.data.startswith("delete_option:")
)
async def delete_option(
    callback: CallbackQuery,
    state: FSMContext,
):
    index = int(
        callback.data.split(":")[1]
    )

    data = await state.get_data()

    options = data.get(
        "options",
        []
    )

    if index < len(options):
        deleted = options.pop(index)

        await state.update_data(
            options=options
        )

        await callback.message.edit_text(
            f"🗑 Удалили:\n"
            f"{deleted['emoji']} "
            f"{deleted['title']}\n\n"
            "Оставшиеся варианты:",
            reply_markup=options_keyboard(
                options
            ),
        )

    await callback.answer()


# ==========================================
# НАЗАД
# ==========================================

@dp.callback_query(
    F.data == "back_to_options"
)
async def back_to_options(
    callback: CallbackQuery,
    state: FSMContext,
):
    data = await state.get_data()

    options = data.get(
        "options",
        []
    )

    await callback.message.edit_text(
        "💌 Варианты свидания:",
        reply_markup=options_keyboard(
            options
        ),
    )

    await callback.answer()


# ==========================================
# ДОБАВИТЬ СВОЙ ВАРИАНТ
# ==========================================

@dp.callback_query(
    F.data == "add_custom_option"
)
async def add_custom_option(
    callback: CallbackQuery,
    state: FSMContext,
):
    await state.set_state(
        Invitation.adding_option
    )

    await callback.message.answer(
        "✨ Напиши свой вариант "
        "свидания.\n\n"
        "Например:\n"
        "🚲 Покататься на велосипедах "
        "по набережной"
    )

    await callback.answer()


@dp.message(Invitation.adding_option)
async def save_custom_option(
    message: Message,
    state: FSMContext,
):
    data = await state.get_data()

    options = data.get(
        "options",
        []
    )

    options.append(
        {
            "id": (
                f"custom_{len(options)}"
            ),
            "emoji": "✨",
            "title": message.text,
        }
    )

    await state.update_data(
        options=options
    )

    await state.set_state(
        Invitation.date_options
    )

    await message.answer(
        "❤️ Добавил твой вариант!",
        reply_markup=options_keyboard(
            options
        ),
    )


# ==========================================
# ВАРИАНТЫ ГОТОВЫ
# ==========================================

@dp.callback_query(
    Invitation.date_options,
    F.data == "options_done"
)
async def options_done(
    callback: CallbackQuery,
    state: FSMContext,
):
    data = await state.get_data()

    options = data.get(
        "options",
        []
    )

    if not options:
        await callback.answer(
            "Добавь хотя бы один "
            "вариант ❤️",
            show_alert=True,
        )
        return

    await state.set_state(
        Invitation.personal_message
    )

    await callback.message.edit_text(
        "💌 Отлично!\n\n"
        "Теперь добавим немного "
        "личного ❤️\n\n"
        "Напиши сообщение, которое "
        "увидит получатель приглашения.\n\n"
        "Например:\n"
        "«Я хочу пригласить тебя "
        "на свидание ❤️ Выбирай "
        "вариант, который тебе "
        "больше нравится!»"
    )

    await callback.answer()


# ==========================================
# ЛИЧНОЕ СООБЩЕНИЕ
# ==========================================

@dp.message(Invitation.personal_message)
async def personal_message_handler(
    message: Message,
    state: FSMContext,
):
    await state.update_data(
        personal_message=message.text
    )

    await state.set_state(
        Invitation.photo
    )

    await message.answer(
        "📸 Хочешь добавить "
        "фотографию к приглашению?\n\n"
        "Она будет показана получателю.",
        reply_markup=photo_keyboard,
    )


# ==========================================
# ДОБАВИТЬ ФОТО
# ==========================================

@dp.callback_query(
    Invitation.photo,
    F.data == "add_photo"
)
async def add_photo(
    callback: CallbackQuery,
    state: FSMContext,
):
    await callback.message.answer(
        "📷 Отправь фотографию "
        "следующим сообщением."
    )

    await callback.answer()


@dp.message(
    Invitation.photo,
    F.photo
)
async def photo_handler(
    message: Message,
    state: FSMContext,
):
    photo = message.photo[-1]

    await state.update_data(
        photo_file_id=photo.file_id
    )

    await message.answer(
        "❤️ Фото добавлено!\n\n"
        "Теперь осталось решить,\n"
        "кто выберет дату и время "
        "свидания."
    )

    await state.set_state(
        Invitation.date_mode
    )

    await message.answer(
        "📅 Кто выбирает дату и время?",
        reply_markup=date_mode_keyboard,
    )


# ==========================================
# ПРОПУСТИТЬ ФОТО
# ==========================================

@dp.callback_query(
    Invitation.photo,
    F.data == "skip_photo"
)
async def skip_photo(
    callback: CallbackQuery,
    state: FSMContext,
):
    await state.update_data(
        photo_file_id=None
    )

    await callback.message.answer(
        "Хорошо ❤️\n\n"
        "Приглашение будет "
        "без фотографии."
    )

    await state.set_state(
        Invitation.date_mode
    )

    await callback.message.answer(
        "📅 Кто выбирает дату и время?",
        reply_markup=date_mode_keyboard,
    )

    await callback.answer()


# ==========================================
# СОЗДАНИЕ ПРИГЛАШЕНИЯ
# ==========================================

async def create_final_invitation(
    state: FSMContext,
    date_mode: str,
    selected_date=None,
    selected_time=None,
):
    data = await state.get_data()

    # --------------------------------------
    # СОЗДАЁМ ЗАПИСЬ
    # --------------------------------------

    invitation_id, public_token = (
        create_invitation(
            recipient_name=data["recipient_name"],
            sender_name=data["sender_name"],
            personal_message=data["personal_message"],
            photo_file_id=data.get("photo_file_id"),
            date_mode=date_mode,
            creator_chat_id=data.get("creator_chat_id"),
        )
    )

    # --------------------------------------
    # ДОБАВЛЯЕМ ВАРИАНТЫ
    # --------------------------------------

    options = data.get(
        "options",
        []
    )

    for index, option in enumerate(
        options
    ):
        add_option(
            invitation_id=invitation_id,
            emoji=option["emoji"],
            title=option["title"],
            sort_order=index,
        )

    # --------------------------------------
    # СОХРАНЯЕМ ДАТУ И ВРЕМЯ
    # --------------------------------------

    if date_mode == "sender":

        if not selected_date:
            raise ValueError(
                "Не передана дата свидания"
            )

        if not selected_time:
            raise ValueError(
                "Не передано время свидания"
            )

        save_assigned_datetime(
            invitation_id=invitation_id,
            selected_date=selected_date,
            selected_time=selected_time,
        )

    # --------------------------------------
    # СОЗДАЁМ TELEGRAM LINK
    # --------------------------------------

    bot_username = "SoftLoveDateBot"

    invitation_link = (
        f"https://t.me/"
        f"{bot_username}"
        f"?startapp={public_token}"
    )

    return (
        invitation_id,
        invitation_link,
    )


# ==========================================
# ЗАВЕРШЕНИЕ
# ==========================================

async def finish_invitation(
    callback: CallbackQuery,
    state: FSMContext,
    date_mode: str,
):
    invitation_id, invitation_link = (
        await create_final_invitation(
            state=state,
            date_mode=date_mode,
        )
    )

    data = await state.get_data()

    share_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💌 Открыть приглашение",
                    url=invitation_link,
                )
            ]
        ]
    )

    await callback.message.edit_text(
        "🎉 Приглашение готово!\n\n"
        f"Для: {data['recipient_name']}\n"
        f"От: {data['sender_name']}\n\n"
        "💌 Дату и время выберет "
        "получатель.\n\n"
        "Теперь эту ссылку можно "
        "отправить получателю ❤️",
        reply_markup=share_keyboard,
    )

    await state.clear()

    await callback.answer()


# ==========================================
# ВЫБОР РЕЖИМА ДАТЫ
# ==========================================

@dp.callback_query(
    Invitation.date_mode,
    F.data.startswith("date_mode:")
)
async def choose_date_mode(
    callback: CallbackQuery,
    state: FSMContext,
):
    date_mode = (
        callback.data.split(":")[1]
    )

    # --------------------------------------
    # СОЗДАТЕЛЬ НАЗНАЧАЕТ ДАТУ
    # --------------------------------------

    if date_mode == "sender":

        await state.update_data(
            date_mode="sender"
        )

        await state.set_state(
            Invitation.assigned_date
        )

        await callback.message.edit_text(
            "❤️ Отлично.\n\n"
            "Теперь укажи дату свидания.\n\n"
            "Напиши её в формате:\n"
            "15.09.2026"
        )

        await callback.answer()

        return

    # --------------------------------------
    # ПОЛУЧАТЕЛЬ ВЫБИРАЕТ ДАТУ
    # --------------------------------------

    await state.update_data(
        date_mode="recipient"
    )

    await finish_invitation(
        callback=callback,
        state=state,
        date_mode="recipient",
    )


# ==========================================
# ДАТА, НАЗНАЧЕННАЯ СОЗДАТЕЛЕМ
# ==========================================

@dp.message(Invitation.assigned_date)
async def assigned_date_handler(
    message: Message,
    state: FSMContext,
):
    date_text = message.text.strip()

    try:
        datetime.strptime(
            date_text,
            "%d.%m.%Y",
        )
    except ValueError:
        await message.answer(
            "Пожалуйста, укажи дату в формате:\n"
            "15.09.2026"
        )
        return

    await state.update_data(
        assigned_date=date_text
    )

    await state.set_state(
        Invitation.assigned_time
    )

    await message.answer(
        "⏰ Теперь укажи время свидания.\n\n"
        "Напиши его в формате:\n"
        "19:30"
    )


# ==========================================
# ВРЕМЯ, НАЗНАЧЕННОЕ СОЗДАТЕЛЕМ
# ==========================================

@dp.message(Invitation.assigned_time)
async def assigned_time_handler(
    message: Message,
    state: FSMContext,
):
    time_text = message.text.strip()

    try:
        datetime.strptime(
            time_text,
            "%H:%M",
        )
    except ValueError:
        await message.answer(
            "Пожалуйста, укажи время в формате:\n"
            "19:30"
        )
        return

    await state.update_data(
        assigned_time=time_text
    )

    data = await state.get_data()

    invitation_id, invitation_link = (
        await create_final_invitation(
            state=state,
            date_mode="sender",
            selected_date=data["assigned_date"],
            selected_time=time_text,
        )
    )

    share_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💌 Открыть приглашение",
                    url=invitation_link,
                )
            ]
        ]
    )

    await message.answer(
        "🎉 Приглашение готово!\n\n"
        f"Для: {data['recipient_name']}\n"
        f"От: {data['sender_name']}\n"
        f"📅 Дата: {data['assigned_date']}\n"
        f"⏰ Время: {time_text}\n\n"
        "Теперь эту ссылку можно "
        "отправить получателю ❤️",
        reply_markup=share_keyboard,
    )

    await state.clear()


# ==========================================
# ЗАПУСК БОТА
# ==========================================

async def main():
    import os

    if os.getenv("USE_PROXY", "false").lower() == "true":
        from curl_session import CurlSession

        session = CurlSession(
            proxy="127.0.0.1:10808",
            timeout=60,
        )

        bot = Bot(
            token=BOT_TOKEN,
            session=session,
        )
    else:
        bot = Bot(
            token=BOT_TOKEN,
        )

    print("💌 SoftLoveDateBot запущен!")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())