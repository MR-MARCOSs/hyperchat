const ws = new WebSocket("ws://127.0.0.1:8000/ws/" + prompt("Digite seu nome de usuário:"));
const input = document.getElementById('messageInput');

input.addEventListener('input', () => {
    ws.send("/typing");
});

ws.onmessage = function (event) {
    const messages = document.getElementById("messages");
    const message = document.createElement("li");
    message.textContent = event.data;
    messages.appendChild(message);
};

function sendMessage() {
    const input = document.getElementById("messageInput");
    ws.send(input.value);
    input.value = "";
}

