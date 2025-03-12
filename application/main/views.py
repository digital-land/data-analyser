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
from planning_data_analysis.cil_process import process_and_save
from planning_data_analysis.cluster_analysis import analyze_clusters
from planning_data_analysis.collect_plan_data import collect_plan_data
from planning_data_analysis.extract import extract_table
from werkzeug.utils import secure_filename

from application.extensions import db
from application.main.forms import (
    CILProcessForm,
    ClusterAnalysisForm,
    ExtractTablesForm,
    PlanDataCollectionForm,
)
from application.models import (
    CILProcess,
    ClusterAnalysis,
    Extract,
    ExtractItem,
    PlanDataCollection,
)
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

            # Save results to database
            analysis = ClusterAnalysis(
                source_file=filename,
                grouped_reasons={},  # TODO: Extract from output
                visualization_path=os.path.join(output_dir, "TSNE_Clusters.png"),
                report_path=os.path.join(
                    output_dir, "Grouped_Invalid_Reason_Details.docx"
                ),
            )
            db.session.add(analysis)
            db.session.commit()

            return redirect(url_for("main.cluster_results", analysis_id=analysis.id))

        except Exception as e:
            flash(f"Error: {e}", "error")
            return redirect(url_for("main.analyze_clusters"))

    return render_template("analyze-clusters.html", form=form)


@main.route("/process-cil", methods=["GET", "POST"])
def process_cil_view():
    form = CILProcessForm()
    if form.validate_on_submit():
        try:
            # Create temp directory for processing
            temp_dir = tempfile.mkdtemp()

            # Save uploaded files
            cil_file = form.cil_file.data
            ref_file = form.reference_file.data

            cil_filename = secure_filename(cil_file.filename)
            ref_filename = secure_filename(ref_file.filename)

            cil_path = os.path.join(temp_dir, cil_filename)
            ref_path = os.path.join(temp_dir, ref_filename)

            cil_file.save(cil_path)
            ref_file.save(ref_path)

            # Create output directory
            output_dir = os.path.join(temp_dir, "output")
            os.makedirs(output_dir, exist_ok=True)

            # Process CIL data
            process_and_save(cil_path, ref_path, output_dir)

            # Save results to database
            process = CILProcess(
                source_file=cil_filename,
                reference_file=ref_filename,
                cil_output_path=os.path.join(output_dir, "cil_dataset.csv"),
                ifs_output_path=os.path.join(output_dir, "ifs_dataset.csv"),
            )
            db.session.add(process)
            db.session.commit()

            return redirect(url_for("main.cil_results", process_id=process.id))

        except Exception as e:
            flash(f"Error: {e}", "error")
            return redirect(url_for("main.process_cil"))

    return render_template("process-cil.html", form=form)


@main.route("/collect-plan-data", methods=["GET", "POST"])
def collect_plan_data_view():
    form = PlanDataCollectionForm()
    if form.validate_on_submit():
        try:
            # Create temp directory for processing
            temp_dir = tempfile.mkdtemp()

            # Save uploaded files
            input_file = form.input_file.data
            ref_file = form.reference_file.data

            input_filename = secure_filename(input_file.filename)
            ref_filename = secure_filename(ref_file.filename)

            input_path = os.path.join(temp_dir, input_filename)
            ref_path = os.path.join(temp_dir, ref_filename)

            input_file.save(input_path)
            ref_file.save(ref_path)

            # Create output directory
            output_dir = os.path.join(temp_dir, "output")
            os.makedirs(output_dir, exist_ok=True)

            # Process plan data
            output_path = os.path.join(output_dir, "plan_data.csv")
            failed_urls_path = os.path.join(output_dir, "failed_urls.csv")

            collect_plan_data(input_path, ref_path, output_path, failed_urls_path)

            # Save results to database
            collection = PlanDataCollection(
                source_file=input_filename,
                reference_file=ref_filename,
                output_path=output_path,
                failed_urls_path=(
                    failed_urls_path if os.path.exists(failed_urls_path) else None
                ),
            )
            db.session.add(collection)
            db.session.commit()

            return redirect(
                url_for("main.plan_data_results", collection_id=collection.id)
            )

        except Exception as e:
            flash(f"Error: {e}", "error")
            return redirect(url_for("main.collect_plan_data"))

    return render_template("collect-plan-data.html", form=form)


@main.route("/cluster-results/<uuid:analysis_id>")
def cluster_results(analysis_id):
    analysis = ClusterAnalysis.query.get_or_404(analysis_id)
    return render_template("cluster-results.html", analysis=analysis)


@main.route("/cil-results/<uuid:process_id>")
def cil_results(process_id):
    process = CILProcess.query.get_or_404(process_id)
    return render_template("cil-results.html", process=process)


@main.route("/plan-data-results/<uuid:collection_id>")
def plan_data_results(collection_id):
    collection = PlanDataCollection.query.get_or_404(collection_id)
    return render_template("plan-data-results.html", collection=collection)
