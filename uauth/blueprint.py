from flask import Blueprint, render_template, request, redirect, flash
from . import auth

NAME = 'uauth'

blueprint = Blueprint(NAME, __name__, template_folder='templates', static_folder='static')

@blueprint.route('/login', methods=['GET', 'POST'])
def login():
    form = {"username": "", "password" : ""}
    form_errors = []
    if request.method == 'POST':
        if "login" in request.form:
            form["username"] = username = request.form["username"].strip()
            password = request.form["password"].strip()
            try:
                username = auth.log_in(username, password)
            except auth.AuthError as e:
                print(e)
                form_errors.append("Wrong username or password.")
            else:
                flash("You have been logged in as '%s'." % username, "success")
                return redirect("/")
                
    return render_template(NAME + '/login.html', form=form, form_errors=form_errors)
    
@blueprint.route('/logout', methods=['GET', 'POST'])
def logout():
    auth.log_out()
    flash("You have been logged out.", "success")
    return redirect("/")
