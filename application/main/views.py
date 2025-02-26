import csv
import os
import tempfile
from io import BytesIO, StringIO

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    send_file,
    url_for,
)
from planning_data_analysis.extract import extract_table
from werkzeug.utils import secure_filename

from application.extensions import db
from application.main.forms import ExtractTablesForm
from application.models import Extract, ExtractItem
from application.utils import allowed_file

main = Blueprint("main", __name__, template_folder="templates")


@main.route("/")
def index():
    return render_template("index.html")


@main.route("/extract-tables", methods=["GET", "POST"])
def extract_tables():
    form = ExtractTablesForm()
    if form.validate_on_submit():
        index = form.index.data if form.index.data else None
        keywords = form.keywords.data if form.keywords.data else None
        try:
            if form.file_or_url.data == "url":
                extracted_tables = extract_table(
                    form.url.data, from_web=True, table_index=index, key_words=keywords
                )
            elif form.file_or_url.data == "file":
                if allowed_file(
                    form.file.data.filename, current_app.config["ALLOWED_EXTENSIONS"]
                ):
                    filename = secure_filename(form.file.data.filename)
                    temp_dir = tempfile.mkdtemp()
                    file_path = os.path.join(temp_dir, filename)
                    form.file.data.save(file_path)
                    extracted_tables = extract_table(
                        file_path, from_file=True, table_index=index, key_words=keywords
                    )
            if extracted_tables:
                extract = Extract(
                    source=(
                        form.url.data
                        if form.file_or_url.data == "url"
                        else form.file.data.filename
                    )
                )
                for index, table in enumerate(extracted_tables):
                    data = table.to_csv(index=False, quoting=csv.QUOTE_MINIMAL)
                    extract.items.append(ExtractItem(data=data, index=index + 1))
                db.session.add(extract)
                db.session.commit()
                return redirect(url_for("main.extract_results", extract_id=extract.id))
            else:
                flash("No tables found in the uploaded file", "error")
                return redirect(url_for("main.extract_tables"))

        except Exception as e:
            flash(f"Error: {e}", "error")
            return redirect(url_for("main.extract_tables"))

    return render_template("extract-tables.html", form=form)


@main.route("/extract-result/<uuid:extract_id>")
def extract_results(extract_id):
    extract = Extract.query.get_or_404(extract_id)
    tables = []
    for item in extract.items:
        reader = csv.DictReader(StringIO(item.data))
        headers = reader.fieldnames
        rows = [row for row in reader]
        tables.append(
            {"index": item.index, "id": item.id, "headers": headers, "rows": rows}
        )
    return render_template("extract-results.html", extract=extract, tables=tables)


@main.route("/extract-result/<uuid:extract_id>/table/<uuid:table_id>")
def download_table(extract_id, table_id):
    item = ExtractItem.query.filter(
        ExtractItem.extract_id == extract_id, ExtractItem.id == table_id
    ).first_or_404()
    if item:
        binary_data = BytesIO(item.data.encode("utf-8"))
        return send_file(
            binary_data, download_name=f"table_{item.index}.csv", as_attachment=True
        )
    return "Table not found", 404


@main.route("/extract-index")
def extract_index():
    extracts = Extract.query.order_by(Extract.created_at.desc()).all()
    return render_template("extract-index.html", extracts=extracts)


@main.route("/cookies")
def cookies():
    return render_template("cookies.html")
