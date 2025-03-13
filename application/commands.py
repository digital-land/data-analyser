from datetime import datetime, timedelta

import click
from flask.cli import AppGroup, with_appcontext

from application.extensions import db
from application.models import ClusterAnalysis, Extract, PlanDataCollection

cli = AppGroup("cli")


@click.command("delete-old-results")
@click.option("--days", default=30, help="Delete data older than this many days")
@with_appcontext
def delete_old_results(days):
    """Delete results older than specified days."""
    cutoff_date = datetime.now() - timedelta(days=days)

    # Delete old extracts
    old_extracts = Extract.query.filter(Extract.created_at < cutoff_date).all()
    for extract in old_extracts:
        db.session.delete(extract)
    extracts_count = len(old_extracts)

    # Delete old cluster analyses
    old_analyses = ClusterAnalysis.query.filter(
        ClusterAnalysis.created_at < cutoff_date
    ).all()
    for analysis in old_analyses:
        db.session.delete(analysis)
    analyses_count = len(old_analyses)

    # Delete old plan data collections
    old_collections = PlanDataCollection.query.filter(
        PlanDataCollection.created_at < cutoff_date
    ).all()
    for collection in old_collections:
        db.session.delete(collection)
    collections_count = len(old_collections)

    db.session.commit()

    click.echo(f"Deleted {extracts_count} extracts")
    click.echo(f"Deleted {analyses_count} cluster analyses")
    click.echo(f"Deleted {collections_count} plan data collections")
    click.echo(
        f"Total items deleted: {extracts_count + analyses_count + collections_count}"
    )
