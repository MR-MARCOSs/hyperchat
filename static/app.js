// Variáveis globais
let currentUser = null;
let currentChat = "general"; // 'general' ou username do contato privado
let websocket = null;
let typingTimeout = null;

// Inicialização quando o DOM estiver carregado
document.addEventListener("DOMContentLoaded", async () => {
  // Verificar autenticação
  await checkAuth();

  // Configurar WebSocket
  setupWebSocket();

  // Configurar eventos
  setupEventListeners();

  // Carregar contatos
  await loadContacts();
});

// Verificar autenticação
async function checkAuth() {
  try {
    const response = await fetch("/users/me", {
      credentials: "include",
    });

    if (response.ok) {
      const userData = await response.json();
      currentUser = userData.username;
      document.getElementById("username").textContent = currentUser;
      document.getElementById("userAvatar").textContent = currentUser
        .charAt(0)
        .toUpperCase();
    } else {
      window.location.href = "/login-page";
    }
  } catch (error) {
    console.error("Erro ao verificar autenticação:", error);
    window.location.href = "/login-page";
  }
}

// Configurar WebSocket
function setupWebSocket() {
  if (!currentUser) return;

  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const host = window.location.host;
  websocket = new WebSocket(`${protocol}//${host}/ws/${currentUser}`);

  websocket.onopen = () => {
    document.getElementById("connectionStatus").textContent = "Conectado";
    document.getElementById("connectionStatus").className = "status connected";
  };

  websocket.onclose = () => {
    document.getElementById("connectionStatus").textContent = "Desconectado";
    document.getElementById("connectionStatus").className =
      "status disconnected";
  };

  websocket.onerror = (error) => {
    console.error("Erro no WebSocket:", error);
  };

  websocket.onmessage = (event) => {
    const data = event.data;

    // Verificar se é uma mensagem privada
    if (data.startsWith("PRIVATE:")) {
      const parts = data.split(":");
      const sender = parts[1];
      const message = parts.slice(2).join(":");

      addMessageToChat(sender, message, "private");

      // Atualizar contato para mostrar notificação
      updateContactNotification(sender, true);
    }
    // Verificar se é notificação de digitação
    else if (data.startsWith("TYPING:")) {
      const typingUser = data.split(":")[1];
      showTypingIndicator(typingUser);
    }
    // Mensagem geral
    else {
      addMessageToChat("general", data, "general");
    }
  };
}

// Configurar listeners de eventos
function setupEventListeners() {
  // Logout
  document.getElementById("logoutBtn").addEventListener("click", logout);

  // Envio de mensagem
  document.getElementById("messageInput").addEventListener("keypress", (e) => {
    if (e.key === "Enter") {
      sendMessage();
    }
  });

  // Digitação (para mostrar "está digitando")
  document.getElementById("messageInput").addEventListener("input", () => {
    if (websocket && websocket.readyState === WebSocket.OPEN) {
      websocket.send("/typing");
    }
  });

  // Pesquisa de usuários
  document
    .getElementById("userSearch")
    .addEventListener("input", debounce(searchUsers, 300));
}

// Pesquisar usuários
async function searchUsers() {
  const searchTerm = document.getElementById("userSearch").value.trim();
  if (searchTerm.length < 2) {
    document.getElementById("searchResults").innerHTML = "";
    return;
  }

  try {
    const response = await fetch(
      `/users/search?q=${encodeURIComponent(searchTerm)}`
    );
    if (response.ok) {
      const users = await response.json();
      displaySearchResults(users);
    }
  } catch (error) {
    console.error("Erro ao pesquisar usuários:", error);
  }
}

// Exibir resultados da pesquisa
function displaySearchResults(users) {
  const resultsContainer = document.getElementById("searchResults");
  resultsContainer.innerHTML = "";

  users.forEach((user) => {
    if (user.username === currentUser) return; // Não mostrar o próprio usuário

    const userElement = document.createElement("div");
    userElement.className = "search-result-item";
    userElement.innerHTML = `
      <div class="user-avatar">${user.username.charAt(0).toUpperCase()}</div>
      <div class="user-info">
        <div class="user-name">${user.username}</div>
      </div>
    `;

    userElement.addEventListener("click", () => {
      startPrivateChat(user.username);
      resultsContainer.innerHTML = "";
      document.getElementById("userSearch").value = "";
    });

    resultsContainer.appendChild(userElement);
  });
}

// Iniciar chat privado
function startPrivateChat(username) {
  // Verificar se já existe um contato
  const existingContact = document.querySelector(
    `.contact[data-chat="${username}"]`
  );

  if (!existingContact) {
    // Adicionar novo contato
    addContact(username);
  }

  // Selecionar o chat
  selectChat(username);
}

// Adicionar contato
function addContact(username) {
  const contactsContainer = document.querySelector(".contacts");

  const contactElement = document.createElement("div");
  contactElement.className = "contact";
  contactElement.dataset.chat = username;
  contactElement.innerHTML = `
    <div class="contact-avatar">${username.charAt(0).toUpperCase()}</div>
    <div class="contact-info">
      <div class="contact-name">${username}</div>
    </div>
    <div class="contact-notification hidden"></div>
  `;

  contactElement.addEventListener("click", () => selectChat(username));
  contactsContainer.appendChild(contactElement);
}

// Selecionar chat
function selectChat(chatId) {
  // Desmarcar todos os contatos
  document.querySelectorAll(".contact").forEach((contact) => {
    contact.classList.remove("selected");
  });

  // Marcar contato selecionado
  const contact = document.querySelector(`.contact[data-chat="${chatId}"]`);
  if (contact) {
    contact.classList.add("selected");
    contact.querySelector(".contact-notification").classList.add("hidden");
  }

  // Atualizar chat atual
  currentChat = chatId;

  // Limpar mensagens e carregar as do chat selecionado
  document.getElementById("messages").innerHTML = "";

  // Carregar mensagens do chat
  loadChatMessages(chatId);
}

// Carregar mensagens do chat
async function loadChatMessages(chatId) {
  try {
    let endpoint = "/messages";
    if (chatId !== "general") {
      endpoint = `/messages/private?with=${chatId}`;
    }

    const response = await fetch(endpoint);
    if (response.ok) {
      const messages = await response.json();
      messages.forEach((msg) => {
        const sender =
          chatId === "general"
            ? msg.username
            : msg.sender === currentUser
            ? "Você"
            : msg.sender;
        const type = chatId === "general" ? "general" : "private";
        addMessageToChat(sender, msg.content, type);
      });
    }
  } catch (error) {
    console.error("Erro ao carregar mensagens:", error);
  }
}

// Adicionar mensagem ao chat
function addMessageToChat(sender, message, type) {
  const messagesContainer = document.getElementById("messages");

  // Verificar se a mensagem pertence ao chat atual
  const isCurrentChat =
    (type === "general" && currentChat === "general") ||
    (type === "private" &&
      (currentChat === sender ||
        (sender === "Você" && currentChat !== "general")));

  if (isCurrentChat) {
    const messageElement = document.createElement("div");
    messageElement.className = `message ${
      sender === currentUser || sender === "Você" ? "sent" : "received"
    }`;
    messageElement.innerHTML = `
      <div class="message-sender">${sender}</div>
      <div class="message-content">${message}</div>
      <div class="message-time">${new Date().toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      })}</div>
    `;
    messagesContainer.appendChild(messageElement);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }
}

// Enviar mensagem
function sendMessage() {
  const input = document.getElementById("messageInput");
  const message = input.value.trim();

  if (message && websocket && websocket.readyState === WebSocket.OPEN) {
    if (currentChat === "general") {
      // Mensagem geral
      websocket.send(message);
    } else {
      // Mensagem privada
      websocket.send(`@${currentChat} ${message}`);
    }

    input.value = "";

    // Adicionar mensagem localmente (feedback imediato)
    addMessageToChat(
      "Você",
      message,
      currentChat === "general" ? "general" : "private"
    );
  }
}

// Mostrar indicador de digitação
function showTypingIndicator(username) {
  if (
    username === currentUser ||
    (currentChat !== "general" && currentChat !== username)
  )
    return;

  const messagesContainer = document.getElementById("messages");
  let typingElement = document.getElementById("typing-indicator");

  if (!typingElement) {
    typingElement = document.createElement("div");
    typingElement.id = "typing-indicator";
    typingElement.className = "typing-indicator";
    messagesContainer.appendChild(typingElement);
  }

  typingElement.textContent = `${username} está digitando...`;
  messagesContainer.scrollTop = messagesContainer.scrollHeight;

  // Limpar após 3 segundos
  clearTimeout(typingTimeout);
  typingTimeout = setTimeout(() => {
    if (typingElement) typingElement.remove();
  }, 3000);
}

// Atualizar notificação de contato
function updateContactNotification(username, hasNewMessage) {
  const contact = document.querySelector(`.contact[data-chat="${username}"]`);
  if (contact) {
    const notification = contact.querySelector(".contact-notification");
    if (hasNewMessage && currentChat !== username) {
      notification.classList.remove("hidden");
    } else {
      notification.classList.add("hidden");
    }
  }
}

// Logout
async function logout() {
  try {
    await fetch("/logout", {
      method: "POST",
      credentials: "include",
    });
    window.location.href = "/login-page";
  } catch (error) {
    console.error("Erro ao fazer logout:", error);
  }
}

// Carregar contatos
async function loadContacts() {
  try {
    const response = await fetch("/users/contacts");
    if (response.ok) {
      const contacts = await response.json();
      contacts.forEach((contact) => {
        addContact(contact.username);
      });
    }
  } catch (error) {
    console.error("Erro ao carregar contatos:", error);
  }
}

// Debounce para pesquisa
function debounce(func, wait) {
  let timeout;
  return function () {
    const context = this,
      args = arguments;
    clearTimeout(timeout);
    timeout = setTimeout(() => {
      func.apply(context, args);
    }, wait);
  };
}
