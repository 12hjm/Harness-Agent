import hashlib

from app.integrations.feishu import parse_feishu_text_event
from app.integrations.wecom import parse_wecom_text_message, verify_wecom_signature


def test_verify_wecom_signature():
    token = "token"
    timestamp = "123"
    nonce = "abc"
    echostr = "hello"
    signature = hashlib.sha1("".join(sorted([token, timestamp, nonce, echostr])).encode()).hexdigest()

    assert verify_wecom_signature(token, signature, timestamp, nonce, echostr)


def test_parse_wecom_text_message():
    inbound = parse_wecom_text_message(
        """
        <xml>
          <ToUserName><![CDATA[corp]]></ToUserName>
          <FromUserName><![CDATA[user-a]]></FromUserName>
          <MsgType><![CDATA[text]]></MsgType>
          <Content><![CDATA[退款多久到账]]></Content>
          <MsgId>42</MsgId>
        </xml>
        """
    )

    assert inbound is not None
    assert inbound.user_id == "user-a"
    assert inbound.content == "退款多久到账"


def test_parse_feishu_text_event():
    inbound = parse_feishu_text_event(
        {
            "event": {
                "sender": {"sender_id": {"open_id": "ou_x"}},
                "message": {
                    "message_type": "text",
                    "chat_id": "oc_x",
                    "message_id": "om_x",
                    "content": "{\"text\":\"发票怎么开\"}",
                },
            }
        }
    )

    assert inbound is not None
    assert inbound.user_id == "ou_x"
    assert inbound.content == "发票怎么开"

