import flask
from werkzeug import security

_admins = {}


class AuthError(Exception):
    pass


def add_admin(username, password_hash):
    _admins[username] = password_hash


def log_in(username, password, session=None):
    if not session:
        session = flask.session
    session['user'] = None
    session['username'] = "Anonymous"
    
    try:
        password_hash = _admins[username.lower()]
    except KeyError:
        raise AuthError("User '%s' doesn't exist." % username)
    
    if not security.check_password_hash(password_hash, password):
        raise AuthError("Wrong password.")
    
    session['user'] = session['username'] = username
    return username


def log_out(session=None):
    if not session:
        session = flask.session
    session['user'] = None
    session['username'] = "Anonymous"


def is_logged_in(session=None):
    if not session:
        session = flask.session
    return 'user' in session and session['user']
