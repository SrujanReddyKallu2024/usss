const chatArea = document.getElementById("chatArea");
const input = document.getElementById("messageInput");
const sendBtn = document.getElementById("sendBtn");

let sessionId = localStorage.getItem("session_id") || "";

input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

function sendChip(el) {
    input.value = el.textContent;
    sendMessage();
}

async function sendMessage() {
    const text = input.value.trim();
    if (!text) return;

    const welcome = document.getElementById("welcome");
    if (welcome) welcome.remove();

    addMessage("user", text);
    input.value = "";
    sendBtn.disabled = true;

    const typingEl = showTyping();

    try {
        const res = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: text, session_id: sessionId }),
        });

        const data = await res.json();
        sessionId = data.session_id;
        localStorage.setItem("session_id", sessionId);

        typingEl.remove();
        addBotMessage(data);
    } catch (err) {
        typingEl.remove();
        addBotMessage({
            answer: "Could not reach the server. Is it running?",
            route: "error",
        });
    }

    sendBtn.disabled = false;
    input.focus();
}

function addMessage(role, text) {
    const div = document.createElement("div");
    div.className = `message ${role}`;

    const avatar = role === "user" ? "👤" : "🤖";

    div.innerHTML = `
        <div class="avatar">${avatar}</div>
        <div class="bubble"><p>${escapeHtml(text)}</p></div>
    `;

    chatArea.appendChild(div);
    scrollDown();
}

function addBotMessage(data) {
    const div = document.createElement("div");
    div.className = "message bot";

    let badge = `<span class="badge ${data.route}">${data.route}</span>`;
    if (data.time_ms) {
        badge += `<span class="badge time">${data.time_ms}ms</span>`;
    }
    let content = formatAnswer(data.answer);
    let extra = "";

    if (data.sql) {
        extra += `<div class="sql-block">${escapeHtml(data.sql)}</div>`;
    }

    if (data.sources && data.sources.length > 0) {
        extra += `<div class="sources">📄 Sources: <span>${data.sources.join(", ")}</span></div>`;
    }

    div.innerHTML = `
        <div class="avatar">🤖</div>
        <div class="bubble">
            ${badge}
            ${content}
            ${extra}
        </div>
    `;

    chatArea.appendChild(div);
    scrollDown();
}

function showTyping() {
    const div = document.createElement("div");
    div.className = "message bot";
    div.id = "typing";
    div.innerHTML = `
        <div class="avatar">🤖</div>
        <div class="bubble">
            <div class="typing">
                <span></span><span></span><span></span>
            </div>
        </div>
    `;
    chatArea.appendChild(div);
    scrollDown();
    return div;
}

function formatAnswer(text) {
    if (!text) return "<p>No response.</p>";

    let html = text
        .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
        .replace(/\n- /g, "\n• ")
        .replace(/\n\n/g, "</p><p>")
        .replace(/\n/g, "<br>");

    return `<p>${html}</p>`;
}

function escapeHtml(text) {
    const el = document.createElement("span");
    el.textContent = text;
    return el.innerHTML;
}

function scrollDown() {
    chatArea.scrollTop = chatArea.scrollHeight;
}
