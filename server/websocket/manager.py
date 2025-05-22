from typing import Dict, Set, Tuple, Optional # Import Optional
from fastapi.websockets import WebSocket
import asyncio
import json # Importar json
# Adicione get_db_connection se precisar de DB ops aqui (pode ser passado ou importado)
# from server.database.database import get_db_connection # Exemplo

class ConnectionManager:
    def __init__(self):
        # Mapeia WebSocket -> username
        self.active_connections: Dict[WebSocket, str] = {}
        # Mapeia username -> WebSocket (para buscas rápidas)
        self.username_to_websocket: Dict[str, WebSocket] = {}

        # Lógica de chat privado antiga removida (private_chats)

        # Lógica de notificação de digitação (mantida, ajustada)
        self.typing_users: Set[str] = set() # Usuários digitando no chat geral
        self.typing_tasks: Dict[str, asyncio.Task] = {} # Tasks para timeout de digitação geral
        # Opcional: Adicionar lógica para notificação de digitação privada se o backend a suportar via WS JSON

    async def connect(self, websocket: WebSocket, username: str):
        await websocket.accept()
        self.active_connections[websocket] = username
        self.username_to_websocket[username] = websocket # Adiciona ao mapeamento

    def disconnect(self, websocket: WebSocket):
        username = self.active_connections.pop(websocket, None)
        if username and username in self.username_to_websocket:
             del self.username_to_websocket[username] # Remove do mapeamento

        # Lógica de digitação geral
        if username in self.typing_users:
            self.typing_users.remove(username)
            self._cancel_typing_task(username)
            # Cria task para broadcast para não bloquear o disconnect
            asyncio.create_task(self._broadcast_typing_status())

        # Lógica de remoção de chats privados antiga removida

    async def broadcast(self, message: str):
        """Envia mensagem para todos os usuários conectados."""
        # O broadcast agora pode receber texto (para mensagens de entrada/saída) ou JSON (para mensagens gerais estruturadas/arquivos gerais)
        for connection in list(self.active_connections.keys()): # Itera sobre uma cópia para evitar erro se alguém desconectar durante o loop
            try:
                 # Tenta enviar como texto, se for string
                 if isinstance(message, str):
                    await connection.send_text(message)
                 # Se for JSON string, envia como texto (frontend JS parseia)
                 elif isinstance(message, str) and message.startswith('{') and message.endswith('}'):
                      await connection.send_text(message)
                 # Se for objeto Python (dict/list), envia como JSON nativo (melhor prática, mas frontend JS atual espera string)
                 # else:
                 #     await connection.send_json(message)

            except RuntimeError:
                # WebSocket may be closing or already closed
                pass # Handle graceful closing
            except Exception as e:
                print(f"Erro ao enviar broadcast para {self.active_connections.get(connection, 'usuário desconhecido')}: {e}")
                # Opcional: self.disconnect(connection) - cuidado com o loop


    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Envia mensagem para um WebSocket específico."""
        # message pode ser string (para erros/sistema) ou JSON string
        try:
            # Envia como texto, mesmo que seja string JSON
            await websocket.send_text(message)
             # Ou send_json se o frontend for modificado para esperar isso
            # if isinstance(message, str) and message.startswith('{') and message.endswith('}'):
            #     await websocket.send_json(json.loads(message))
            # else:
            #     await websocket.send_text(message)

        except RuntimeError:
            # WebSocket may be closing or already closed
            pass
        except Exception as e:
            print(f"Erro ao enviar mensagem pessoal: {e}")
            # Opcional: self.disconnect(websocket)


    def get_websocket_by_username(self, username: str) -> Optional[WebSocket]:
        """Retorna o WebSocket de um usuário pelo nome."""
        return self.username_to_websocket.get(username)


    # Lógica de notificação de digitação (Geral)
    async def typing_notification(self, username: str):
        # Cancelar task anterior se existir
        self._cancel_typing_task(username)

        # Adicionar usuário aos que estão digitando no chat geral
        if username not in self.typing_users:
            self.typing_users.add(username)
            await self._broadcast_typing_status()

        # Criar task para remover após 3 segundos de inatividade
        self.typing_tasks[username] = asyncio.create_task(
            self._remove_typing_after_delay(username)
        )

    def _cancel_typing_task(self, username: str):
        if username in self.typing_tasks:
            task = self.typing_tasks.pop(username)
            task.cancel()
            # print(f"Task de digitação para {username} cancelada.") # Debug

    async def _remove_typing_after_delay(self, username: str, delay: int = 2):
        """Remove o status de digitação após um delay, a menos que a task seja cancelada."""
        try:
            await asyncio.sleep(delay)
            # Verifica se o usuário ainda está na lista antes de remover
            # Isso é importante caso ele comece a digitar novamente e uma nova task seja criada
            if username in self.typing_users and username not in self.typing_tasks:
                 # Pequena proteção, a task é removida do dict antes do sleep se uma nova começar
                 # A verificação principal é se a task não foi cancelada.
                 pass # Este caminho é menos provável com a lógica de cancelamento.
            elif username in self.typing_users and self.typing_tasks.get(username) != asyncio.current_task():
                 # Se o usuário está na lista, mas a task atual NÃO é a que está rodando para ele,
                 # significa que uma nova task foi criada. A task atual deve apenas terminar.
                 # print(f"Task de digitação antiga para {username} terminando.") # Debug
                 return


            if username in self.typing_users:
                 self.typing_users.remove(username)
                 # print(f"{username} parou de digitar (timeout).") # Debug
                 await self._broadcast_typing_status()

        except asyncio.CancelledError:
            # print(f"Task de digitação para {username} foi cancelada.") # Debug
            # A task foi cancelada (usuário digitou novamente ou desconectou)
            # Não faça nada aqui, a nova task ou o disconnect lidam com o status.
            pass
        except Exception as e:
            print(f"Erro na task de digitação para {username}: {e}")
            import traceback
            traceback.print_exc()


    async def _broadcast_typing_status(self):
        """Broadcasta o status de quem está digitando no chat geral."""
        # Ajustar o formato da mensagem para o frontend esperar "nome(s) está(ão) digitando..."
        if self.typing_users:
            users_list = list(self.typing_users)
            if len(users_list) == 1:
                message = f"{users_list[0]} está digitando..."
            else:
                # Junta os nomes, ex: "user1, user2 e user3 estão digitando..."
                users_str = ", ".join(users_list[:-1])
                message = f"{users_str} e {users_list[-1]} estão digitando..."
        else:
            message = "Ninguém está digitando." # Formato esperado pelo JS

        # Envia para todos os usuários conectados
        await self.broadcast(message)
        # print(f"Broadcast de digitação: {message}") # Debug


    # Opcional: Adicionar lógica para notificação de digitação privada se o backend suportar
    # async def notify_typing_private(self, sender_username: str, recipient_username: str, status: bool):
    #     recipient_ws = self.get_websocket_by_username(recipient_username)
    #     if recipient_ws:
    #         # Formato JSON que o frontend espera para notificação privada
    #         message = json.dumps({
    #             "type": "typing_private",
    #             "sender": sender_username,
    #             "recipient": recipient_username, # Pode ser útil para o frontend validar
    #             "status": status
    #         })
    #         await self.send_personal_message(message, recipient_ws)