from app import app, db, User
from werkzeug.security import generate_password_hash

with app.app_context():
    admin = User(
        email='admin@techshop.com',
        password=generate_password_hash('admin123'),
        name='Admin',
        is_admin=True
    )
    db.session.add(admin)
    db.session.commit()