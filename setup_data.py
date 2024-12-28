from app import app, db, Category, Product
from slugify import slugify

def setup_sample_data():
    with app.app_context():
        # Create main categories
        categories = [
            {
                'name': 'Laptops & Computers',
                'subcategories': ['Gaming Laptops', 'Business Laptops', 'Desktop PCs', 'Monitors']
            },
            {
                'name': 'Smartphones & Tablets',
                'subcategories': ['iPhones', 'Android Phones', 'iPads', 'Android Tablets']
            },
            {
                'name': 'Gaming & Entertainment',
                'subcategories': ['Gaming Consoles', 'Video Games', 'Gaming Accessories']
            },
            {
                'name': 'Accessories',
                'subcategories': ['Phone Cases', 'Chargers', 'Headphones', 'Speakers']
            }
        ]

        # Create categories
        for cat_data in categories:
            main_cat = Category(
                name=cat_data['name'],
                slug=slugify(cat_data['name']),
                image_url=f'/static/images/categories/{slugify(cat_data["name"])}.jpg'
            )
            db.session.add(main_cat)
            db.session.flush()  # To get the ID

            # Create subcategories
            for sub_name in cat_data['subcategories']:
                sub_cat = Category(
                    name=sub_name,
                    slug=slugify(sub_name),
                    parent_id=main_cat.id,
                    image_url=f'/static/images/categories/{slugify(sub_name)}.jpg'
                )
                db.session.add(sub_cat)

        # Sample products
        products = [
            {
                'name': 'MacBook Pro 16"',
                'description': 'Latest MacBook Pro with M2 chip, 16GB RAM, 512GB SSD',
                'price': 2499.99,
                'category': 'Business Laptops',
                'featured': True,
                'specifications': {
                    'processor': 'Apple M2 Pro',
                    'ram': '16GB',
                    'storage': '512GB SSD',
                    'display': '16-inch Retina',
                    'battery': 'Up to 22 hours'
                }
            },
            {
                'name': 'iPhone 15 Pro',
                'description': 'Latest iPhone with A17 Pro chip, 256GB storage',
                'price': 1199.99,
                'sale_price': 1099.99,
                'category': 'iPhones',
                'featured': True,
                'specifications': {
                    'screen': '6.1-inch OLED',
                    'processor': 'A17 Pro',
                    'storage': '256GB',
                    'camera': '48MP + 12MP + 12MP'
                }
            },
            {
                'name': 'PlayStation 5',
                'description': 'Next-gen gaming console with ultra-high-speed SSD',
                'price': 499.99,
                'category': 'Gaming Consoles',
                'featured': True,
                'specifications': {
                    'storage': '825GB SSD',
                    'resolution': '4K',
                    'fps': 'Up to 120fps',
                    'hdr': 'Yes'
                }
            }
        ]

        # Add products
        for product_data in products:
            category = Category.query.filter_by(name=product_data['category']).first()
            if category:
                product = Product(
                    name=product_data['name'],
                    slug=slugify(product_data['name']),
                    description=product_data['description'],
                    price=product_data['price'],
                    sale_price=product_data.get('sale_price'),
                    category_id=category.id,
                    featured=product_data['featured'],
                    specifications=product_data['specifications'],
                    image_url=f'/static/images/products/{slugify(product_data["name"])}.jpg',
                    stock=100
                )
                db.session.add(product)

        try:
            db.session.commit()
            print("Sample data created successfully!")
        except Exception as e:
            db.session.rollback()
            print(f"Error creating sample data: {e}")

if __name__ == "__main__":
    setup_sample_data()
