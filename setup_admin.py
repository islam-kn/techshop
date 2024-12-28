from app import app, db, User
from werkzeug.security import generate_password_hash

def setup_admin():
    with app.app_context():
        # Drop all tables and recreate them
        db.drop_all()
        db.create_all()
        
        # Check if admin user already exists
        admin = User.query.filter_by(email='admin@techshop.com').first()
        
        if not admin:
            # Create admin user
            admin = User(
                email='admin@techshop.com',
                password=generate_password_hash('admin123'),
                name='Admin',
                is_admin=True
            )
            db.session.add(admin)
            try:
                db.session.commit()
                print("Admin user created successfully!")
                print("Email: admin@techshop.com")
                print("Password: admin123")
            except Exception as e:
                db.session.rollback()
                print(f"Error creating admin user: {e}")
        else:
            print("Admin user already exists!")

if __name__ == "__main__":
    setup_admin()
