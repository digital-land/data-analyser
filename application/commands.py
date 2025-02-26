from flask.cli import AppGroup

cli = AppGroup("cli")


@cli.command("delete-extracts")
def delete_extracts():
    from datetime import datetime, timedelta

    from application.extensions import db
    from application.models import Extract

    five_days_ago = datetime.now() - timedelta(days=5)
    extracts_to_delete = Extract.query.filter(Extract.created_at < five_days_ago).all()
    for extract in extracts_to_delete:
        print(
            f"Deleting extract {extract.id} from {extract.source} created at {extract.created_at}"
        )
        db.session.delete(extract)
    db.session.commit()
