from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import PlainTextResponse

from app.core.container import AppContainer, get_container
from app.domain.models import OutboundMessage, Platform
from app.integrations.feishu import parse_feishu_text_event, send_feishu_text_reply, verify_feishu_token
from app.integrations.wecom import (
    build_wecom_text_reply,
    parse_wecom_text_message,
    verify_wecom_signature,
)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.get("/wecom", response_class=PlainTextResponse)
async def verify_wecom(
    msg_signature: str = Query(alias="msg_signature"),
    timestamp: str = Query(),
    nonce: str = Query(),
    echostr: str = Query(),
    container: AppContainer = Depends(get_container),
) -> str:
    if not verify_wecom_signature(container.settings.wecom_token, msg_signature, timestamp, nonce, echostr):
        return "invalid signature"
    return echostr


@router.post("/wecom", response_class=PlainTextResponse)
async def wecom_webhook(request: Request, container: AppContainer = Depends(get_container)) -> str:
    body = (await request.body()).decode("utf-8")
    inbound = parse_wecom_text_message(body)
    if inbound is None:
        return "success"
    first_seen = await container.idempotency.mark_once(inbound.message_id)
    if not first_seen:
        return "success"
    outbound = await container.agent.answer(inbound)
    return build_wecom_text_reply(inbound, outbound)


@router.post("/feishu")
async def feishu_webhook(payload: dict, container: AppContainer = Depends(get_container)) -> dict:
    if payload.get("type") == "url_verification":
        return {"challenge": payload.get("challenge")}
    if not verify_feishu_token(payload, container.settings.feishu_verification_token):
        return {"code": 401, "msg": "invalid token"}

    inbound = parse_feishu_text_event(payload)
    if inbound is None:
        return {"code": 0, "msg": "ignored"}
    first_seen = await container.idempotency.mark_once(inbound.message_id)
    if not first_seen:
        return {"code": 0, "msg": "duplicate"}

    outbound = await container.agent.answer(inbound)
    await send_feishu_text_reply(
        app_id=container.settings.feishu_app_id,
        app_secret=container.settings.feishu_app_secret,
        message_id=inbound.metadata.get("message_id", ""),
        outbound=outbound,
    )
    return {"code": 0, "msg": "ok"}


def ignored_message(platform: Platform, conversation_id: str) -> OutboundMessage:
    return OutboundMessage(platform=platform, conversation_id=conversation_id, content="")

