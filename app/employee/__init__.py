"""CA Manage — Employee Blueprint"""
from flask import Blueprint

employee_bp = Blueprint('employee', __name__, template_folder='../templates/employee')

from . import routes  # noqa: E402, F401
from . import attendance  # noqa: E402, F401

