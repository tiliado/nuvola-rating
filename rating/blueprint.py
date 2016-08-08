from flask import Blueprint, render_template, request, url_for, redirect, flash, jsonify, send_file
from rating.models import WebAppRating
import easybadges
from io import BytesIO
from collections import namedtuple
import re
import uauth

NAME = 'rating'

APP_ID_REGEX = re.compile("^[a-z0-9]+(?:_[a-z0-9]+)*$");
APP_VERSION_REGEX = re.compile("^[1-9][0-9]*\.[0-9]+$");

RATING_LABELS = {
    "X": "Unknown",
    "A": "Excellent",
    "B": "Good",
    "C": "Outdated",
    "D": "Broken",
    "E": "Garbage",
    "F": "Discontinued",
}

RATING_COLORS = {
    "A": (36, 176, 0),
    "B": (36, 176, 0),
    "C": (255, 110, 0),
    "D": (208, 0, 0),
    "E": (208, 0, 0),
    "F": (208, 0, 0),
    "X": (41, 41, 41),
    }

RATING_OPTIONS = tuple(sorted(RATING_LABELS.keys()))

AppIndexEntry = namedtuple("AppIndexEntry", "id name version rating reason link")

def get_latest_rating(rating_map):
    versions = get_sorted_versions(rating_map)
    if not versions:
        return None, None
    version = versions[0]
    return version, rating_map[version]

def get_sorted_versions(rating_map):
    versions = list(rating_map.keys())
    if not versions:
        return None
    
    def key_func(x):
        x = x.split(".")
        try:
            return [int(i) for i in x]
        except ValueError:
            return [-1]
        
    versions.sort(key=key_func, reverse=True)
    return versions


blueprint = Blueprint(NAME, __name__, template_folder='templates', static_folder='static')

@blueprint.route('/', methods=['GET', 'POST'])
def index():
    APP_ID = "app_id"
    APP_NAME = "app_name"
    editable = uauth.is_logged_in()
    form_errors = []
    edit_id = request.form.get("edit_id", request.args.get("edit_id"))
    web_app = WebAppRating.entities.get(app_id=edit_id) if edit_id else None
    form = {
        "app_id": "",
        "app_name": "",
    }
    if request.method == 'GET' and edit_id:
        form = {
            "app_id": edit_id,
            "app_name": web_app.app_name,
        }
    if editable and request.method == 'POST':
        if "app_add" in request.form or "app_edit" in request.form:
            form = request.form
            app_id = request.form[APP_ID].strip()
            app_name = request.form[APP_NAME].strip()
            
            if not app_id:
                form_errors.append("App id must not be empty.")
            elif not APP_ID_REGEX.match(app_id):
                form_errors.append("App id must contain only letters, digits and possibly an underscore as a separator of words.")
            elif edit_id != app_id and WebAppRating.entities.exists(app_id=app_id):
                form_errors.append("App id must be unique.")
            if not app_name:
                form_errors.append("App name must not be empty.")
            elif (not web_app or web_app.app_name != app_name) and WebAppRating.entities.exists(app_name=app_name):
                form_errors.append("App name must be unique.")
            if not form_errors:
                if web_app:
                    web_app.app_id = app_id
                    web_app.app_name = app_name
                    web_app.save()
                    flash("Web app instance %s (%s) has been updated." % (app_name, app_id), "success")
                else:
                    WebAppRating.entities.create(app_id=app_id, app_name=app_name, rating={})
                    flash("Web app instance %s (%s) has been created." % (app_name, app_id), "success")
                return redirect(url_for('.index'))
        elif "app_delete" in request.form:
            app_ids = request.form.getlist("app_id")
            if app_ids:
                for app_id in app_ids:
                    WebAppRating.entities.delete_by(app_id=app_id)
                flash("%d Web app instances have been deleted." % len(app_ids), "success")
            return redirect(url_for('.index'))

    web_apps = []
    for app in WebAppRating.entities.query(order_by="app_name").all():
        version, info = get_latest_rating(app.rating)
        if info:
            rating = info["rating"]
            reason = info.get("reason", "")
            link = info.get("link")
        else:
            version = "*"
            rating = "X"
            reason = ""
            link = None
        web_apps.append(AppIndexEntry(app.app_id, app.app_name, version, rating, reason, link))
            
    return render_template(NAME + '/index.html',
        web_apps=web_apps, editable=editable, labels=RATING_LABELS, form = form, form_errors=form_errors, edit_id=edit_id)

@blueprint.route('/index.json')
def index_json():
    web_apps = []
    for app in WebAppRating.entities.query(order_by="app_name").all():
        version, info = get_latest_rating(app.rating)
        if info:
            info["version"] = version
        else:
            info = {
                "version": "*",
                "rating": "X",
                "reason": None,
                "link": None,
            }
        info["id"] = app.app_id
        info["name"] = app.app_name
        web_apps.append(info)
    return jsonify(apps=web_apps, labels=RATING_LABELS)

@blueprint.route('/<app_id>/', methods=['GET', 'POST'])
def web_app(app_id):
    editable = uauth.is_logged_in()
    web_app = WebAppRating.entities.get(app_id=app_id)
    
    form_errors = []
    edit_version = request.form.get("edit_version", request.args.get("edit_version"))
    form = {
        "rating_version": "",
        "rating_rating": "",
        "rating_reason": "",
        "rating_link": ""
     }
    if request.method == 'GET' and edit_version:
        rating = web_app.rating[edit_version]
        form = {
            "rating_version": edit_version,
            "rating_rating": rating["rating"],
            "rating_reason": rating["reason"],
            "rating_link": rating["link"]
         }  
             
        
    if editable and request.method == 'POST':
        if "rating_add" in request.form or "rating_edit" in request.form:
            form = request.form
            version = request.form["rating_version"].strip()
            rating = request.form["rating_rating"].strip().upper()
            reason = request.form["rating_reason"].strip()
            link = request.form["rating_link"].strip()
            if not version:
                form_errors.append("Version must not be empty.")
            elif version != "*" and not APP_VERSION_REGEX.match(version):
                form_errors.append("Version number must be in the form of 'MAJOR.MINOR' or '*' as wildchar.")
            elif version in web_app.rating and version != edit_version:
                form_errors.append("This version has been already rated.")
            if not rating:
                form_errors.append("Rating must not be empty.")
            elif rating not in RATING_LABELS:
                form_errors.append("Rating must be one of %s." % (RATING_OPTIONS,))
            if link and not link.startswith(("http://", "https://")):
                form_errors.append("Link must start with 'https://' or 'http://'.")
            if not form_errors:
                if edit_version and edit_version != version:
                    del web_app.rating[edit_version]
                
                web_app.rating[version] = {
                "rating": rating,
                "reason": reason,
                "link": link
                }
                web_app.save()
                flash("Web app instance %s (%s) has been updated." % (web_app.app_name, web_app.app_id), "success")
                return redirect(url_for('.web_app', app_id=app_id))
        
        elif "rating_delete" in request.form:
            rating_versions = request.form.getlist("rating_version")
            if rating_versions:
                for version in rating_versions:
                    del web_app.rating[version]
                web_app.save()
                flash("Web app instance %s (%s) has been updated." % (web_app.app_name, web_app.app_id), "success")
                return redirect(url_for('.web_app', app_id=app_id))
            return redirect(url_for('.web_app', app_id=app_id))
    
    rating_map = web_app.rating
    versions = get_sorted_versions(rating_map)
    return render_template(NAME + '/web_app.html',
        web_app=web_app, editable=editable, versions=versions, rating_map=rating_map,
        labels=RATING_LABELS, options=RATING_OPTIONS, form=form, form_errors=form_errors, edit_version=edit_version)
        
@blueprint.route('/<app_id>.json')
def web_app_json(app_id):
    web_app = WebAppRating.entities.get(app_id=app_id)
    rating_map = web_app.rating
    versions = get_sorted_versions(rating_map)
    return jsonify(sorted=versions, versions=rating_map, labels=RATING_LABELS)

@blueprint.route('/<app_id>/<version>/')
def web_app_rating(app_id, version):
    return app_id + " " + version

@blueprint.route('/<app_id>/<version>.json')
def web_app_version_json(app_id, version):
    app = WebAppRating.entities.get(app_id=app_id)
    try:
        info = app.rating[version]
    except KeyError:
        version = "*"
        try:
            info = app.rating[version]
        except KeyError:
            info = {
                "rating": "X",
                "reason": None,
                "link": None,
            }
    info["id"] = app.app_id
    info["name"] = app.app_name
    info["version"] = version
    info["label"] = RATING_LABELS[info["rating"]]
    return jsonify(**info)

def send_pil_image(img, format, mimetype, **params):
    buffer = BytesIO()
    img.save(buffer, format, **params)
    buffer.seek(0)
    return send_file(buffer, mimetype=mimetype)
    
@blueprint.route('/<app_id>/<version>.png')
def web_app_version_png(app_id, version):
    app = WebAppRating.entities.get(app_id=app_id)
    info = None
    if version == "latest":
        version, info = get_latest_rating(app.rating)
        if not info:
            version = "*"
    if not info:
        try:
            info = app.rating[version]
        except KeyError:
            version = "*"
            try:
                info = app.rating[version]
            except KeyError:
                info = None
    
    rating = info["rating"] if info else "X"
    variants = ["(%s) %s" % entry for entry in RATING_LABELS.items()]
    label = RATING_LABELS[rating]
    color = RATING_COLORS[rating]
    img = easybadges.badge("Rating", "(%s) %s" % (rating, label), color=color, variants=variants)
    return send_pil_image(img, "PNG", "image/png", compress_level=9)
    
    
    
