// static/script.js
document.addEventListener("DOMContentLoaded", () => {
  const chatBox = document.getElementById("chat-box");
  const messageInput = document.getElementById("messageInput");
  const sendMessageBtn = document.getElementById("sendMessageBtn");
  const currentUsernameSpan = document.getElementById("current-username");
  const chatTargetNameHeader = document.getElementById("chat-target-name");
  const logoutBtn = document.getElementById("logout-btn");
  const userSearchInput = document.getElementById("user-search-input");
  const userSearchResultsList = document.getElementById("user-search-results");
  const recentChatsList = document.getElementById("recent-chats-list");
  const typingIndicator = document.getElementById("typing-indicator");
  const fileInput = document.getElementById("fileInput");
  // const uploadBtn = document.getElementById('uploadBtn'); // Removido do HTML e JS

  let currentUser = null;
  let websocket = null;
  let currentChatTarget = "general"; // 'general' ou 'username'
  let typingTimer = null; // Timer para notificação de digitação
  const TYPING_TIMEOUT = 2000; // 2 segundos sem digitar para parar a notificação

  // --- Funções Auxiliares ---

  // Função para formatar a data/hora
  function formatTimestamp(isoString) {
    if (!isoString) return "";
    try {
      const date = new Date(isoString);
      if (isNaN(date)) {
        console.warn("Invalid date string:", isoString);
        return isoString; // Retorna a string original se for inválida
      }
      // Retorna apenas HH:MM
      return date.toLocaleTimeString("pt-BR", {
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch (e) {
      console.error("Error formatting timestamp:", e, isoString);
      return isoString;
    }
  }

  // Função para exibir uma mensagem de texto no chat
  // targetChat: indica a qual chat (geral ou username) esta mensagem pertence
  function displayTextMessage(
    sender,
    content,
    timestamp,
    isCurrentUserSender,
    targetChat
  ) {
    // Só exibe se a mensagem for para o chat ativo no momento
    // O targetChat passado aqui deve ser 'general' OU o username do outro usuário no chat privado
    // currentChatTarget é 'general' OU o username do outro usuário no chat privado
    if (targetChat !== currentChatTarget) {
      // console.log(`Mensagem para ${targetChat} ignorada no chat ${currentChatTarget}`);
      // Adicionar notificação visual para chat privado não ativo (se a mensagem for para mim e de outro usuário)
      if (
        targetChat !== "general" &&
        targetChat === currentUser &&
        sender !== currentUser
      ) {
        const contactItem = recentChatsList.querySelector(
          `li[data-chat-target="${sender}"]`
        );
        if (contactItem && !contactItem.classList.contains("active")) {
          if (!contactItem.querySelector(".new-message-indicator")) {
            const indicator = document.createElement("span");
            indicator.classList.add("new-message-indicator");
            indicator.textContent = "•"; // Ou um contador simples
            contactItem.appendChild(indicator);
          }
        }
      }
      return; // Não exibe na caixa de chat atual
    }

    const messageElement = document.createElement("div");
    messageElement.classList.add("message");
    messageElement.classList.add(isCurrentUserSender ? "sent" : "received");

    // Cria elementos internos
    const senderSpan = document.createElement("span");
    senderSpan.classList.add("message-sender");
    senderSpan.textContent = isCurrentUserSender ? "Você" : sender;

    const contentSpan = document.createElement("span");
    contentSpan.classList.add("message-content");
    contentSpan.textContent = content;

    const timestampSpan = document.createElement("span");
    timestampSpan.classList.add("message-timestamp");
    timestampSpan.textContent = formatTimestamp(timestamp);

    // Adiciona elementos à mensagem
    messageElement.appendChild(senderSpan);
    messageElement.appendChild(contentSpan);
    messageElement.appendChild(timestampSpan);

    chatBox.appendChild(messageElement);
    // Rola para a última mensagem
    chatBox.scrollTop = chatBox.scrollHeight;
  }

  // Função para exibir mensagens de arquivo (simplificado: apenas link)
  // targetChat: indica a qual chat (geral ou username) esta mensagem pertence
  function displayFileMessage(
    sender,
    filename,
    filePath,
    timestamp,
    isCurrentUserSender,
    targetChat
  ) {
    // Similarmente, só exibe se a mensagem for para o chat ativo
    if (targetChat !== currentChatTarget) {
      // Opcional: Adicionar notificação visual para chat privado não ativo (similar ao texto)
      return; // Não exibe na caixa de chat atual
    }

    const messageElement = document.createElement("div");
    messageElement.classList.add("message");
    messageElement.classList.add(isCurrentUserSender ? "sent" : "received");

    const senderSpan = document.createElement("span");
    senderSpan.classList.add("message-sender");
    senderSpan.textContent = isCurrentUserSender ? "Você" : sender;

    const contentLink = document.createElement("a");
    contentLink.classList.add("message-content");
    // Garante que o caminho seja absoluto e seguro
    contentLink.href = encodeURI(filePath); // Use encodeURI para caminhos com espaços/chars especiais
    contentLink.target = "_blank"; // Abrir em nova aba
    contentLink.textContent = `📁 Arquivo: ${filename}`; // Texto do link com ícone simples

    const timestampSpan = document.createElement("span");
    timestampSpan.classList.add("message-timestamp");
    timestampSpan.textContent = formatTimestamp(timestamp);

    messageElement.appendChild(senderSpan);
    messageElement.appendChild(contentLink); // Adiciona o link
    messageElement.appendChild(timestampSpan);

    chatBox.appendChild(messageElement);
    chatBox.scrollTop = chatBox.scrollHeight;
  }

  // Limpar a caixa de chat
  function clearChatBox() {
    chatBox.innerHTML = "";
  }

  // Adicionar um usuário à lista de chats recentes
  function addRecentChat(username) {
    // Não adiciona o próprio usuário
    if (username === currentUser) return;

    // Verifica se já existe na lista de "Chats Recentes"
    if (recentChatsList.querySelector(`li[data-chat-target="${username}"]`)) {
      // Se já existe, move para o topo (opcional, para chats mais recentes ficarem em cima)
      // const existingItem = recentChatsList.querySelector(`li[data-chat-target="${username}"]`);
      // const generalChatLi = recentChatsList.querySelector('li[data-chat-target="general"]');
      // if (existingItem && generalChatLi && existingItem !== generalChatLi.nextSibling) {
      //     recentChatsList.insertBefore(existingItem, generalChatLi.nextSibling);
      // }
      return; // Já na lista, não duplica
    }

    const listItem = document.createElement("li");
    listItem.dataset.chatTarget = username;
    listItem.innerHTML = `<i class="fas fa-user"></i> ${username}`; // Use fas fa-user ou similar
    listItem.addEventListener("click", () => {
      switchChat(username);
      // Limpa o indicador de nova mensagem ao abrir o chat
      const indicator = listItem.querySelector(".new-message-indicator");
      if (indicator) {
        indicator.remove();
      }
    });

    // Adiciona no início da lista, abaixo do Chat Geral
    const generalChatLi = recentChatsList.querySelector(
      'li[data-chat-target="general"]'
    );
    if (generalChatLi) {
      recentChatsList.insertBefore(listItem, generalChatLi.nextSibling);
    } else {
      // Fallback: Se o Chat Geral não existe, adiciona no topo
      recentChatsList.insertBefore(listItem, recentChatsList.firstChild);
    }
  }

  // Função para carregar o chat geral
  async function loadGeneralChat() {
    clearChatBox();
    chatTargetNameHeader.textContent = "Chat Geral";
    currentChatTarget = "general";
    updateActiveChatItem();
    typingIndicator.textContent = ""; // Limpa indicador ao mudar de chat

    // Carregar histórico de mensagens gerais via REST
    try {
      const response = await fetch("/messages");
      if (response.ok) {
        const messages = await response.json();
        // Espera [{"username": "...", "content": "...", "timestamp": "..."}, ...]
        messages.forEach((msg) => {
          // console.log("Carregando mensagem geral:", msg);
          displayTextMessage(
            msg.username,
            msg.content,
            msg.timestamp,
            msg.username === currentUser,
            "general"
          );
        });
      } else if (response.status === 401) {
        console.warn(
          "Sessão expirada ao carregar chat geral, redirecionando..."
        );
        window.location.href = "/login-page"; // Redireciona se desautenticou
      } else {
        console.error(
          "Erro ao carregar histórico do chat geral:",
          response.statusText
        );
        displayTextMessage(
          "Sistema",
          `Não foi possível carregar o histórico do chat geral.`,
          null,
          false,
          "general"
        );
      }
    } catch (error) {
      console.error("Erro ao carregar histórico do chat geral:", error);
      displayTextMessage(
        "Sistema",
        `Erro na rede ao carregar histórico do chat geral.`,
        null,
        false,
        "general"
      );
    }

    // As novas mensagens gerais virão via WebSocket onmessage
  }

  // Função para carregar um chat privado com outro usuário
  async function loadPrivateChat(targetUsername) {
    clearChatBox();
    chatTargetNameHeader.textContent = `Chat com ${targetUsername}`;
    currentChatTarget = targetUsername;
    updateActiveChatItem();
    addRecentChat(targetUsername); // Garante que ele esteja na lista de recentes
    typingIndicator.textContent = ""; // Limpa indicador ao mudar de chat

    // Carregar histórico de mensagens privadas via REST
    try {
      const response = await fetch(
        `/messages/private?with_user=${encodeURIComponent(targetUsername)}`
      );
      if (response.ok) {
        const messages = await response.json();
        // Espera lista de dicionários como [{"sender": "...", "content": "...", "timestamp": "...", "message_type": "...", "filename": "...", "file_path": "..."}, ...]
        messages.forEach((msg) => {
          const isCurrentUserSender = msg.sender === currentUser;

          // Verifica o tipo de mensagem retornado pelo backend
          if (msg.message_type === "file" && msg.filename && msg.file_path) {
            displayFileMessage(
              msg.sender,
              msg.filename,
              msg.file_path,
              msg.timestamp,
              isCurrentUserSender,
              targetUsername
            );
          } else {
            // Assume que é mensagem de texto por padrão ou se o tipo for 'text'
            displayTextMessage(
              msg.sender,
              msg.content,
              msg.timestamp,
              isCurrentUserSender,
              targetUsername
            );
          }
        });
      } else if (response.status === 401) {
        console.warn(
          "Sessão expirada ao carregar chat privado, redirecionando..."
        );
        window.location.href = "/login-page"; // Redireciona se desautenticou
      } else if (response.status === 404) {
        console.warn(
          `Chat com usuário '${targetUsername}' não encontrado (talvez usuário excluído?).`
        );
        displayTextMessage(
          "Sistema",
          `Usuário '${targetUsername}' não encontrado.`,
          null,
          false,
          targetUsername
        );
      } else {
        console.error(
          "Erro ao carregar mensagens privadas:",
          response.statusText
        );
        displayTextMessage(
          "Sistema",
          `Não foi possível carregar o histórico de mensagens com ${targetUsername}.`,
          null,
          false,
          targetUsername
        );
      }
    } catch (error) {
      console.error("Erro ao carregar mensagens privadas:", error);
      displayTextMessage(
        "Sistema",
        `Erro na rede ao carregar histórico de mensagens com ${targetUsername}.`,
        null,
        false,
        targetUsername
      );
    }
  }

  // Alternar entre chat geral e privado
  function switchChat(target) {
    if (currentChatTarget === target) return; // Já no chat selecionado

    // Limpa o input de mensagem ao trocar de chat
    messageInput.value = "";
    // Cancela o timer de digitação do chat anterior, mas *não* envia "/stopped_typing" ou JSON falso.
    // O próximo input iniciará um novo timer se necessário.
    if (typingTimer) {
      clearTimeout(typingTimer);
      typingTimer = null;
      // No backend atual, o status de digitação geral só para quando uma mensagem é enviada.
      // Se implementarmos notificação de digitação privada no backend via JSON,
      // precisaremos enviar um sinal de parada explícito aqui ao trocar de chat privado.
    }
    typingIndicator.textContent = ""; // Limpa indicador visual

    if (target === "general") {
      loadGeneralChat();
    } else {
      loadPrivateChat(target);
    }
  }

  // Atualiza a classe 'active' na lista de chats/contatos
  function updateActiveChatItem() {
    recentChatsList.querySelectorAll("li").forEach((item) => {
      item.classList.remove("active");
      if (item.dataset.chatTarget === currentChatTarget) {
        item.classList.add("active");
        // Remove qualquer indicador de nova mensagem do item ativo
        const indicator = item.querySelector(".new-message-indicator");
        if (indicator) {
          indicator.remove();
        }
      }
    });
    // Também remove 'active' dos resultados da busca (para evitar confusão visual)
    userSearchResultsList.querySelectorAll("li").forEach((item) => {
      item.classList.remove("active");
    });
  }

  // --- Conexão WebSocket ---

  function connectWebSocket() {
    if (websocket && websocket.readyState === WebSocket.OPEN) {
      console.log("WebSocket já está aberto.");
      return;
    }
    if (!currentUser) {
      console.error("Não é possível conectar ao WS sem o nome de usuário.");
      // Tenta iniciar o processo de login se não tem usuário
      init(); // Chama init novamente, que redirecionará se não autenticado
      return;
    }

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws/${currentUser}`;
    websocket = new WebSocket(wsUrl);
    console.log(`Attempting WebSocket connection to ${wsUrl}`); // Log

    websocket.onopen = (event) => {
      console.log("WebSocket connection opened:", event);
      // As mensagens gerais iniciais agora são carregadas via REST em loadGeneralChat()
      // e as mensagens privadas em loadPrivateChat().
      // Novas mensagens virão via onmessage.
    };

    websocket.onmessage = (event) => {
      // console.log("WebSocket message received:", event.data);

      let message;
      try {
        // Tenta parsear como JSON
        message = JSON.parse(event.data);
        // console.log("Parsed JSON message:", message);
      } catch (e) {
        // Se não for JSON, trata como mensagem de texto simples
        // console.log("Received plain text message:", event.data);
        message = { type: "text_plain", content: event.data };
      }

      // Lógica para displayar mensagens baseada no tipo:

      // 1. Notificação de digitação (backend envia como texto simples)
      // O backend ConnectionManager.broadcast_typing_status agora envia texto simples como:
      // "UsuárioX está digitando..."
      // "UsuárioX e UsuárioY estão digitando..."
      // "UsuárioX, UsuárioY e UsuárioZ estão digitando..."
      // "Ninguém está digitando."
      const typingRegex = /^(.*?) est(á|ao) digitando\.\.\.$/;
      const nobodyTypingRegex = /^Ninguém est(á|ao) digitando\.$/;

      if (message.type === "text_plain") {
        // Mensagens do Manager como "User entrou/saiu do chat." também são texto simples
        const userInOutRegex = /^(.*?) (entrou|saiu) do chat\.$/;
        const userInOutMatch = message.content.match(userInOutRegex);

        if (userInOutMatch) {
          // Mensagem de entrada/saída do usuário (sempre para chat geral)
          displayTextMessage(
            "Sistema",
            message.content,
            new Date().toISOString(),
            false,
            "general"
          );
          return; // Mensagem do sistema tratada
        }

        const typingMatch = message.content.match(typingRegex);
        const nobodyTypingMatch = message.content.match(nobodyTypingRegex);

        if (typingMatch || nobodyTypingMatch) {
          // É uma notificação de digitação (do chat geral)
          // A notificação de digitação do backend atual só é para o chat geral.
          if (currentChatTarget === "general") {
            typingIndicator.textContent = message.content;
          } else {
            typingIndicator.textContent = ""; // Garante que não mostra notificação geral em chat privado
          }
          return; // Notificação tratada, não é mensagem de chat
        }

        // Se for texto simples que não é entrada/saída nem notificação de digitação
        // E *se* o chat geral estiver ativo, tenta parsear como mensagem de chat geral.
        // O backend ainda pode broadcastar texto simples no formato original "[ts] user: content".
        if (currentChatTarget === "general") {
          const generalMsgRegex = /\[(.*?)\] (.*?): (.*)/;
          const match = message.content.match(generalMsgRegex);

          if (match) {
            // Mensagem geral no formato esperado
            const timestampStr = match[1]; // Ex: "2023-10-27 10:30:00"
            const sender = match[2];
            const content = match[3];
            // Tenta criar uma data. Se falhar, usa a string original ou null.
            const timestamp =
              new Date(timestampStr).toString() === "Invalid Date"
                ? null
                : new Date(timestampStr).toISOString();

            displayTextMessage(
              sender,
              content,
              timestamp,
              sender === currentUser,
              "general"
            );
            return; // Mensagem geral tratada
          } else {
            // Texto simples desconhecido no chat geral
            console.warn(
              "Mensagem de texto simples desconhecida no chat geral:",
              message.content
            );
            // Opcional: Exibir como mensagem do sistema desconhecida?
            // displayTextMessage('Sistema', `Mensagem desconhecida: ${message.content}`, new Date().toISOString(), false, 'general');
          }
        }
        // Se for texto simples e não for para o chat geral, simplesmente ignora.
        return; // Texto simples tratado ou ignorado
      }

      // --- Lógica para mensagens JSON ---
      // Assume que mensagens JSON vêm com um campo 'type'

      // 2. Mensagem Privada (Esperando JSON: { type: 'private', sender: '...', receiver: '...', content: '...', timestamp: '...' })
      if (
        message.type === "private" &&
        message.sender &&
        message.receiver &&
        typeof message.content === "string" &&
        message.timestamp
      ) {
        // Determina para qual chat privado esta mensagem é
        const targetChat =
          message.sender === currentUser ? message.receiver : message.sender;
        displayTextMessage(
          message.sender,
          message.content,
          message.timestamp,
          message.sender === currentUser,
          targetChat
        );
        addRecentChat(targetChat); // Garante que o contato aparece na lista
        return; // Mensagem privada tratada
      }

      // 3. Mensagem de Arquivo (Esperando JSON: { type: 'file', sender: '...', receiver: '...'|null, filename: '...', path: '...', timestamp: '...' })
      if (
        message.type === "file" &&
        message.sender &&
        message.filename &&
        message.path &&
        message.timestamp
      ) {
        // Determina para qual chat (geral ou privado) esta mensagem de arquivo é
        const targetChat =
          message.receiver === null || message.receiver === "general"
            ? "general"
            : message.sender === currentUser
            ? message.receiver
            : message.sender;
        displayFileMessage(
          message.sender,
          message.filename,
          message.path,
          message.timestamp,
          message.sender === currentUser,
          targetChat
        );
        if (targetChat !== "general") {
          addRecentChat(targetChat); // Garante que o contato aparece na lista
        }
        return; // Mensagem de arquivo tratada
      }

      // 4. Outros tipos de mensagem JSON que o backend possa enviar (ex: private typing notifications)
      // Se o backend enviar JSON para notificações de digitação privada:
      // Ex: { type: 'typing_private', sender: 'user', recipient: 'me', status: true }
      if (
        message.type === "typing_private" &&
        message.recipient === currentUser &&
        message.sender &&
        message.status !== undefined
      ) {
        // Só atualiza o indicador se estiver no chat privado com este usuário
        if (currentChatTarget === message.sender) {
          typingIndicator.textContent = message.status
            ? `${message.sender} está digitando...`
            : "";
        }
        return; // Notificação privada de digitação tratada
      }

      // Se chegou aqui, a mensagem WS (JSON) era de um tipo desconhecido ou faltou campo(s)
      console.warn(
        "Mensagem WS JSON recebida em formato inesperado ou incompleta:",
        message
      );
    };

    websocket.onerror = (event) => {
      console.error("WebSocket error observed:", event);
      displayTextMessage(
        "Sistema",
        "Erro na conexão com o chat. Tentando reconectar...",
        null,
        false,
        currentChatTarget
      );
      // Limpa a referência para forçar uma nova conexão
      websocket = null;
      // Tenta reconectar após um pequeno delay
      setTimeout(connectWebSocket, 5000); // Tenta reconectar após 5 segundos
    };

    websocket.onclose = (event) => {
      console.log("WebSocket connection closed:", event);
      websocket = null; // Limpa a referência

      let reconnectDelay = 5000; // Default 5 seconds

      if (event.wasClean) {
        console.log(
          `Connection closed cleanly, code=${event.code} reason=${event.reason}`
        );
        // Códigos de fechamento comuns: 1000 (Normal), 1001 (Going Away), 1006 (Abnormal closure)
        // Códigos customizados (4000-4999)
        if (event.code === 4000 || event.code === 1008) {
          // 4000 custom, 1008 Policy Violation (ex: token inválido)
          alert(
            "Sua sessão expirou ou é inválida. Por favor, faça login novamente."
          );
          window.location.href = "/login-page"; // Redireciona para login
          return; // Não tenta reconectar se a sessão expirou
        }
        // Para outros fechamentos limpos que não são expiração de sessão, pode tentar reconectar
        // se for um problema temporário ou se o servidor fechou por algum motivo esperado que pode se resolver.
        // Se o código indica um fechamento intencional que não requer reconexão (ex: 1000 por logout no servidor), não reconecta.
        if (event.code !== 1000 && event.code !== 1001) {
          displayTextMessage(
            "Sistema",
            `Conexão com o chat fechada inesperadamente (Código: ${event.code}). Tentando reconectar...`,
            null,
            false,
            currentChatTarget
          );
          setTimeout(connectWebSocket, reconnectDelay);
        } else {
          displayTextMessage(
            "Sistema",
            "Conexão com o chat fechada.",
            null,
            false,
            currentChatTarget
          );
        }
      } else {
        // Ex: servidor caiu ou rede offline (código 1006)
        console.error("Connection died (code 1006 or similar)");
        displayTextMessage(
          "Sistema",
          "Conexão com o chat perdida. Tentando reconectar...",
          null,
          false,
          currentChatTarget
        );
        setTimeout(connectWebSocket, reconnectDelay); // Tenta reconectar
      }
    };
  }

  // --- Event Listeners ---

  // Enviar mensagem ao clicar no botão
  sendMessageBtn.addEventListener("click", () => {
    const content = messageInput.value.trim();
    if (!content) return; // Não envia mensagem vazia

    if (websocket && websocket.readyState === WebSocket.OPEN) {
      if (currentChatTarget === "general") {
        // Enviar mensagem geral como texto simples (compatível com backend atual, que espera texto para save_message)
        websocket.send(content);
        // Frontend espera a mensagem de volta via broadcast WS para exibir, no formato "[ts] user: content"
      } else {
        // Enviar mensagem privada como JSON (backend modificado irá lidar com isso)
        const privateMessage = {
          type: "private",
          recipient: currentChatTarget,
          content: content,
        };
        websocket.send(JSON.stringify(privateMessage));
        // Frontend espera a mensagem de volta via WS (enviada pelo backend para si mesmo e o destinatário)
        // no formato JSON { type: 'private', sender: currentUser, receiver: target, content: '...', timestamp: '...' }
      }
      messageInput.value = ""; // Limpa o input

      // Envia notificação para parar de digitar se necessário
      // A lógica de notificação de digitação do backend atual só funciona para o chat geral.
      // Se estiver em chat privado, o envio de JSON para notificação exigiria implementação no backend.
      if (typingTimer) {
        clearTimeout(typingTimer);
        typingTimer = null;
        // No backend atual, parar de digitar no chat geral é implícito ao enviar uma msg.
        // Se implementarmos notificação de digitação privada via JSON, precisaríamos enviar um status=false aqui.
      }
      // Limpa o indicador de digitação imediatamente no frontend ao enviar uma mensagem
      typingIndicator.textContent = "";
    } else {
      console.warn("WebSocket não está conectado. Mensagem não enviada.");
      displayTextMessage(
        "Sistema",
        "Não foi possível enviar a mensagem: conexão offline.",
        null,
        false,
        currentChatTarget
      );
    }
  });

  // Enviar mensagem ao pressionar Enter
  messageInput.addEventListener("keypress", (event) => {
    if (event.key === "Enter") {
      event.preventDefault(); // Evita quebra de linha no input
      sendMessageBtn.click(); // Simula clique no botão de enviar
    }
  });

  // Notificação de digitação
  messageInput.addEventListener("input", () => {
    // A lógica de notificação de digitação no backend atual só funciona para o chat geral.
    // O comando "/typing" só faz sentido no chat geral.
    if (
      currentChatTarget === "general" &&
      websocket &&
      websocket.readyState === WebSocket.OPEN
    ) {
      if (messageInput.value.length > 0) {
        if (!typingTimer) {
          // Envia /typing APENAS se começar a digitar e não houver timer ativo
          websocket.send("/typing"); // Backend atual entende este texto
          // console.log("Enviado: /typing");
        }
        // Reseta o timer cada vez que digita
        clearTimeout(typingTimer);
        typingTimer = setTimeout(() => {
          // O timer expira, o usuário parou de digitar por um tempo
          typingTimer = null;
          // No backend atual, parar de digitar é implícito ao enviar a próxima msg
          // ou após um tempo se não enviar nada, o manager remove.
          // Não é necessário enviar um comando de "parar de digitar" aqui.
        }, TYPING_TIMEOUT); // Tempo sem digitar para considerar que parou
      } else {
        // Input está vazio (após apagar), parou de digitar
        if (typingTimer) {
          clearTimeout(typingTimer);
          typingTimer = null;
          // Se o backend tiver um comando para parar de digitar explicitamente
          // websocket.send("/stopped_typing"); // Exemplo (não implementado no backend)
        }
      }
    }
    // Lógica de notificação de digitação para chat privado (REQUER IMPLEMENTAÇÃO NO BACKEND)
    // Exemplo JSON: websocket.send(JSON.stringify({ type: 'typing_private', recipient: currentChatTarget, status: true|false }));
  });

  // Logout
  logoutBtn.addEventListener("click", async () => {
    try {
      // Fecha a conexão WebSocket antes de deslogar
      if (websocket && websocket.readyState === WebSocket.OPEN) {
        // Usa código 1000 (Normal Closure) para indicar fechamento limpo
        websocket.close(1000, "Logout");
      }

      const response = await fetch("/logout", {
        method: "POST",
      });
      if (response.ok) {
        // Redirecionar para a página de login ou home pública
        window.location.href = "/login-page"; // Ou '/'
      } else {
        // Mesmo em caso de erro no backend, tentar deslogar localmente redirecionando
        console.error("Erro no backend ao fazer logout:", response.statusText);
        alert("Erro ao fazer logout. Redirecionando...");
        window.location.href = "/login-page";
      }
    } catch (error) {
      console.error("Erro na rede ao fazer logout:", error);
      alert("Erro na rede ao fazer logout. Redirecionando...");
      window.location.href = "/login-page";
    }
  });

  // Buscar usuários
  userSearchInput.addEventListener("input", async () => {
    const query = userSearchInput.value.trim();
    userSearchResultsList.innerHTML = ""; // Limpa resultados anteriores

    // Mínimo 2 caracteres para buscar, conforme backend
    if (query.length < 2) {
      return;
    }

    try {
      // Usa o endpoint GET /users/search
      // O backend em routes.py agora retorna lista de objetos {username: ...}
      const response = await fetch(
        `/users/search?q=${encodeURIComponent(query)}`
      );
      if (response.ok) {
        const users = await response.json();
        // users é uma lista como [{"username": "user1"}, {"username": "user2"}]
        users.forEach((userObj) => {
          const username = userObj.username;
          // Não adiciona o próprio usuário nos resultados da busca
          if (username === currentUser) return;

          const listItem = document.createElement("li");
          listItem.dataset.chatTarget = username;
          listItem.innerHTML = `<i class="fas fa-user"></i> ${username}`; // Ícone + nome
          listItem.addEventListener("click", () => {
            switchChat(username);
            userSearchInput.value = ""; // Limpa a busca
            userSearchResultsList.innerHTML = ""; // Limpa resultados visuais
          });
          userSearchResultsList.appendChild(listItem);
        });
      } else if (response.status === 401) {
        console.warn("Sessão expirada durante a busca, redirecionando...");
        window.location.href = "/login-page"; // Redireciona se desautenticou
      } else {
        // console.error('Erro na busca de usuários:', response.statusText);
        // Se a busca não encontrar nada, a lista fica vazia, o que é esperado.
        // Não precisa exibir erro para o usuário.
      }
    } catch (error) {
      console.error("Erro na busca de usuários:", error);
      // Não exibir erro na UI para o usuário, apenas no console
    }
  });

  // Upload de arquivo
  fileInput.addEventListener("change", async (event) => {
    const file = event.target.files[0];
    if (!file) {
      return; // Nenhum arquivo selecionado
    }

    // Validação básica de tamanho/tipo (opcional)
    // if (file.size > 10 * 1024 * 1024) { // Ex: 10MB limite
    //     alert("Arquivo muito grande. Limite de 10MB.");
    //     fileInput.value = '';
    //     return;
    // }
    // if (!file.type.startsWith('image/') && !file.type === 'application/pdf') { // Ex: Apenas imagens e PDF
    //      alert("Tipo de arquivo não permitido.");
    //      fileInput.value = '';
    //      return;
    // }

    const formData = new FormData();
    formData.append("file", file); // 'file' deve corresponder ao nome do parâmetro no endpoint POST /upload/

    // Opcional: mostrar algum feedback de upload (mensagem "Enviando...")
    // displayTextMessage(currentUser, `Enviando arquivo: ${file.name}...`, new Date().toISOString(), true, currentChatTarget);

    try {
      // Usa o endpoint POST /upload/
      const response = await fetch("/upload/", {
        method: "POST",
        body: formData,
      });

      if (response.ok) {
        const result = await response.json(); // Assume que retorna JSON { filename: ..., message: ... }
        console.log("Upload successful:", result);

        // *** IMPORTANTE ***
        // Após o upload bem-sucedido, envia uma mensagem VIA WEBSOCKET
        // para notificar o(s) destinatário(s) e a si mesmo sobre o arquivo enviado.
        // O backend `/ws` modificado irá receber este JSON e roteá-lo/salvá-lo.
        if (websocket && websocket.readyState === WebSocket.OPEN) {
          const fileMessage = {
            type: "file",
            // receiver: null ou 'general' para chat geral, nome de usuário para privado
            receiver:
              currentChatTarget === "general" ? null : currentChatTarget,
            filename: result.filename,
            // path: O backend /upload/ não retorna o path completo, apenas filename.
            // O frontend precisa construir o path acessível, assumindo a pasta /uploads
            // Ex: /uploads/nomearquivo.ext
            path: `/uploads/${result.filename}`, // Assumindo que a pasta 'uploads' é servida em '/uploads'
          };
          websocket.send(JSON.stringify(fileMessage));
          if (currentChatTarget !== "general") {
            addRecentChat(currentChatTarget); // Garante que o destinatário está na lista de recentes
          }
          // A mensagem visual no chat virá do onmessage handler quando o backend
          // enviar esta notificação de volta (incluindo timestamp e path correto).
        } else {
          console.warn(
            "WebSocket não está conectado. Notificação de arquivo não enviada via WS."
          );
          displayTextMessage(
            "Sistema",
            `Arquivo ${file.name} enviado, mas WS offline. Notificação não enviada.`,
            null,
            false,
            currentChatTarget
          );
        }
      } else if (response.status === 401) {
        console.warn("Sessão expirada durante o upload, redirecionando...");
        window.location.href = "/login-page"; // Redireciona se desautenticou
      } else {
        const errorText = await response.text();
        console.error("Upload failed:", response.status, errorText);
        displayTextMessage(
          "Sistema",
          `Erro ao enviar arquivo: ${file.name}`,
          new Date().toISOString(),
          false,
          currentChatTarget
        );
      }
    } catch (error) {
      console.error("Upload error:", error);
      displayTextMessage(
        "Sistema",
        `Erro na rede ao enviar arquivo: ${file.name}`,
        new Date().toISOString(),
        false,
        currentChatTarget
      );
    } finally {
      fileInput.value = ""; // Limpa o input de arquivo para poder selecionar o mesmo arquivo novamente
    }
  });

  // --- Inicialização ---

  // Carregar nome do usuário logado e iniciar WS
  async function init() {
    try {
      const response = await fetch("/users/me");
      if (response.ok) {
        const user = await response.json(); // Espera { username: "..." }
        currentUser = user.username;
        currentUsernameSpan.textContent = currentUser;
        console.log(`Current user: ${currentUser}`); // Log
        connectWebSocket(); // Inicia a conexão WS com o username
        loadRecentChats(); // Carrega contatos recentes via REST
        loadGeneralChat(); // Carrega o chat geral (histórico via REST, novas via WS)
      } else if (response.status === 401) {
        // Não autenticado, redireciona para login
        console.warn("Não autenticado no init. Redirecionando para login.");
        window.location.href = "/login-page";
      } else {
        console.error("Erro ao buscar usuário logado:", response.statusText);
        alert(
          "Erro ao carregar informações do usuário. Por favor, tente novamente."
        );
        // Opcional: redirecionar para login ou mostrar erro na tela
      }
    } catch (error) {
      console.error("Erro ao buscar usuário logado:", error);
      alert(
        "Erro na rede ao carregar informações do usuário. Por favor, tente novamente."
      );
      // Opcional: redirecionar para login ou mostrar erro na tela
    }
  }

  // Carregar lista de chats recentes (contatos)
  async function loadRecentChats() {
    try {
      const response = await fetch("/users/contacts");
      if (response.ok) {
        const contacts = await response.json(); // Espera lista de objetos { username: ... }
        contacts.forEach((contact) => {
          addRecentChat(contact.username); // Adiciona cada contato à lista visual
        });
      } else if (response.status === 401) {
        console.warn("Sessão expirada ao carregar contatos, redirecionando...");
        window.location.href = "/login-page"; // Redireciona se desautenticou
      } else {
        console.error("Erro ao carregar contatos:", response.statusText);
        // Não exibir erro para o usuário se a lista de contatos não carregar, apenas logar
      }
    } catch (error) {
      console.error("Erro ao carregar contatos:", error);
      // Não exibir erro para o usuário, apenas logar
    }
  }

  // Adiciona o listener para o item 'Chat Geral' que já existe no HTML
  // Este listener garante que switchChat('general') é chamado ao clicar no item estático
  const generalChatLi = recentChatsList.querySelector(
    'li[data-chat-target="general"]'
  );
  if (generalChatLi) {
    generalChatLi.addEventListener("click", () => {
      switchChat("general");
    });
    // Define o Chat Geral como ativo inicialmente
    // Isso pode ser feito após init() ou garantido por CSS/HTML inicial
    // generalChatLi.classList.add('active'); // Já chamado por updateActiveChatItem() em loadGeneralChat()
  } else {
    console.error("Elemento 'Chat Geral' não encontrado na lista de chats.");
    // Fallback: Cria o elemento e adiciona o listener se não encontrar no HTML
    const listItem = document.createElement("li");
    listItem.dataset.chatTarget = "general";
    listItem.innerHTML = `<i class="fas fa-users"></i> Chat Geral`;
    // listItem.classList.add('active'); // Será adicionado por updateActiveChatItem()
    listItem.addEventListener("click", () => switchChat("general"));
    recentChatsList.insertBefore(listItem, recentChatsList.firstChild); // Adiciona como primeiro
  }

  // Iniciar o aplicativo
  init();
});
