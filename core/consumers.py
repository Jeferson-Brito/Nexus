import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

logger = logging.getLogger(__name__)


class CameraSignalingConsumer(AsyncWebsocketConsumer):
    """
    Consumer de sinalização WebRTC para monitoramento de câmera ao vivo.

    Cada usuário conectado entra no grupo: camera_user_{user_id}
    O gestor envia mensagens para o grupo do analista alvo (e vice-versa).

    Tipos de mensagem suportados:
      - camera_request : gestor solicita câmera do analista
      - offer          : analista envia oferta SDP ao gestor
      - answer         : gestor envia resposta SDP ao analista
      - ice_candidate  : troca de candidatos ICE (ambos os lados)
      - camera_stop    : gestor encerra a sessão
      - camera_denied  : analista informa que câmera não está disponível
    """

    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close()
            return

        self.user = user
        self.user_group = f"camera_user_{user.id}"

        # Entra no próprio grupo de câmera
        await self.channel_layer.group_add(self.user_group, self.channel_name)
        await self.accept()
        logger.info(f"[Camera WS] Usuário {user.username} conectado ao grupo {self.user_group}")

    async def disconnect(self, close_code):
        if hasattr(self, "user_group"):
            await self.channel_layer.group_discard(self.user_group, self.channel_name)

    async def receive(self, text_data):
        """Recebe mensagem do browser e roteia para o grupo correto."""
        try:
            data = json.loads(text_data)
        except (json.JSONDecodeError, TypeError):
            return

        msg_type = data.get("type")
        target_user_id = data.get("target_user_id")

        # Apenas gestores/admins podem iniciar câmera ou enviar answer/ICE como gestor
        is_gestor = await self._is_gestor_or_admin(self.user)

        if msg_type == "camera_request":
            if not is_gestor:
                return
            if not target_user_id:
                return
            # Envia solicitação ao analista alvo
            await self.channel_layer.group_send(
                f"camera_user_{target_user_id}",
                {
                    "type": "camera.request",
                    "from_user_id": self.user.id,
                    "from_user_name": self.user.get_full_name() or self.user.username,
                }
            )

        elif msg_type == "offer":
            # Analista enviando oferta SDP ao gestor
            if not target_user_id:
                return
            await self.channel_layer.group_send(
                f"camera_user_{target_user_id}",
                {
                    "type": "webrtc.relay",
                    "payload": {"type": "offer", "sdp": data.get("sdp")},
                }
            )

        elif msg_type == "answer":
            # Gestor enviando resposta SDP ao analista
            if not is_gestor or not target_user_id:
                return
            await self.channel_layer.group_send(
                f"camera_user_{target_user_id}",
                {
                    "type": "webrtc.relay",
                    "payload": {"type": "answer", "sdp": data.get("sdp")},
                }
            )

        elif msg_type == "ice_candidate":
            # Troca de ICE candidates (ambos os lados)
            if not target_user_id:
                return
            await self.channel_layer.group_send(
                f"camera_user_{target_user_id}",
                {
                    "type": "webrtc.relay",
                    "payload": {"type": "ice_candidate", "candidate": data.get("candidate")},
                }
            )

        elif msg_type == "camera_stop":
            # Gestor encerra a sessão
            if not is_gestor or not target_user_id:
                return
            await self.channel_layer.group_send(
                f"camera_user_{target_user_id}",
                {
                    "type": "webrtc.relay",
                    "payload": {"type": "camera_stop"},
                }
            )

        elif msg_type == "camera_denied":
            # Analista avisa que câmera não disponível
            if not target_user_id:
                return
            await self.channel_layer.group_send(
                f"camera_user_{target_user_id}",
                {
                    "type": "webrtc.relay",
                    "payload": {"type": "camera_denied"},
                }
            )

    # ── Handlers de mensagens vindas do channel layer ──

    async def camera_request(self, event):
        """Entrega ao analista a solicitação de câmera do gestor."""
        await self.send(text_data=json.dumps({
            "type": "camera_request",
            "from_user_id": event["from_user_id"],
            "from_user_name": event["from_user_name"],
        }))

    async def webrtc_relay(self, event):
        """Retransmite payload WebRTC (offer/answer/ICE/stop) ao destinatário."""
        await self.send(text_data=json.dumps(event["payload"]))

    @database_sync_to_async
    def _is_gestor_or_admin(self, user):
        try:
            return user.is_gestor() or user.is_administrador()
        except Exception:
            return False
