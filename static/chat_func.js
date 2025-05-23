// Obter nome de usuário e atualizar a interface
const username = prompt("Digite seu nome de usuário:") || "Usuário";
document.getElementById("username").textContent = username;
document.getElementById("userAvatar").textContent = username
  .charAt(0)
  .toUpperCase();

// Configurar WebSocket
const ws = new WebSocket("ws://127.0.0.1:8000/ws/" + username);
const input = document.getElementById("messageInput");
const messagesContainer = document.getElementById("messages");
const statusElement = document.getElementById("connectionStatus");

// Eventos do WebSocket
ws.onopen = function () {
  statusElement.textContent = "Online";
  statusElement.style.color = "var(--success)";
};

ws.onclose = function () {
  statusElement.textContent = "Offline - Tentando reconectar...";
  statusElement.style.color = "var(--danger)";
};

ws.onerror = function (error) {
  statusElement.textContent = "Erro na conexão";
  statusElement.style.color = "var(--danger)";
  console.error("WebSocket error:", error);
};

// Variáveis para controle de digitação
let typingTimeout;
let lastTypingTime = 0;

// Evento de digitação
input.addEventListener("input", () => {
  const now = Date.now();
  // Enviar notificação apenas se passou mais de 1 segundo desde a última
  if (now - lastTypingTime > 1000) {
    ws.send("/typing");
    lastTypingTime = now;
  }

  // Limpar timeout anterior
  if (typingTimeout) clearTimeout(typingTimeout);

  // Configurar novo timeout para parar de mostrar "digitando"
  typingTimeout = setTimeout(() => {
    // O servidor irá lidar com o timeout automaticamente
  }, 2000);
});

// Evento de recebimento de mensagem
ws.onmessage = function (event) {
  const data = event.data;

  // Verificar se é um indicador de digitação
  if (data.startsWith("/typing:")) {
    const typingUsers = data.split(":")[1];
    showTypingIndicator(typingUsers);
    return;
  }

  // Verificar se é para parar o indicador de digitação
  if (data === "/stop-typing") {
    hideTypingIndicator();
    return;
  }

  // Criar elemento de mensagem
  const message = document.createElement("div");
  message.classList.add("message");

  // Verificar se é uma mensagem do usuário atual
  if (data.startsWith(username + ":")) {
    message.classList.add("sent");
    message.textContent = data.split(":")[1];
  } else {
    message.classList.add("received");
    message.textContent = data;
  }

  // Adicionar informações da mensagem
  const messageInfo = document.createElement("div");
  messageInfo.classList.add("message-info");

  const time = new Date().toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
  const sender = data.split(":")[0];

  messageInfo.innerHTML = `
            <span>${sender}</span>
            <span>${time}</span>
        `;

  message.appendChild(messageInfo);
  messagesContainer.appendChild(message);

  // Rolagem automática para a última mensagem
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
};

// Função para enviar mensagem
function sendMessage() {
  const input = document.getElementById("messageInput");
  const message = input.value.trim();

  if (message) {
    ws.send(message);
    input.value = "";

    // Limpar indicador de digitação ao enviar mensagem
    if (typingTimeout) {
      clearTimeout(typingTimeout);
      typingTimeout = null;
    }
  }
}

// Função para enviar arquivo
async function uploadFile() {
  const input = document.getElementById("fileInput");
  const file = input.files[0];

  if (!file) return;

  const formData = new FormData();
  formData.append("file", file);

  try {
    const response = await fetch("http://127.0.0.1:8000/upload/", {
      method: "POST",
      body: formData,
    });

    const result = await response.json();

    // Adicionar mensagem com o arquivo enviado
    const message = document.createElement("div");
    message.classList.add("message", "sent");
    message.innerHTML = `
                <div>Arquivo enviado: ${file.name}</div>
                <div class="message-info">
                    <span>${username}</span>
                    <span>${new Date().toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}</span>
                </div>
            `;

    messagesContainer.appendChild(message);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  } catch (error) {
    console.error("Erro ao enviar arquivo:", error);
    alert("Erro ao enviar arquivo");
  } finally {
    // Limpar o input de arquivo
    input.value = "";
  }
}

// Funções para indicador de digitação
function showTypingIndicator(users) {
  let indicator = document.getElementById("typing-indicator");

  if (!indicator) {
    indicator = document.createElement("div");
    indicator.id = "typing-indicator";
    indicator.classList.add("typing-indicator");
    messagesContainer.appendChild(indicator);
  }

  const usersList = users.split(",");
  if (usersList.length > 1) {
    indicator.textContent = `${usersList.join(", ")} estão digitando...`;
  } else {
    indicator.textContent = `${users} está digitando...`;
  }

  // Rolagem automática para mostrar o indicador
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function hideTypingIndicator() {
  const indicator = document.getElementById("typing-indicator");
  if (indicator) {
    indicator.remove();
  }
}

// Permitir enviar mensagem com Enter
input.addEventListener("keypress", function (e) {
  if (e.key === "Enter") {
    sendMessage();
  }
});

// Configurar evento para upload de arquivo
document.getElementById("fileInput").addEventListener("change", uploadFile);

// Focar no input de mensagem ao carregar a página
window.addEventListener("load", () => {
  input.focus();
});
