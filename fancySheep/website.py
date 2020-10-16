from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
from werkzeug.exceptions import abort

from fancySheep.auth import login_required
from fancySheep.db import get_db

bp = Blueprint('website', __name__)

@bp.route('/')
def index():
    db = get_db()
    if g.user is None:
        webhooks = []
    else:
        webhooks = db.execute(
            'SELECT w.tag, message, count(b.bot_id) AS count'
            ' FROM webhook w'
            ' LEFT JOIN subscription '
            ' LEFT JOIN bot b'
            ' WHERE w.owner_id = (?)'
            ' GROUP BY w.tag',
            (g.user['id'],)
        ).fetchall()
        print(webhooks)
    return render_template('website/index.html', webhooks=webhooks)

@bp.route('/create', methods=('GET', 'POST'))
@login_required
def create():
    if request.method == 'POST':
        tag = request.form['tag']
        message = request.form['message']
        error = None
        db = get_db()

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

            db.execute(
                'INSERT INTO webhook (tag, message, owner_id)'
                ' VALUES (?, ?, ?)',
                (tag, message, g.user['id'])
            )
            db.commit()
            return redirect(url_for('website.index'))

    return render_template('website/create.html')

def get_webhook(tag):
    webhook = get_db().execute(
        'SELECT w.tag, message, owner_id, group_id, b.bot_id'
        ' FROM webhook w'
        ' LEFT JOIN subscription '
        ' LEFT JOIN bot b'
        ' WHERE w.tag = ?',
        (tag,)
    ).fetchone()

    if webhook is None:
        abort(404, "Webhook {0} doesn't exist.".format(tag))

    if webhook['owner_id'] != g.user['id']:
        abort(403)

    return webhook

def get_bot(bot_id, check_exist=False):
    bot = get_db().execute(
        'SELECT b.bot_id, owner_id, group_id'
        ' FROM bot b'
        ' WHERE b.bot_id = ?',
        (bot_id,)
    ).fetchone()

    if check_exist and bot is None:
        abort(404, "Bot {0} doesn't exist.".format(bot_id))

    return bot

@bp.route('/<string:tag>/update', methods=('GET', 'POST'))
@login_required
def update(tag):
    webhook = get_webhook(tag)

    if request.method == 'POST':
        new_tag = request.form['new_tag']
        message = request.form['message']
        error = None
        db = get_db()

        if not new_tag:
            error = 'Tag is required.'
        if not message:
            error = 'Message is required.'
        if tag != new_tag and db.execute(
            'SELECT tag FROM webhook WHERE tag = ?', (new_tag,)
        ).fetchone() is not None:
            error = 'Tag {} is already in use.'.format(new_tag)

        if error is not None:
            flash(error)
        else:
            db.execute(
                'UPDATE webhook SET tag = ?, message = ?'
                ' WHERE tag = ?',
                (new_tag, message, tag)
            )
            db.commit()
            return redirect(url_for('website.index'))

    return render_template('website/update.html', webhook = webhook)

@bp.route('/<string:tag>/add_subscription', methods=('POST',))
@login_required
def add_subscription(tag):
    group_id = request.form['group_id']
    bot_id = request.form['bot_id']
    error = None

    webhook = get_webhook(tag)
    bot = get_bot(bot_id, check_exist=False)

    if not group_id:
        error = 'Group ID is required.'
    if not bot_id:
        error = 'Bot ID is required.'

    if error is None:
        db = get_db()
        if bot is None:
            db.execute(
                'INSERT INTO bot (bot_id, group_id, owner_id)'
                ' VALUES (?, ?, ?)',
                (bot_id, group_id, g.user['id'])
            )
        db.execute(
            'INSERT INTO subscription (bot_id, tag)'
            ' VALUES (?, ?)',
            (bot_id, tag)
        )
        db.commit()
    return render_template('website/update.html', webhook = webhook)

@bp.route('/<string:tag>/remove_subscription', methods=('POST',))
@login_required
def remove_subscription(tag):
    bot_id = request.form['bot_id']
    error = None

    webhook = get_webhook(tag)
    get_bot(bot_id, check_exist=True)

    if error is None:
        db = get_db()
        db.execute(
            'DELETE FROM bot (bot_id, tag)'
            ' VALUES (?, ?)',
            (bot_id, tag)
        )
        db.commit()
    return render_template('website/update.html', webhook = webhook)

@bp.route('/<string:tag>/delete', methods=('POST',))
@login_required
def delete(tag):
    get_webhook(tag)
    db = get_db()
    db.execute('DELETE FROM webhook WHERE tag = ?', (tag,))
    db.commit()
    return redirect(url_for('website.index'))