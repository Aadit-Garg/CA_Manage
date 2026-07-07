"""CA Manage — Admin Blueprint"""
from flask import Blueprint

admin_bp = Blueprint('admin', __name__, template_folder='../templates/admin')

from . import routes, attendance, audit, search  # noqa: E402, F401
