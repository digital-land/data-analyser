from flask import Blueprint, render_template

main = Blueprint("main", __name__, template_folder="templates")


@main.route("/")
def index():
    return render_template("index.html")


@main.route("/cookies")
def cookies():
    return render_template("cookies.html")
