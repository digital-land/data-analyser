from dotenv import load_dotenv
from flask import Flask

from application.models import *  # noqa

load_dotenv()


def create_app(config_filename):
    app = Flask(__name__)
    app.config.from_object(config_filename)
    register_blueprints(app)
    register_context_processors(app)
    register_templates(app)
    register_filters(app)
    register_extensions(app)
    register_commands(app)
    return app


def register_blueprints(app):
    from application.main.views import main

    app.register_blueprint(main)


def register_filters(app):
    from application.filters import short_datetime

    app.add_template_filter(short_datetime, "short_datetime")


def register_context_processors(app):

    def base_context_processor():
        return {"assetPath": "/static"}

    app.context_processor(base_context_processor)

    def global_variables_context_processor():
        return {
            "site_settings": {
                "name": "Planning Data Analysis",
                "team_name": "Digital Land",
            },
        }

    app.context_processor(global_variables_context_processor)


def register_templates(app):
    from jinja2 import ChoiceLoader, PackageLoader, PrefixLoader

    multi_loader = ChoiceLoader(
        [
            app.jinja_loader,
            PrefixLoader(
                {
                    "govuk_frontend_jinja": PackageLoader("govuk_frontend_jinja"),
                    "digital-land-frontend": PackageLoader("digital_land_frontend"),
                }
            ),
        ]
    )
    app.jinja_loader = multi_loader


def register_commands(app):
    from application.commands import cli

    app.cli.add_command(cli)


def register_extensions(app):
    from application.extensions import db, migrate

    db.init_app(app)
    migrate.init_app(app, db)
    # talisman.init_app(app)
