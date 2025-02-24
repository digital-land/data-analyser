import os
import tempfile

from flask import Blueprint, current_app, flash, redirect, render_template, url_for
from planning_data_analysis.extract import extract_table
from werkzeug.utils import secure_filename

from application.main.forms import ExtractTablesForm
from application.utils import allowed_file

main = Blueprint("main", __name__, template_folder="templates")


@main.route("/")
def index():
    return render_template("index.html")


@main.route("/extract-tables", methods=["GET", "POST"])
def extract_tables():
    form = ExtractTablesForm()
    if form.validate_on_submit():
        try:
            if form.file_or_url.data == "url":
                extracted_tables = extract_table(form.url.data, from_web=True)
            elif form.file_or_url.data == "file":
                if allowed_file(
                    form.file.data.filename, current_app.config["ALLOWED_EXTENSIONS"]
                ):
                    filename = secure_filename(form.file.data.filename)
                    temp_dir = tempfile.mkdtemp()
                    file_path = os.path.join(temp_dir, filename)
                    form.file.data.save(file_path)
                    extracted_tables = extract_table(file_path, from_file=True)
            return redirect(url_for("main.display_tables", tables=extracted_tables))

        except Exception as e:
            flash(f"Error: {e}", "error")
            return redirect(url_for("main.extract_tables"))

    return render_template("extract-tables.html", form=form)


@main.route("/display-tables")
def display_tables():
    return "OK", 200


@main.route("/cookies")
def cookies():
    return render_template("cookies.html")
