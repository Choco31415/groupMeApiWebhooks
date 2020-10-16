# Handle imports
import functools
from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, redirect
)
from werkzeug.security import check_password_hash
from fancySheep.db import get_db
from groupy.client import Client
import json

# Global vars
bp = Blueprint('auth', __name__, url_prefix='/auth')
client = None

with open("config.json", "r") as f:
    config = json.loads(f.read())

# Define functions
@bp.route('/login', methods=('GET', 'POST'))
def login():
    global client
    print("a")
    if request.method == 'POST':
        token = request.form['token']
        client = Client.from_token(token)
        error = None

        try:
            me = client.user.get_me()
        except:
            error = "Bad GroupMe login."

        if error is not None:
            flash(error)
        else:
            username = "placeholder"
            user_id = "placeholder"
            print(me)

            session.clear()
            session['user_id'] = user_id

            db = get_db()
            if db.execute(
                'SELECT id FROM user WHERE id = ?', (user_id,)
            ).fetchone() is not None:
                #Add user entry
                db.execute(
                    'INSERT INTO user (id, username)'
                    ' VALUES (?, ?)',
                    (user_id, username)
                )
                db.commit()
            return redirect(url_for('index'))

    return render_template('auth/login.html', client_id=config["client_id"])

@bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')

    if user_id is None:
        g.user = None
    else:
        g.user = get_db().execute(
            'SELECT * FROM user WHERE id = ?', (user_id,)
        ).fetchone()

def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('auth.login'))

        return view(**kwargs)

    return wrapped_view