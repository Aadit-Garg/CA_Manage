"""
Sumit n Garg & Associates — Error Handlers

Custom error pages for common HTTP errors.
Each renders a branded, mobile-friendly error page.
"""
from flask import render_template, request, current_app
from . import errors_bp


@errors_bp.app_errorhandler(400)
def bad_request(error):
    current_app.logger.warning(f'400 Bad Request: {request.url}')
    return render_template('errors/400.html'), 400


@errors_bp.app_errorhandler(403)
def forbidden(error):
    current_app.logger.warning(f'403 Forbidden: {request.url} by {request.remote_addr}')
    return render_template('errors/403.html'), 403


@errors_bp.app_errorhandler(404)
def not_found(error):
    return render_template('errors/404.html'), 404


@errors_bp.app_errorhandler(429)
def too_many_requests(error):
    current_app.logger.warning(f'429 Too Many Requests: {request.url} from {request.remote_addr}')
    return render_template('errors/429.html'), 429


@errors_bp.app_errorhandler(500)
def internal_error(error):
    current_app.logger.error(f'500 Internal Server Error: {request.url}', exc_info=True)
    return render_template('errors/500.html'), 500
