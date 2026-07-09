import os
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models.document import Document
from app.models.document_file import DocumentFile

app = create_app()

def migrate_data():
    with app.app_context():
        print('Starting data migration...')
        documents = Document.query.all()
        count = 0
        
        for doc in documents:
            # Check if this document already has a file mapped
            existing_file = DocumentFile.query.filter_by(document_id=doc.id).first()
            if existing_file:
                continue
                
            # If the document has a legacy file
            if doc.cloudinary_url:
                new_file = DocumentFile(
                    document_id=doc.id,
                    name=doc.original_filename or 'Document',
                    cloudinary_public_id=doc.cloudinary_public_id,
                    cloudinary_url=doc.cloudinary_url,
                    original_filename=doc.original_filename or 'Document',
                    file_size=doc.file_size or 0,
                    file_hash=doc.file_hash,
                    created_at=doc.created_at
                )
                db.session.add(new_file)
                count += 1
                
        db.session.commit()
        print(f'Migrated {count} document files successfully.')

if __name__ == '__main__':
    migrate_data()
