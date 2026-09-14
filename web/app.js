const screens = {
    cover: document.getElementById("screen-cover"),
    invitation: document.getElementById("screen-invitation"),
    options: document.getElementById("screen-options"),
    datetime: document.getElementById("screen-datetime"),
    final: document.getElementById("screen-final"),
};


let invitation = null;
let selectedOption = null;


function showScreen(screen) {
    Object.values(screens).forEach((element) => {
        if (element) {
            element.classList.remove("active");
        }
    });

    if (screen) {
        screen.classList.add("active");
    }
}


async function loadInvitation() {

    const telegram = window.Telegram?.WebApp;

    let token = null;


    if (telegram) {

        telegram.ready();

        const startParam =
            telegram.initDataUnsafe?.start_param;

        if (startParam) {
            token = startParam;
        }
    }


    if (!token) {

        const urlParams =
            new URLSearchParams(
                window.location.search
            );

        token =
            urlParams.get("startapp");
    }


    if (!token) {

        console.error(
            "Не найден ключ приглашения"
        );

        return;
    }


    try {

        const response = await fetch(
            `/api/invitation/${token}`
        );


        if (!response.ok) {

            throw new Error(
                "Приглашение не найдено"
            );
        }


        invitation =
            await response.json();


        console.log(
            "Приглашение загружено:",
            invitation
        );


        renderInvitation();


    } catch (error) {

        console.error(
            "Ошибка загрузки приглашения:",
            error
        );
    }
}


function renderInvitation() {

    document.getElementById(
        "recipient-name"
    ).textContent =
        invitation.recipient_name;


    document.getElementById(
        "sender-name"
    ).textContent =
        invitation.sender_name;


    document.getElementById(
        "cover-recipient-name"
    ).textContent =
        invitation.recipient_name;


    document.getElementById(
        "cover-sender-name"
    ).textContent =
        invitation.sender_name;


    document.getElementById(
        "personal-message"
    ).textContent =
        invitation.personal_message;


    // =========================
    // ФОТО
    // =========================

    const photo =
        document.getElementById(
            "invitation-photo"
        );

    const photoPlaceholder =
        document.getElementById(
            "photo-placeholder"
        );


    if (!photo || !photoPlaceholder) {

        console.error(
            "Элементы фотографии не найдены в index.html"
        );

    } else if (invitation.photo_file_id) {

        console.log(
            "Photo file_id:",
            invitation.photo_file_id
        );


        const photoUrl =
            `/api/photo/${encodeURIComponent(
                invitation.photo_file_id
            )}`;


        console.log(
            "Загружаем фото:",
            photoUrl
        );


        photo.src = photoUrl;

        photo.style.display = "block";

        photoPlaceholder.style.display =
            "none";


        photo.onload = () => {

            console.log(
                "Фото успешно загружено"
            );

            photo.style.display =
                "block";

            photoPlaceholder.style.display =
                "none";
        };


        photo.onerror = (error) => {

            console.error(
                "Ошибка загрузки фотографии:",
                error
            );

            console.error(
                "URL фотографии:",
                photoUrl
            );

            photo.style.display =
                "none";

            photoPlaceholder.style.display =
                "flex";
        };


    } else {

        console.log(
            "У приглашения нет фотографии"
        );

        photo.style.display =
            "none";

        photoPlaceholder.style.display =
            "flex";
    }


    renderOptions();
}


function renderOptions() {

    const container =
        document.getElementById(
            "date-options"
        );


    container.innerHTML = "";


    invitation.options.forEach(
        (option) => {

            const button =
                document.createElement(
                    "button"
                );


            button.className =
                "date-option";


            button.innerHTML = `
                <span class="date-option-emoji">
                    ${option.emoji}
                </span>

                <span class="date-option-title">
                    ${option.title}
                </span>
            `;


            button.addEventListener(
                "click",
                () => {

                    selectedOption =
                        option;


                    document
                        .querySelectorAll(
                            ".date-option"
                        )
                        .forEach(
                            (element) => {
                                element.classList.remove(
                                    "selected"
                                );
                            }
                        );


                    button.classList.add(
                        "selected"
                    );


                    if (
                        invitation.date_mode ===
                        "recipient"
                    ) {

                        showScreen(
                            screens.datetime
                        );

                        return;
                    }


                    saveChoiceAndFinish();
                }
            );


            container.appendChild(
                button
            );
        }
    );
}


async function saveChoiceAndFinish() {

    if (
        !invitation ||
        !selectedOption
    ) {

        return;
    }


    const dateInput =
        document.getElementById(
            "date-input"
        );


    const timeInput =
        document.getElementById(
            "time-input"
        );


    const selectedDate =
        dateInput?.value || null;


    const selectedTime =
        timeInput?.value || null;


    try {

        const response =
            await fetch(
                `/api/invitation/${invitation.id}/choice`,
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json",
                    },

                    body: JSON.stringify({

                        selected_option:
                            selectedOption.title,

                        selected_date:
                            selectedDate,

                        selected_time:
                            selectedTime,
                    }),
                }
            );


        if (!response.ok) {

            throw new Error(
                "Не удалось сохранить выбор"
            );
        }


        let resultText =
            selectedOption.title;


        if (selectedDate) {

            resultText +=
                `\n${selectedDate}`;
        }


        if (selectedTime) {

            resultText +=
                ` · ${selectedTime}`;
        }


        document.getElementById(
            "selected-date"
        ).textContent =
            resultText;


        showScreen(
            screens.final
        );


    } catch (error) {

        console.error(
            "Ошибка сохранения:",
            error
        );


        alert(
            "Не получилось сохранить выбор. Попробуй ещё раз."
        );
    }
}


// =========================
// ПОДТВЕРЖДЕНИЕ ДАТЫ
// =========================

document
    .getElementById(
        "confirm-datetime"
    )
    ?.addEventListener(
        "click",
        () => {

            const dateInput =
                document.getElementById(
                    "date-input"
                );


            const timeInput =
                document.getElementById(
                    "time-input"
                );


            if (!dateInput.value) {

                alert(
                    "Пожалуйста, выбери день."
                );

                return;
            }


            if (!timeInput.value) {

                alert(
                    "Пожалуйста, выбери время."
                );

                return;
            }


            saveChoiceAndFinish();
        }
    );


// =========================
// НАЗАД К ВАРИАНТАМ
// =========================

document
    .getElementById(
        "back-to-options-from-datetime"
    )
    ?.addEventListener(
        "click",
        () => {

            showScreen(
                screens.options
            );
        }
    );


// =========================
// ОТКРЫТЬ ПРИГЛАШЕНИЕ
// =========================

document
    .getElementById(
        "open-invitation"
    )
    ?.addEventListener(
        "click",
        () => {

            showScreen(
                screens.invitation
            );
        }
    );


// =========================
// ПОКАЗАТЬ ВАРИАНТЫ
// =========================

document
    .getElementById(
        "show-options"
    )
    ?.addEventListener(
        "click",
        () => {

            showScreen(
                screens.options
            );
        }
    );


// =========================
// НАЗАД К ВАРИАНТАМ
// =========================

document
    .getElementById(
        "back-to-options"
    )
    ?.addEventListener(
        "click",
        () => {

            showScreen(
                screens.options
            );
        }
    );


// =========================
// ЗАПУСК
// =========================

loadInvitation();