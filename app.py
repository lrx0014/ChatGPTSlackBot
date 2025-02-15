import json
import os
import re
import logging
from logging.handlers import TimedRotatingFileHandler

from revChatGPT.V3 import Chatbot
from slack_bolt import App

with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

ChatGPTConfig = {
    "api_key": config['openai_api_key']
}
if config["openai_engine"] != "":
    ChatGPTConfig["engine"] = config['openai_engine']

app = App(token=config['slack_token'], signing_secret=config['slack_signing_secret'])
chatbot = Chatbot(**ChatGPTConfig)

port = 4000
if config['port'] != "":
    port = config['port']


# 配置TimedRotatingFileHandler
handler = TimedRotatingFileHandler('log/requests.log', when='midnight', interval=1, backupCount=180, encoding='utf-8')
handler.setLevel(logging.INFO)
handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s:%(message)s'))

# 配置日志记录器
logger = logging.getLogger('requests')
logger.setLevel(logging.INFO)
logger.addHandler(handler)


# Listen for an event from the Events API
@app.event("app_mention")
def event_test(event, say):
    user = event['user']
    if "reset_chatgpt" in event['text']:
        chatbot.reset(convo_id=user)
        say("user:" + user + " reset chatgpt context done")
        return

    prompt = re.sub('(?:\s)<@[^, ]*|(?:^)<@[^, ]*', '', event['text'])
    try:
        response = chatbot.ask(prompt=prompt, convo_id=user)
        user = event['user']
        user = f"<@{user}> you asked:"
        asked = ['>', prompt]
        asked = "".join(asked)
        send = [user, asked, response]
        send = "\n".join(send)
    except Exception as e:
        print(e)
        send = "We're experiencing exceptionally high demand. Please, try again."

    # Get the `ts` value of the original message
    original_message_ts = event["ts"]

    # Use the `app.event` method to send a reply to the message thread
    say(send, thread_ts=original_message_ts)


@app.event("message")
def event_msg(event, say):
    user = event['user']
    if event['text'] == "reset_chatgpt":
        chatbot.reset(convo_id=user)
        say("user:" + user + " reset chatgpt context done")
        return

    prompt = re.sub('(?:\s)<@[^, ]*|(?:^)<@[^, ]*', '', event['text'])
    logger.info("user:"+user+" > " + prompt)
    try:
        response = chatbot.ask(prompt=prompt, convo_id=user)
        send = response
    except Exception as e:
        print(e)
        send = "We're experiencing exceptionally high demand. Please, try again."

    # Use the `app.event` method to send a reply to the message thread
    say(send)


if __name__ == "__main__":
    app.start(port)  # POST http://localhost:port/slack/events
