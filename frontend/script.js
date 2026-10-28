
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
