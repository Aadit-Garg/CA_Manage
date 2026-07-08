from flask import jsonify, request, current_app
from flask_login import login_required, current_user
import cloudinary.utils
import time
from . import api_bp
from ..models.user import User

@api_bp.route('/cloudinary/signature', methods=['GET'])
@login_required
def generate_signature():
    """
    Generate a secure Cloudinary upload signature for client-side uploads.
    Only allows employees and admins to upload files.
    """
    if current_user.role not in [User.ROLE_ADMIN, User.ROLE_EMPLOYEE]:
        return jsonify({'error': 'Unauthorized'}), 403

    timestamp = int(time.time())
    
    # Parameters that must be signed. These must EXACTLY match the upload options 
    # used in the frontend Cloudinary Upload Widget.
    params_to_sign = {
        'timestamp': timestamp,
        'folder': 'ca_manage_docs',
        'source': 'uw'
    }

    # Generate the signature using the API secret
    api_secret = current_app.config.get('CLOUDINARY_API_SECRET')
    if not api_secret:
        return jsonify({'error': 'Cloudinary API secret not configured'}), 500

    signature = cloudinary.utils.api_sign_request(params_to_sign, api_secret)
    api_key = current_app.config.get('CLOUDINARY_API_KEY')
    cloud_name = current_app.config.get('CLOUDINARY_CLOUD_NAME')

    return jsonify({
        'signature': signature,
        'timestamp': timestamp,
        'api_key': api_key,
        'cloud_name': cloud_name,
        'folder': 'ca_manage_docs'
    })
