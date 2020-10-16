from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
from werkzeug.exceptions import abort
from fancySheep.auth import login_required
from fancySheep.db import get_db
import functools
from groupy.api.groups import Groups
from groupy.api.bots import Bots
import json

bp = Blueprint('website', __name__)

with open("config.json", "r") as f:
    config = json.loads(f.read())

@bp.route('/')
def index():
    db = get_db()
    if g.user is None:
        webhooks = []
    else:
        # Get user's webhooks
        webhooks = db.execute(
            'SELECT w.tag, message, count(b.bot_id) AS count'
            ' FROM webhook w'
            ' LEFT JOIN subscription '
            ' LEFT JOIN bot b'
            ' WHERE w.owner_id = (?)'
            ' GROUP BY w.tag',
            (g.user['user_id'],)
        ).fetchall()
    return render_template('website/index.html', webhooks=webhooks)

@bp.route('/create', methods=('GET', 'POST'))
@login_required
def create():
    if request.method == 'POST':
        # Get info
        tag = request.form['tag']
        message = request.form['message']
        error = None
        db = get_db()

        # Error check
        if not tag:
            error = 'Tag is required.'
        if not message:
            error = 'Message is required.'
        if db.execute(
            'SELECT tag FROM webhook WHERE tag = ?', (tag,)
        ).fetchone() is not None:
            error = 'Tag {} is already in use.'.format(tag)

        if error is not None:
            flash(error)
        else:
            # Insert to DB
            db.execute(
                'INSERT INTO webhook (tag, message, owner_id)'
                ' VALUES (?, ?, ?)',
                (tag, message, g.user['user_id'])
            )
            db.commit()
            return redirect(url_for('website.index'))

    return render_template('website/create.html')

def get_webhook(tag):
    webhook = get_db().execute(
        'SELECT w.tag, message, owner_id'
        ' FROM webhook w'
        ' WHERE w.tag = ?',
        (tag,)
    ).fetchone()

    if webhook is None:
        abort(404, "Webhook {0} doesn't exist.".format(tag))

    if webhook['owner_id'] != g.user['user_id']:
        abort(403)

    return webhook

def get_bots_by_tag(tag):
    bots = get_db().execute(
        'SELECT b.bot_id, b.group_id'
        ' FROM bot b'
        ' JOIN subscription'
        ' JOIN webhook w'
        ' WHERE w.tag = ?',
        (tag,)
    ).fetchall()

    return bots

def update_page(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        tag = kwargs["tag"]

        # Do view actions FIRST
        view(**kwargs)

        # Get freshest GroupMe data
        # TODO: Look at caching
        client = g.user["client"]
        groups = Groups(client.session)

        webhook = get_webhook(tag)

        bots = get_bots_by_tag(tag)
        current_groups = [groups.get(bot["group_id"]) for bot in
                          bots]

        available_groups = client.groups.list_all(per_page=100)

        return render_template('website/update.html',
                               webhook=webhook,
                               current_groups=current_groups,
                               available_groups=available_groups)

    return wrapped_view

@bp.route('/<string:tag>/update', methods=('GET', 'POST'))
@login_required
@update_page
def update(tag):
    if request.method == 'POST':
        # Get data
        new_tag = request.form['new_tag']
        message = request.form['message']
        error = None
        db = get_db()

        # Handle errors
        if not new_tag:
            error = 'Tag is required.'
        if not message:
            error = 'Message is required.'
        if tag != new_tag and db.execute(
            'SELECT * FROM webhook WHERE tag = ?', (new_tag,)
        ).fetchone() is not None:
            error = 'Tag {} is already in use.'.format(new_tag)

        if error is not None:
            flash(error)
        else:
            # Update the bot
            db.execute(
                'UPDATE webhook SET tag = ?, message = ?'
                ' WHERE tag = ?',
                (new_tag, message, tag)
            )
            db.commit()
            return redirect(url_for('website.index'))

@bp.route('/<string:tag>/add_subscription', methods=('POST',))
@login_required
@update_page
def add_subscription(tag):
    get_webhook(tag)

    if request.method == 'POST':
        # Get data
        new_group = request.form['new_group']
        error = None
        db = get_db()

        # Handle errors
        if not new_group:
            error = 'Group ID is required.'
        if db.execute(
            'SELECT * FROM subscription WHERE tag = ? AND group_id = ?', (tag, new_group)
        ).fetchone() is not None:
            error = 'Subscription is already active.'

        if error is not None:
            flash(error)
        else:
            # Check if a bot needs to be made
            if db.execute(
                'SELECT * FROM bot WHERE group_id = ?', (new_group,)
            ).fetchone() is None:
                # Make a bot
                client = g.user["client"]
                bot = client.bots.create(config["name"], new_group, config["avatar_url"])
                bot_id = bot.data["bot_id"]

                db.execute(
                    'INSERT INTO bot (bot_id, group_id)'
                    ' VALUES (?, ?)',
                    (bot_id, new_group,)
                )

            # Add subscription tie in
            db.execute(
                'INSERT INTO subscription (tag, group_id)'
                ' VALUES (?, ?)',
                (tag, new_group,)
            )
            db.commit()

            flash("Successfully created a subscription!")

@bp.route('/<string:tag>/remove_subscription', methods=('POST',))
@login_required
@update_page
def remove_subscription(tag):
    get_webhook(tag)

    if request.method == 'POST':
        group_id = request.form['group_id']

        # Remove the subscription
        db = get_db()
        db.execute('DELETE FROM subscription WHERE group_id = ? AND tag = ?', (group_id, tag))

        if db.execute(
                'SELECT * FROM subscription WHERE group_id = ? ', (group_id,)
            ).fetchone() is None:
            # A bot might no longer be referenced. Check
            bot = db.execute(
                'SELECT * FROM bot WHERE group_id = ? ', (group_id,)
            ).fetchone()

            if bot is not None:
                # Delete the bot
                client = g.user["client"]
                Bots(client.session).destroy(bot["bot_id"])

                # Remove the DB reference
                db.execute('DELETE FROM bot WHERE group_id = ?', (group_id,))

        db.commit()

        flash("Successfully removed a subscription!")

@bp.route('/<string:tag>/delete', methods=('POST',))
@login_required
def delete(tag):
    get_webhook(tag)
    db = get_db()
    db.execute('DELETE FROM webhook WHERE tag = ?', (tag,))
    db.commit()
    return redirect(url_for('website.index'))