from flask import Blueprint, render_template
from planning_data_analysis.extract import extract_table

from application.main.forms import ExtractTablesForm

main = Blueprint("main", __name__, template_folder="templates")


@main.route("/")
def index():
    return render_template("index.html")


@main.route("/extract-tables")
def extract_tables():
    form = ExtractTablesForm()
    if form.validate_on_submit():
        extract_table()
    return render_template("extract-tables.html", form=form)


@main.route("/cookies")
def cookies():
    return render_template("cookies.html")
