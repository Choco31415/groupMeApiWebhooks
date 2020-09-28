"""
Bot code. Easy peasy lemon squeezy
"""

### Handle imports
import os
import json
import requests
from flask import Flask, request, Response
from logger import *

### Logging
log_path = os.path.join("logs", "status.log")
logger = setup_logger(log_path)

### Load config
# Use os.path, it's cookie cutter stuff people >3>
config_file = os.path.join("data", "config.json")
with open(config_file, "r") as f:
    config = json.loads(f.read())

groups = config["groups"]
messages = config["messages"]

groupme_base_api = "https://api.groupme.com/v3"
groupme_api_bot_post = "/bots/post"
groupme_api_chat = "/chat"

app = Flask(__name__)

### Define methods
@app.route('/fancy_sheep', methods=["GET"])
def generic_webhook():
    """
    Expects an HTTP GET with a message call.
    """
    call = request.args.get("call")
    logger.info("Received call: {}".format(call))

    found = False
    if not call is None:
        for message in messages:
            if message["call"].strip().lower() == \
                    call.strip().lower():
                process_message(message)
                found = True

    if found:
        return Response(status=200)
    else:
        return Response(status=404)

def process_message(message):
    """
    Post a message to various groups

    :param message: Message JSON obj
    """
    msg = message["response"]
    for group_name in message["post_to"]:
        group = groups[group_name]
        guid = group["group_ID"]
        bot_id = group["bot_ID"]
        post_groupme_msg(bot_id, guid, msg)

def post_groupme_msg(bot_id, guid, msg, notify_all=True):
    """
    Post a message to a groupme group.

    :param bot_id: Bot ID
    :param guid: Group ID
    :param msg: Message
    :param notify_all: Notify everyone or no?
    """
    if notify_all:
        user_ids = get_groupme_ids(bot_id, guid)

        attachments = [{
                "loci": [],
                "type": "mentions",
                "user_ids": user_ids
        }]
    else:
        attachments = []

    data = {
        "bot_id": bot_id,
        "text": msg,
        "attachments": attachments
    }

    url = groupme_base_api + groupme_api_bot_post
    requests.post(url = url, data = data)

def get_groupme_ids(bot_id, guid):
    """
    Get the user id's of all members in a group.
    :return:
    """
    data = {
        "bot_id": bot_id,
        "guid": guid
    }

    url = groupme_base_api + "/groups/" + guid
    print(url)
    r = requests.get(url=url, data = data)
    print(r.text)

    return json.loads(r.text)

@app.route('/fancy_sheep_test', methods=["GET"])
def test_webhook():
    """For debug only."""
    return generic_webhook()

### Run code
logger.info("Starting bot")
if __name__ == '__main__':
    app.run()