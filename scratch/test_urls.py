from app import create_app
from app.models.document import Document

app = create_app()
with app.app_context():
    for d in Document.query.all():
        print(f'{d.id}: {d.cloudinary_url} -> {d.cloudinary_url.replace("/upload/", "/upload/fl_attachment/")}')
