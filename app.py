# -*- encoding: utf-8 -*-
from flask import Flask, request, abort

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, ImageSendMessage, ImagemapSendMessage
)
from linebot.models.imagemap import (
    BaseSize, ImagemapArea, URIImagemapAction, MessageImagemapAction, ImagemapArea
)
import sys
import os
import urllib.request
import json
from datetime import datetime
import re

app = Flask(__name__)

# 環境変数からchannel_secret・channel_access_tokenを取得
channel_secret = os.environ['LINE_CHANNEL_SECRET']
channel_access_token = os.environ['LINE_CHANNEL_ACCESS_TOKEN']

if channel_secret is None:
    print('Specify LINE_CHANNEL_SECRET as environment variable.')
    sys.exit(1)
if channel_access_token is None:
    print('Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.')
    sys.exit(1)

line_bot_api = LineBotApi(channel_access_token)
handler = WebhookHandler(channel_secret)

weapons_json = open("weapons.json", "r", encoding="utf-8")
weapons = json.load(weapons_json)


def get_battle_stage(event, rule):
    req = urllib.request.Request(
        "https://spla2.yuu26.com/{rule}/now".format(rule=rule))
    req.add_header("user-agent", "@nohararc")
    with urllib.request.urlopen(req) as res:
        response_body = res.read().decode("utf-8")
        response_json = json.loads(response_body.split("\n")[0])
        data = response_json["result"][0]

        now_start = datetime.strptime(data["start"], '%Y-%m-%dT%H:%M:%S')
        now_end = datetime.strptime(data["end"], '%Y-%m-%dT%H:%M:%S')

        line_bot_api.reply_message(
            event.reply_token, [
                TextSendMessage(text="{start} ～ {end}\n{rule}\n{stage1}\n{stage2}".format(
                    start=now_start.strftime("%m/%d %H:%M"), end=now_end.strftime("%m/%d %H:%M"),
                    rule=data["rule_ex"]["name"],
                    stage1=data["maps_ex"][0]["name"], stage2=data["maps_ex"][1]["name"]
                ))
            ]
        )


def get_specified_battle_stage(event, rule, m):
    req = urllib.request.Request(
        "https://spla2.yuu26.com/{rule}/schedule".format(rule=rule))
    req.add_header("user-agent", "@nohararc")
    with urllib.request.urlopen(req) as res:
        response_body = res.read().decode("utf-8")
        response_json = json.loads(response_body.split("\n")[0])
        data = response_json["result"]
        for d in data:
            start_time = datetime.strptime(d["start"], '%Y-%m-%dT%H:%M:%S')
            end_time = datetime.strptime(d["end"], '%Y-%m-%dT%H:%M:%S')
            start_hour = start_time.strftime("%H")
            print("start_hour = {}".format(start_hour))
            if int(m.group(1)) == int(start_hour):
                line_bot_api.reply_message(
                    event.reply_token, [
                        TextSendMessage(text="{start} ～ {end}\n{rule}\n{stage1}\n{stage2}".format(
                            start=start_time.strftime("%m/%d %H:%M"), end=end_time.strftime("%m/%d %H:%M"),
                            rule=d["rule_ex"]["name"],
                            stage1=d["maps_ex"][0]["name"], stage2=d["maps_ex"][1]["name"]
                        ))
                    ]
                )


@app.route("/")
def hello_world():
    return "hello world!"


@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text

    m_league = re.fullmatch(r'(?:リーグマッチ|リグマ)(\d+)時', text)
    m_gachi = re.fullmatch(r'(?:ガチマッチ|ガチマ)(\d+)時', text)
    m_regular = re.fullmatch(r'(?:レギュラーマッチ|ナワバリ)(\d+)時', text)

    if text == 'サーモンラン':
        req = urllib.request.Request("https://spla2.yuu26.com/coop/schedule")
        req.add_header("user-agent", "@nohararc")
        with urllib.request.urlopen(req) as res:
            response_body = res.read().decode("utf-8")
            response_json = json.loads(response_body.split("\n")[0])
            now = response_json["result"][0]
            the_next = response_json["result"][1]
            the_next_one = response_json["result"][2:]

            now_start = datetime.strptime(now["start"], '%Y-%m-%dT%H:%M:%S')
            now_end = datetime.strptime(now["end"], '%Y-%m-%dT%H:%M:%S')

            line_bot_api.reply_message(
                event.reply_token, [
                    TextSendMessage(text="{0} ～ {1}\n{2}\nブキ : {3}\n{4}\n{5}\n{6}".format(
                        now_start.strftime(
                            "%m/%d %H:%M"), now_end.strftime("%m/%d %H:%M"),
                        now["stage"]["name"],
                        now["weapons"][0]["name"], now["weapons"][1]["name"],
                        now["weapons"][2]["name"], now["weapons"][3]["name"]))
                ]
            )
    elif re.fullmatch(r'レギュラーマッチ|ナワバリ', text):
        rule = "regular"
        get_battle_stage(event, rule)

    elif re.fullmatch(r'ガチマッチ|ガチマ', text):
        rule = "gachi"
        get_battle_stage(event, rule)

    elif re.fullmatch(r'リーグマッチ|リグマ', text):
        rule = "league"
        get_battle_stage(event, rule)

    elif m_league is not None:
        rule = "league"
        get_specified_battle_stage(event, rule, m_league)

    elif m_gachi is not None:
        rule = "gachi"
        get_specified_battle_stage(event, rule, m_gachi)

    elif m_regular is not None:
        rule = "regular"
        get_specified_battle_stage(event, rule, m_regular)

    elif text in weapons:
        line_bot_api.reply_message(
            event.reply_token, [
                TextSendMessage(text="ブキ: {weapon}\nサブ: {sub}\nスペシャル: {special}".format(
                    weapon=text,
                    sub=weapons[text]["sub"],
                    special=weapons[text]["special"]
                ))
            ]
        )


if __name__ == "__main__":
    app.run()
