from flask_wtf import FlaskForm
from wtforms import FileField, RadioField, URLField, ValidationError
from wtforms.validators import DataRequired, Optional


class ExtractTablesForm(FlaskForm):
    url = URLField("URL", validators=[Optional()])
    file_name = FileField("File Name", validators=[Optional()])
    file_or_url = RadioField(
        "File or URL",
        choices=[("file", "File"), ("url", "URL")],
        validators=[DataRequired()],
    )

    def validate(self):
        if not super().validate():
            return False

        if bool(self.url.data) == bool(self.file_name.data):
            # If both are empty or both are filled, raise error
            raise ValidationError(
                "Please provide either a URL or a file name, but not both"
            )

        return True
