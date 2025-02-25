# -*- coding: utf-8 -*-
"""Extensions module. Each extension is initialized in the app factory located
in factory.py
"""
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_talisman import Talisman

db = SQLAlchemy()
migrate = Migrate(db=db)
talisman = Talisman()
