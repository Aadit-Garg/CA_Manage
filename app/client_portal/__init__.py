"""CA Manage — Client Portal Blueprint"""
from flask import Blueprint

client_bp = Blueprint('client_portal', __name__, template_folder='../templates/client')

from . import routes  # noqa: E402, F401

