"""
Bot code. Easy peasy lemon squeezy
"""

### Handle imports
import json

import requests
from flask import Blueprint, g, request, Response
from fancySheep import *
from fancySheep.db import get_db
from groupy.api.groups import Groups
from groupy.api.bots import Bots
from groupy.api.attachments import Mentions

from fancySheep.logger import *

### Logging
log_path = os.path.join("logs", "status.log")
logger = setup_logger(log_path)

bp = Blueprint('main', __name__, url_prefix='/main')

### Define methods
@bp.route('/fancy_sheep', methods=["GET"])
def generic_webhook():
    """
    Expects an HTTP GET with a message call.
    """
    tag = request.args.get("tag")
    logger.info("Received tag: {}".format(tag))

    webhook = None
    if not tag is None:
        db = get_db()
        webhook = db.execute(
            'SELECT * FROM webhook WHERE tag = ?', (tag,)
        ).fetchone()

    if webhook:
        process_webhook(webhook)
        return Response(status=200)
    else:
        return Response(status=404)

def process_webhook(webhook):
    """
    Post a message to various groups

    :param webhook: Webhook SQL row
    """
    db = get_db()
    subscriptions = db.execute(
            'SELECT * FROM subscription JOIN bot WHERE tag = ?', (webhook["tag"],)
        ).fetchall()

    for sub in subscriptions:
        post_groupme_msg(sub["bot_id"], sub["group_id"], webhook["message"])

def post_groupme_msg(bot_id, group_id, msg, notify_all=True):
    """
    Post a message to a groupme group.

    :param bot_id: Bot ID
    :param guid: Group ID
    :param msg: Message
    :param notify_all: Notify everyone or no?
    """
    if notify_all:
        user_ids = Groups(None).get(group_id)
        attachements = [Mentions(user_ids=user_ids)]
    else:
        attachements = []

    Bots(None).post(bot_id, msg, attachments=attachements)

#@app.route('/fancy_sheep_test', methods=["GET"])
def test_webhook():
    """For debug only."""
    return generic_webhook()

### Run code
logger.info("Starting bot")
if __name__ == '__main__':
    app.run()