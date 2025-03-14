import csv
import os
import tempfile
from io import BytesIO, StringIO
from pathlib import Path

import matplotlib
from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    send_file,
    url_for,
)
from planning_data_analysis.cluster_analysis import analyze_clusters
from planning_data_analysis.collect_plan_data import collect_plan_data
from planning_data_analysis.extract import extract_table
from werkzeug.utils import secure_filename

from application.extensions import db
from application.main.forms import (
    ClusterAnalysisForm,
    ExtractTablesForm,
    PlanDataCollectionForm,
)
from application.models import ClusterAnalysis, Extract, ExtractItem, PlanDataCollection
from application.utils import allowed_file

matplotlib.use("Agg")  # Use non-interactive backend


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
                messages = {
                    "file": "No tables found in the uploaded file",
                    "url": "No tables found in the webpage provided",
                }
                flash(messages[form.file_or_url.data], "error")
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


@main.route("/analyze-clusters", methods=["GET", "POST"])
def analyze_clusters_view():
    form = ClusterAnalysisForm()
    if form.validate_on_submit():
        try:
            # Create temp directory for processing
            temp_dir = tempfile.mkdtemp()

            # Save uploaded file
            input_file = form.file.data
            filename = secure_filename(input_file.filename)
            input_path = os.path.join(temp_dir, filename)
            input_file.save(input_path)

            # Create output directory
            output_dir = os.path.join(temp_dir, "output")
            os.makedirs(output_dir, exist_ok=True)

            # Run analysis
            analyze_clusters(input_path, output_dir)

            # Read the generated files
            visualization_path = os.path.join(output_dir, "TSNE_Clusters.png")
            report_path = os.path.join(
                output_dir, "Grouped_Invalid_Reason_Details.docx"
            )
            csv_path = os.path.join(output_dir, "Grouped_Invalid_Reason_Details.csv")

            with open(visualization_path, "rb") as f:
                visualization_data = f.read()

            with open(report_path, "rb") as f:
                report_data = f.read()

            # Read the CSV to get grouped reasons
            import pandas as pd

            grouped_df = pd.read_csv(csv_path)
            grouped_reasons = {
                col: grouped_df[col].dropna().tolist() for col in grouped_df.columns
            }

            # Save results to database
            analysis = ClusterAnalysis(
                source_file=filename,
                grouped_reasons=grouped_reasons,
                visualization_data=visualization_data,
                visualization_mime_type="image/png",
                report_data=report_data,
                report_mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
            db.session.add(analysis)
            db.session.commit()

            return redirect(url_for("main.cluster_results", analysis_id=analysis.id))

        except Exception as e:
            flash(f"Error: {e}", "error")
            return redirect(url_for("main.analyze_clusters"))

    return render_template("analyze-clusters.html", form=form)


@main.route("/collect-plan-documents", methods=["GET", "POST"])
def collect_plan_documents():
    form = PlanDataCollectionForm()
    if form.validate_on_submit():
        try:
            # Create temp directory for processing
            temp_dir = tempfile.mkdtemp()

            # Save uploaded file
            input_file = form.input_file.data
            input_filename = secure_filename(input_file.filename)
            input_path = os.path.join(temp_dir, input_filename)
            input_file.save(input_path)

            # Use local reference file
            app_path = Path(current_app.root_path)
            data_dir = app_path.parent / "data"
            ref_path = data_dir / "local-plan-document-type.csv"

            # Create output directory
            output_dir = os.path.join(temp_dir, "output")
            os.makedirs(output_dir, exist_ok=True)

            # Process plan data
            output_path = os.path.join(output_dir, "plan_documents.csv")
            failed_urls_path = os.path.join(output_dir, "failed_urls.csv")

            collect_plan_data(input_path, ref_path, output_path, failed_urls_path)

            # Read the output files
            with open(output_path, "r") as f:
                output_data = f.read()

            failed_urls_data = None
            if os.path.exists(failed_urls_path):
                with open(failed_urls_path, "r") as f:
                    failed_urls_data = f.read()

            # Save results to database
            collection = PlanDataCollection(
                source_file=input_filename,
                reference_file="local-plan-document-type.csv",
                data=output_data,
                failed_urls=failed_urls_data,
            )
            db.session.add(collection)
            db.session.commit()

            return redirect(
                url_for("main.plan_documents_results", collection_id=collection.id)
            )

        except Exception as e:
            flash(f"Error: {e}", "error")
            return redirect(url_for("main.collect_plan_documents"))

    return render_template("collect-plan-documents.html", form=form)


@main.route("/plan-documents-results/<uuid:collection_id>")
def plan_documents_results(collection_id):
    collection = PlanDataCollection.query.get_or_404(collection_id)

    # Parse the CSV data to display in the template
    reader = csv.DictReader(StringIO(collection.data))
    headers = reader.fieldnames
    rows = [row for row in reader]

    # Parse failed URLs if they exist
    failed_urls = None
    if collection.failed_urls:
        failed_reader = csv.DictReader(StringIO(collection.failed_urls))
        failed_urls = [row for row in failed_reader]

    return render_template(
        "plan-documents-results.html",
        collection=collection,
        headers=headers,
        rows=rows,
        failed_urls=failed_urls,
    )


@main.route("/plan-documents-results/<uuid:collection_id>/download")
def download_plan_documents(collection_id):
    collection = PlanDataCollection.query.get_or_404(collection_id)
    return send_file(
        BytesIO(collection.data.encode("utf-8")),
        mimetype="text/csv",
        download_name=f"local-plan-documents-{collection_id}.csv",
        as_attachment=True,
    )


@main.route("/plan-documents-results/<uuid:collection_id>/failed-urls")
def download_failed_urls(collection_id):
    collection = PlanDataCollection.query.get_or_404(collection_id)
    if not collection.failed_urls:
        flash("No failed URLs file available", "error")
        return redirect(
            url_for("main.plan_documents_results", collection_id=collection_id)
        )

    return send_file(
        BytesIO(collection.failed_urls.encode("utf-8")),
        mimetype="text/csv",
        download_name=f"failed_urls_{collection_id}.csv",
        as_attachment=True,
    )


@main.route("/plan-documents-index")
def plan_documents_index():
    collections = PlanDataCollection.query.order_by(
        PlanDataCollection.created_at.desc()
    ).all()
    return render_template("plan-documents-index.html", collections=collections)


@main.route("/cluster-index")
def cluster_index():
    analyses = ClusterAnalysis.query.order_by(ClusterAnalysis.created_at.desc()).all()
    return render_template("cluster-index.html", analyses=analyses)


@main.route("/cluster-results/<uuid:analysis_id>")
def cluster_results(analysis_id):
    analysis = ClusterAnalysis.query.get_or_404(analysis_id)
    return render_template("cluster-results.html", analysis=analysis)


@main.route("/cluster-results/<uuid:analysis_id>/visualization")
def cluster_visualization(analysis_id):
    analysis = ClusterAnalysis.query.get_or_404(analysis_id)
    return send_file(
        BytesIO(analysis.visualization_data),
        mimetype=analysis.visualization_mime_type,
        as_attachment=False,
    )


@main.route("/cluster-results/<uuid:analysis_id>/report")
def cluster_report(analysis_id):
    analysis = ClusterAnalysis.query.get_or_404(analysis_id)
    return send_file(
        BytesIO(analysis.report_data),
        mimetype=analysis.report_mime_type,
        download_name=f"cluster_analysis_report_{analysis_id}.docx",
        as_attachment=True,
    )
