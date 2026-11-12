const API_URL = "http://127.0.0.1:8000";


async function checkConnection() {
    const statusElement = document.querySelector("#connection-status");

    try {
        const response = await fetch(`${API_URL}/status`);

        if (!response.ok) {
            throw new Error("Ошибка ответа сервера");
        }

        const data = await response.json();

        statusElement.textContent = "Сервер подключён";
        statusElement.className = "connection-status online";

        console.log("Информация о ноде:", data);

    } catch (error) {
        statusElement.textContent = "Нет подключения к серверу";
        statusElement.className = "connection-status offline";

        console.error("Ошибка подключения:", error);
    }
}

const registrationForm = document.querySelector("#registration-form");

registrationForm.addEventListener("submit", async function(event) {
    event.preventDefault();
    // Получаем значения полей формы
    const landId = document.querySelector("#land-id").value.trim();
    const owner = document.querySelector("#owner").value.trim();
    const address = document.querySelector("#address").value.trim();
    const area = document.querySelector("#area").value.trim();

    const message = document.querySelector("#registration-message");

    // Очищаем предыдущее сообщение
    message.textContent = "";
    message.className = "";

    // Проверяем заполнение всех полей
    if (!landId || !owner || !address || !area) {
        message.textContent = "Заполните все обязательные поля.";
        message.className = "error";
        return;
    }

    // Проверяем корректность площади
    if (!Number.isFinite(Number(area)) || Number(area) <= 0) {
        message.textContent = "Укажите корректную площадь участка.";
        message.className = "error";
        return;
    }

    // Формируем данные для отправки на сервер
    const landData = {
        land_id: landId,
        owner: owner,
        address: address,
        area_sqm: Number(area)
    };

    try {
        const response = await fetch(`${API_URL}/submit_application`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(landData)
        });

        const result = await response.json();

        if (!response.ok || result.status !== "success") {
            throw new Error(result.message || result.error || "Не удалось зарегистрировать участок.");
        }

        message.textContent = "Участок успешно зарегистрирован!";
        message.className = "success";

        // Добавляем новый участок в общий массив
        const newLand = {
            id: landId,
            name: `Участок № ${landId}`,
            address: address,
            area: `${Number(area).toLocaleString("ru-RU")} м²`,
            currentOwner: owner,
            since: "Право зарегистрировано только что",
            history: [
                {
                    owner: owner,
                    period: "С момента регистрации",
                    event: "Текущий владелец"
                }
            ]
        };

        lands.push(newLand);

        // Обновляем список участков
        renderResults(lands);

        // Показываем список участков
        detailsSection.hidden = true;
        resultsSection.hidden = false;

        // Очищаем поисковую строку
        searchInput.value = "";

        // Очищаем форму
        registrationForm.reset();

        // Прокручиваем страницу к списку
        resultsSection.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });

        console.log("Результат регистрации:", result);

    } catch (error) {
        message.textContent = error.message || "Ошибка при отправке заявки.";
        message.className = "error";

        console.error("Ошибка регистрации:", error);
    }
});


const lands = [
    {
        id: "104",
        name: "Сосновый берег",
        address: "г. Казань, условный адрес",
        area: "1 200 м²",
        currentOwner: "Иванов Иван Иванович",
        since: "Право зарегистрировано в 2025 году",
        history: [
            {
                owner: "Иванов Иван Иванович",
                period: "2025 — настоящее время",
                event: "Текущий владелец"
            },
            {
                owner: "Петров Пётр Петрович",
                period: "2021–2025",
                event: "Переход права собственности"
            },
            {
                owner: "Сидорова Анна Сергеевна",
                period: "2017–2021",
                event: "Предыдущий владелец"
            }
        ]
    },
    {
        id: "208",
        name: "Зелёный склон",
        address: "г. Казань, условный адрес",
        area: "860 м²",
        currentOwner: "Смирнова Елена Андреевна",
        since: "Право зарегистрировано в 2024 году",
        history: [
            {
                owner: "Смирнова Елена Андреевна",
                period: "2024 — настоящее время",
                event: "Текущий владелец"
            },
            {
                owner: "Кузнецов Алексей Олегович",
                period: "2019–2024",
                event: "Переход права собственности"
            }
        ]
    },
    {
        id: "315",
        name: "Луговой",
        address: "г. Казань, условный адрес",
        area: "1 540 м²",
        currentOwner: "Васильев Дмитрий Сергеевич",
        since: "Право зарегистрировано в 2023 году",
        history: [
            {
                owner: "Васильев Дмитрий Сергеевич",
                period: "2023 — настоящее время",
                event: "Текущий владелец"
            },
            {
                owner: "Морозова Ольга Викторовна",
                period: "2018–2023",
                event: "Переход права собственности"
            }
        ]
    }
];


async function loadLandsFromBlockchain() {
    try {
        const response = await fetch(`${API_URL}/blocks`);

        if (!response.ok) {
            throw new Error("Не удалось загрузить участки из блокчейна.");
        }

        const blocks = await response.json();

        const blockchainLands = [];

        blocks.forEach(block => {
            block.transactions.forEach(transaction => {

                if (transaction.type === "REGISTER_LAND") {
                    const newLand = {
                        id: transaction.land_id,
                        name: `Участок № ${transaction.land_id}`,
                        address: transaction.address,
                        area: `${Number(transaction.area_sqm).toLocaleString("ru-RU")} м²`,
                        currentOwner: transaction.owner,
                        since: "Право зарегистрировано",
                        history: [
                            {
                                owner: transaction.owner,
                                period: "С момента регистрации",
                                event: "Текущий владелец"
                            }
                        ]
                    };

                    blockchainLands.push(newLand);
                }

            });
        });

        // Объединяем демонстрационные и реальные участки.
        // Если ID совпадает, оставляем данные из блокчейна.
        const landsMap = new Map();

        lands.forEach(land => {
            landsMap.set(String(land.id), land);
        });

        blockchainLands.forEach(land => {
            landsMap.set(String(land.id), land);
        });

        lands.length = 0;
        lands.push(...landsMap.values());

        renderResults(lands);

    } catch (error) {
        console.error("Ошибка загрузки участков:", error);
    }
}


const searchForm = document.querySelector("#search-form");
const searchInput = document.querySelector("#search-input");
const resultsSection = document.querySelector("#results-section");
const detailsSection = document.querySelector("#details-section");
const resultsContainer = document.querySelector("#results");
const emptyState = document.querySelector("#empty-state");

function renderResults(list) {
    resultsContainer.innerHTML = "";

    document.querySelector("#results-count").textContent =
        `Найдено: ${list.length}`;

    emptyState.hidden = list.length !== 0;

    list.forEach(land => {
        const card = document.createElement("button");
        card.type = "button";
        card.className = "land-card";

        const number = document.createElement("span");
        number.className = "land-number";
        number.textContent = `Участок № ${land.id}`;

        const title = document.createElement("h3");
        title.textContent = land.name;

        const address = document.createElement("p");
        address.className = "land-address";
        address.textContent = land.address;

        const divider = document.createElement("div");
        divider.className = "card-divider";

        const ownerLabel = document.createElement("div");
        ownerLabel.className = "owner-label";
        ownerLabel.textContent = "Текущий владелец";

        const ownerName = document.createElement("div");
        ownerName.className = "owner-name";
        ownerName.textContent = land.currentOwner;

        card.append(number, title, address, divider, ownerLabel, ownerName);

        card.addEventListener("click", () => {
            showDetails(land);
        });

        resultsContainer.appendChild(card);
    });
}

function searchLands(query) {
    const value = query.trim().toLocaleLowerCase("ru");

    if (!value) {
        return lands;
    }

    return lands.filter(land => {
        return (
            land.id.toLocaleLowerCase("ru").includes(value) ||
            land.name.toLocaleLowerCase("ru").includes(value) ||
            land.address.toLocaleLowerCase("ru").includes(value) ||
            land.currentOwner.toLocaleLowerCase("ru").includes(value)
        );
    });
}

function showDetails(land) {
    resultsSection.hidden = true;
    detailsSection.hidden = false;

    document.querySelector("#details-title").textContent = land.name;
    document.querySelector("#details-address").textContent =
        `Участок № ${land.id} · ${land.address}`;

    document.querySelector("#current-owner").textContent =
        land.currentOwner;

    document.querySelector("#owner-since").textContent = land.since;
    document.querySelector("#land-number").textContent = land.id;
    document.querySelector("#land-area").textContent = land.area;

    const historyContainer =
        document.querySelector("#ownership-history");

    historyContainer.innerHTML = "";

    land.history.forEach(item => {
        const entry = document.createElement("div");
        entry.className = "timeline-item";

        const date = document.createElement("p");
        date.className = "timeline-date";
        date.textContent = item.period;

        const owner = document.createElement("p");
        owner.className = "timeline-owner";
        owner.textContent = item.owner;

        const event = document.createElement("p");
        event.className = "timeline-event";
        event.textContent = item.event;

        entry.append(date, owner, event);
        historyContainer.appendChild(entry);
    });

    detailsSection.scrollIntoView({
        behavior: "smooth",
        block: "start"
    });
}

searchForm.addEventListener("submit", event => {
    event.preventDefault();

    const query = searchInput.value;
    const foundLands = searchLands(query);

    detailsSection.hidden = true;
    resultsSection.hidden = false;

    document.querySelector("#results-title").textContent =
        query.trim() ? "Результаты поиска" : "Земельные участки";

    renderResults(foundLands);
});

document.querySelector("#back-button").addEventListener("click", () => {
    detailsSection.hidden = true;
    resultsSection.hidden = false;

    resultsSection.scrollIntoView({
        behavior: "smooth",
        block: "start"
    });
});

renderResults(lands);
loadLandsFromBlockchain();
checkConnection();


// ======================================
// ДЕМОНСТРАЦИОННАЯ АВТОРИЗАЦИЯ
// ======================================

const authSection = document.querySelector("#demo-auth-section");
const registerSection = document.querySelector("#demo-register-section");
const landSection = document.querySelector(".registration-section");

const authModal = document.querySelector("#auth-modal");
const openLoginButton = document.querySelector("#open-login");
const closeAuthButton = document.querySelector("#close-auth-modal");
const openRegistrationButton = document.querySelector("#open-registration");


const loginForm = document.querySelector("#demo-login-form");
const registerForm = document.querySelector("#demo-register-form");

const loginMessage = document.querySelector("#demo-auth-message");
const registerMessage = document.querySelector("#demo-register-message");

// Данные демонстрационных пользователей
let demoUsers = JSON.parse(sessionStorage.getItem("demo-users")) || [];

// Тестовый аккаунт для показа проекта
if (!demoUsers.some(user => user.email === "demo@test.ru")) {
    demoUsers.push({
        name: "Демонстрационный пользователь",
        email: "demo@test.ru",
        password: "1234"
    });

    sessionStorage.setItem("demo-users", JSON.stringify(demoUsers));
}

// Показываем нужный экран

function showAuthScreen(screen) {
    authSection.hidden = screen !== "login";
    registerSection.hidden = screen !== "register";

    // Форма регистрации участка доступна только после входа
    landSection.hidden = screen !== "account";
}


// Открываем окно авторизации
openLoginButton.addEventListener("click", function() {
    showAuthScreen("login");
    authModal.hidden = false;
});

// Закрываем окно по кнопке
closeAuthButton.addEventListener("click", function() {
    authModal.hidden = true;
});

// Закрываем окно при нажатии на затемнённую область
authModal.addEventListener("click", function(event) {
    if (event.target === authModal) {
        authModal.hidden = true;
    }
});

// Переход к регистрации земельного участка
openRegistrationButton.addEventListener("click", function() {
    const user = JSON.parse(sessionStorage.getItem("demo-user"));

    if (!user) {
        showAuthScreen("login");
        authModal.hidden = false;
        loginMessage.textContent = "Для регистрации участка сначала войдите в аккаунт.";
        return;
    }

    landSection.scrollIntoView({
        behavior: "smooth",
        block: "start"
    });
});


// Проверяем, есть ли активная сессия
function checkDemoSession() {
    const user = JSON.parse(sessionStorage.getItem("demo-user"));

    if (user) {
        showAuthScreen("account");
    } else {
        showAuthScreen("login");
    }
}


// Переход от входа к созданию аккаунта
document.querySelector("#demo-show-register").addEventListener("click", function() {
    registerMessage.textContent = "";
    registerForm.reset();
    showAuthScreen("register");
});

// Возвращение от создания аккаунта ко входу
document.querySelector("#demo-show-login").addEventListener("click", function() {
    loginMessage.textContent = "";
    loginForm.reset();
    showAuthScreen("login");
});


// Регистрация нового демонстрационного пользователя
registerForm.addEventListener("submit", function(event) {
    event.preventDefault();

    const name = document.querySelector("#demo-register-name").value.trim();
    const email = document.querySelector("#demo-register-email").value.trim().toLowerCase();
    const password = document.querySelector("#demo-register-password").value;
    const confirmPassword = document.querySelector("#demo-register-confirm").value;

    if (password !== confirmPassword) {
        registerMessage.textContent = "Пароли не совпадают";
        return;
    }

    if (demoUsers.some(user => user.email === email)) {
        registerMessage.textContent = "Пользователь с таким email уже существует";
        return;
    }

    const newUser = {
        name: name,
        email: email,
        password: password
    };

    demoUsers.push(newUser);

    sessionStorage.setItem("demo-users", JSON.stringify(demoUsers));
    sessionStorage.setItem("demo-user", JSON.stringify({
        name: newUser.name,
        email: newUser.email
    }));

    registerForm.reset();

    checkDemoSession();
    authModal.hidden = true;
});

// Вход в аккаунт
loginForm.addEventListener("submit", function(event) {
    event.preventDefault();

    const email = document.querySelector("#demo-email").value.trim().toLowerCase();
    const password = document.querySelector("#demo-password").value;

    const user = demoUsers.find(function(item) {
        return item.email === email && item.password === password;
    });

    if (!user) {
        loginMessage.textContent = "Неверная почта или пароль";
        return;
    }

    sessionStorage.setItem("demo-user", JSON.stringify({
        name: user.name,
        email: user.email
    }));

    loginForm.reset();

    checkDemoSession();
    authModal.hidden = true;
});

// Выход из аккаунта
document.querySelector("#demo-logout").addEventListener("click", function() {
    sessionStorage.removeItem("demo-user");
    checkDemoSession();

    loginMessage.textContent = "";
    loginForm.reset();

    window.scrollTo({
        top: 0,
        behavior: "smooth"
    });
});

// При открытии страницы проверяем авторизацию
authModal.hidden = true;
checkDemoSession();

