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
checkConnection();


// ======================================
// ДЕМОНСТРАЦИОННАЯ АВТОРИЗАЦИЯ
// ======================================

const authSection = document.querySelector("#demo-auth-section");
const registerSection = document.querySelector("#demo-register-section");
const landSection = document.querySelector(".registration-section");

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
    landSection.hidden = screen !== "account";
}

// Проверяем, есть ли активная сессия
function checkDemoSession() {
    const user = JSON.parse(sessionStorage.getItem("demo-user"));

    if (user) {
        showAuthScreen("account");
    } else {
        showAuthScreen("login");
    }
}

// Переключение между входом и регистрацией
document.querySelector("#demo-show-register").addEventListener("click", function() {
    registerMessage.textContent = "";
    showAuthScreen("register");
});

document.querySelector("#demo-show-login").addEventListener("click", function() {
    loginMessage.textContent = "";
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
});

// Выход из аккаунта
document.querySelector("#demo-logout").addEventListener("click", function() {
    sessionStorage.removeItem("demo-user");
    checkDemoSession();
});

// При открытии страницы проверяем авторизацию
checkDemoSession();

