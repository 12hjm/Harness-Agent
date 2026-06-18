from __future__ import annotations

import hashlib
import time
import xml.etree.ElementTree as ET

from app.domain.models import InboundMessage, OutboundMessage, Platform


def verify_wecom_signature(token: str, signature: str, timestamp: str, nonce: str, echostr: str) -> bool:
    values = sorted([token, timestamp, nonce, echostr])
    digest = hashlib.sha1("".join(values).encode("utf-8")).hexdigest()
    return digest == signature


def parse_wecom_text_message(xml_body: str) -> InboundMessage | None:
    root = ET.fromstring(xml_body)
    msg_type = _find_text(root, "MsgType")
    if msg_type != "text":
        return None
    user_id = _find_text(root, "FromUserName") or "unknown"
    conversation_id = _find_text(root, "ToUserName") or user_id
    message_id = _find_text(root, "MsgId") or f"wecom-{int(time.time())}-{user_id}"
    return InboundMessage(
        platform=Platform.WECOM,
        user_id=user_id,
        conversation_id=f"wecom:{conversation_id}:{user_id}",
        content=_find_text(root, "Content") or "",
        message_id=f"wecom:{message_id}",
        metadata={"raw_msg_type": msg_type},
    )


def build_wecom_text_reply(inbound: InboundMessage, outbound: OutboundMessage) -> str:
    to_user = inbound.user_id
    from_user = inbound.metadata.get("to_user") or inbound.conversation_id.split(":")[1]
    content = outbound.content
    return (
        "<xml>"
        f"<ToUserName><![CDATA[{to_user}]]></ToUserName>"
        f"<FromUserName><![CDATA[{from_user}]]></FromUserName>"
        f"<CreateTime>{int(time.time())}</CreateTime>"
        "<MsgType><![CDATA[text]]></MsgType>"
        f"<Content><![CDATA[{content}]]></Content>"
        "</xml>"
    )


def _find_text(root: ET.Element, tag: str) -> str | None:
    node = root.find(tag)
    return node.text if node is not None else None

