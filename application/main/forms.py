from flask_wtf import FlaskForm
from wtforms import (
    FileField,
    IntegerField,
    RadioField,
    StringField,
    URLField,
    ValidationError,
)
from wtforms.validators import DataRequired, Optional


class ExtractTablesForm(FlaskForm):
    url = URLField("URL", validators=[Optional()])
    file = FileField("File Name", validators=[Optional()])
    file_or_url = RadioField(
        "File or URL",
        choices=[("file", "File"), ("url", "URL")],
        validators=[DataRequired()],
    )
    index = IntegerField("Index", validators=[Optional()])
    keywords = StringField("Keywords", validators=[Optional()])

    def validate(self, extra_validators=None):
        if not super().validate(extra_validators=extra_validators):
            return False

        if bool(self.url.data) == bool(self.file.data):
            # If both are empty or both are filled, raise error
            raise ValidationError(
                "Please provide either a URL or a file name, but not both"
            )

        return True


class ClusterAnalysisForm(FlaskForm):
    file = FileField("CSV File", validators=[DataRequired()])


class PlanDataCollectionForm(FlaskForm):
    input_file = FileField("Input CSV", validators=[DataRequired()])
