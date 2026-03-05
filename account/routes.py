from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

from extensions import db
from models import User
from . import account_bp


@account_bp.route("/email", methods=["GET", "POST"])
@login_required
def email():
    if request.method == "POST":
        new_email = (request.form.get("email") or "").strip().lower()
        password = (request.form.get("password") or "").strip()

        if not new_email or not password:
            flash("Completează emailul nou și parola.", "error")
            return render_template("account_email.html")

        if not current_user.check_password(password):
            flash("Parola este greșită.", "error")
            return render_template("account_email.html")

        # email unic
        if User.query.filter(User.email == new_email, User.id != current_user.id).first():
            flash("Emailul este deja folosit de alt cont.", "error")
            return render_template("account_email.html")

        current_user.email = new_email
        db.session.commit()

        flash("Emailul a fost actualizat.", "success")
        return redirect(url_for("menu.menu_home"))

    return render_template("account_email.html")


@account_bp.route("/password", methods=["GET", "POST"])
@login_required
def password():
    if request.method == "POST":
        cur = (request.form.get("current_password") or "").strip()
        new1 = (request.form.get("new_password") or "").strip()
        new2 = (request.form.get("new_password2") or "").strip()

        if not current_user.check_password(cur):
            flash("Parola curentă este greșită.", "error")
            return render_template("account_password.html")

        if len(new1) < 8:
            flash("Parola nouă trebuie să aibă minim 8 caractere.", "error")
            return render_template("account_password.html")

        if new1 != new2:
            flash("Parolele noi nu se potrivesc.", "error")
            return render_template("account_password.html")

        current_user.set_password(new1)
        db.session.commit()

        flash("Parola a fost schimbată.", "success")
        return redirect(url_for("menu.menu_home"))

    return render_template("account_password.html")
