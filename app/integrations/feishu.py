from __future__ import annotations

import httpx

from app.domain.models import InboundMessage, OutboundMessage, Platform


def verify_feishu_token(payload: dict, verification_token: str) -> bool:
    token = payload.get("token") or payload.get("header", {}).get("token")
    return not verification_token or token == verification_token


def parse_feishu_text_event(payload: dict) -> InboundMessage | None:
    if payload.get("type") == "url_verification":
        return None

    event = payload.get("event", {})
    message = event.get("message", {})
    if message.get("message_type") != "text":
        return None

    sender = event.get("sender", {}).get("sender_id", {})
    user_id = sender.get("open_id") or sender.get("user_id") or "unknown"
    chat_id = message.get("chat_id") or user_id
    message_id = message.get("message_id") or f"feishu:{chat_id}:{user_id}"
    content = message.get("content", "")
    return InboundMessage(
        platform=Platform.FEISHU,
        user_id=user_id,
        conversation_id=f"feishu:{chat_id}",
        content=_extract_text_content(content),
        message_id=f"feishu:{message_id}",
        metadata={"chat_id": chat_id, "message_id": message_id},
    )


async def send_feishu_text_reply(
    app_id: str,
    app_secret: str,
    message_id: str,
    outbound: OutboundMessage,
) -> None:
    if not app_id or not app_secret or not message_id:
        return
    async with httpx.AsyncClient(timeout=10) as client:
        token_response = await client.post(
            "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
            json={"app_id": app_id, "app_secret": app_secret},
        )
        token_response.raise_for_status()
        token = token_response.json().get("tenant_access_token")
        if not token:
            return
        response = await client.post(
            f"https://open.feishu.cn/open-apis/im/v1/messages/{message_id}/reply",
            headers={"Authorization": f"Bearer {token}"},
            params={"receive_id_type": "open_id"},
            json={"content": f'{{"text":"{_escape_json_text(outbound.content)}"}}', "msg_type": "text"},
        )
        response.raise_for_status()


def _extract_text_content(content: str) -> str:
    import json

    try:
        parsed = json.loads(content)
        return parsed.get("text", content)
    except json.JSONDecodeError:
        return content


def _escape_json_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")

