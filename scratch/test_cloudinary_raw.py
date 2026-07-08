import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

load_dotenv()

import cloudinary
import cloudinary.api
import cloudinary.utils

cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET')
)

try:
    public_id = 'ca_manage_docs/awqeduf9prfn76seybml.pdf'
    # Check details of the raw file
    result = cloudinary.api.resource(public_id, resource_type='raw')
    print("Resource exists:", result['secure_url'])
except Exception as e:
    print("Error:", e)
