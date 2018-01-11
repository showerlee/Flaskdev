from flask import flash, redirect, url_for, session
from functools import wraps


# Check if user logged in
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, Please login.', 'danger')
            return redirect(url_for('.login'))
    return wrap


# Check user status
def is_active(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if session['user_status'] == 1:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, Please check if your account is disabled.', 'danger')
            return redirect(url_for('.login'))
    return wrap


# Check if user has admin authority
def is_admin(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if session['user_role'] == 1:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, Please check if you have valid permission.', 'danger')
            return redirect(url_for('.index'))
    return wrap
