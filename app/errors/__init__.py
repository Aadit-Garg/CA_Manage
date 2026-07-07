"""CA Manage — Error Handlers Blueprint"""
from flask import Blueprint

errors_bp = Blueprint('errors', __name__)

from . import handlers  # noqa: E402, F401

