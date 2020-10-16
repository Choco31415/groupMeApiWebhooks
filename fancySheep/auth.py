# Handle imports
import functools
from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, redirect
)
from werkzeug.security import check_password_hash
from fancySheep.db import get_db
from groupy.client import Client
from groupy.api.bots import Bots
import json

# Global vars
bp = Blueprint('auth', __name__, url_prefix='/auth')

with open("config.json", "r") as f:
    config = json.loads(f.read())

# Define functions
@bp.route('/login')
def login():
    token = request.args.get('access_token')
    if not token is None:
        # Get client
        client = Client.from_token(token)
        error = None

        # Error check
        try:
            me = client.user.get_me()
        except:
            error = "Bad GroupMe login."

        if error is not None:
            flash(error)
        else:
            # Setup the session
            user_id = me["id"]
            username = me["name"]

            session.clear()
            session['user_id'] = user_id
            session['username'] = username
            session['token'] = token

            # Check for bot instances
            # Only useful in event of catastrophic DB failure
            bot_client = Bots(client.session)
            bots = bot_client.list()
            for bot in bots:
                if bot["name"] == config["name"]:
                    db = get_db()
                    if db.execute(
                            'SELECT * FROM bot WHERE group_id = ?', (bot["group_id"],)
                    ).fetchone() is None:
                        # This bot instance is unrecorded
                        bot_client.destroy(bot["bot_id"])

            return redirect(url_for('index'))

    return render_template('auth/login.html')

@bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')
    username = session.get('user_id')
    token = session.get('token')

    if user_id is None:
        g.user = None
    else:
        g.user = {"user_id": int(user_id),
                  "username": username,
                  "client": Client.from_token(token)}

def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('auth.login'))

        return view(**kwargs)

    return wrapped_view

@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))