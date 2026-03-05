from functools import wraps
from flask import redirect, url_for, flash, request
from flask_login import current_user


def agent_required(fn):
    """
    Requires user to be authenticated and have 'agent' role.
    Redirects clients to client landing page.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("Trebuie să te loghezi ca să continui.", "error")
            return redirect(url_for("auth.login", next=request.path))
        if current_user.is_client:
            flash("Această secțiune este disponibilă doar pentru agenți.", "error")
            return redirect(url_for("client.landing"))
        return fn(*args, **kwargs)
    return wrapper


def client_required(fn):
    """
    Requires user to be authenticated and have 'client' role.
    Redirects agents to home.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("Trebuie să te loghezi ca să continui.", "error")
            return redirect(url_for("client.login", next=request.path))
        if current_user.is_agent:
            flash("Această secțiune este disponibilă doar pentru clienți.", "error")
            return redirect(url_for("home"))
        return fn(*args, **kwargs)
    return wrapper


def access_required(fn):
    """
    - Dacă nu e logat -> login (cu next)
    - Dacă e logat dar nu are access (paid expirat / is_active False / nu mai are acțiuni gratuite) -> /menu
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("Trebuie să te loghezi ca să continui.", "error")
            return redirect(url_for("auth.login", next=request.path))

        if not current_user.has_access():
            flash("Acces expirat. Apasă «Contact tehnic» ca să activezi contul.", "error")
            return redirect(url_for("menu.menu_home"))

        return fn(*args, **kwargs)

    return wrapper
