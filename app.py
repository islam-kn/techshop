from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from werkzeug.utils import secure_filename
import os
from datetime import datetime
import stripe
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY')
app.config['STRIPE_PUBLIC_KEY'] = os.getenv('STRIPE_PUBLIC_KEY')
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///shop.db'
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

UPLOAD_FOLDER = 'static/images/products'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Create upload folder if it doesn't exist
os.makedirs(os.path.join(app.root_path, UPLOAD_FOLDER), exist_ok=True)

# Models
class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    image_url = db.Column(db.String(200))
    parent_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    products = db.relationship('Product', backref='category', lazy=True)
    subcategories = db.relationship('Category', backref=db.backref('parent', remote_side=[id]))

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    sale_price = db.Column(db.Float)
    stock = db.Column(db.Integer, default=0)
    image_url = db.Column(db.String(200))
    additional_images = db.Column(db.JSON)
    specifications = db.Column(db.JSON)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    featured = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    product = db.relationship('Product')

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    cart_items = db.relationship('CartItem', backref='user', lazy=True)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    total = db.Column(db.Float, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)
    discount = db.Column(db.Float, default=0)
    coupon_id = db.Column(db.Integer, db.ForeignKey('coupon.id'))
    shipping_address = db.Column(db.Text, nullable=False)
    phone = db.Column(db.String(20))
    status = db.Column(db.String(20), default='pending')
    payment_intent_id = db.Column(db.String(100))
    payment_status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    items = db.relationship('OrderItem', backref='order', lazy=True)
    coupon = db.relationship('Coupon')

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    product = db.relationship('Product')

class Promotion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    discount_percent = db.Column(db.Float)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    image_url = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Coupon(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    discount_percent = db.Column(db.Float)
    valid_until = db.Column(db.DateTime)
    max_uses = db.Column(db.Integer)
    current_uses = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Admin decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('You need to be an admin to access this page.')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def home():
    categories = Category.query.filter_by(parent_id=None).all()
    featured_products = Product.query.filter_by(featured=True).all()
    latest_products = Product.query.order_by(Product.created_at.desc()).limit(8).all()
    return render_template('index.html', categories=categories, products=featured_products + latest_products)

@app.route('/category/<slug>')
def category(slug):
    category = Category.query.filter_by(slug=slug).first_or_404()
    products = Product.query.filter_by(category_id=category.id).all()
    return render_template('category.html', category=category, products=products)

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    related_products = Product.query.filter_by(category_id=product.category_id).filter(Product.id != product.id).limit(4).all()
    return render_template('product_detail.html', product=product, related_products=related_products)

@app.route('/cart')
@login_required
def cart():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    total = sum(item.product.price * item.quantity for item in cart_items)
    return render_template('cart.html', cart_items=cart_items, total=total)

@app.route('/add-to-cart/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    quantity = int(request.form.get('quantity', 1))
    
    cart_item = CartItem.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    
    if cart_item:
        cart_item.quantity += quantity
    else:
        cart_item = CartItem(user_id=current_user.id, product_id=product_id, quantity=quantity)
        db.session.add(cart_item)
    
    db.session.commit()
    flash('Product added to cart successfully!')
    return redirect(url_for('cart'))

@app.route('/update-cart/<int:item_id>', methods=['POST'])
@login_required
def update_cart(item_id):
    cart_item = CartItem.query.get_or_404(item_id)
    if cart_item.user_id != current_user.id:
        abort(403)
    
    quantity = int(request.form.get('quantity'))
    if quantity > 0:
        cart_item.quantity = quantity
        db.session.commit()
    else:
        db.session.delete(cart_item)
        db.session.commit()
    
    return redirect(url_for('cart'))

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        flash('Your cart is empty')
        return redirect(url_for('cart'))

    # Calculate subtotal
    subtotal = sum(item.quantity * item.product.price for item in cart_items)
    
    # Calculate discount if coupon is applied
    discount = 0
    if 'coupon_id' in session:
        coupon = Coupon.query.get(session['coupon_id'])
        if coupon:
            discount = subtotal * (coupon.discount_percent / 100)
    
    # Calculate total
    total = subtotal - discount

    return render_template('checkout.html',
                         cart_items=cart_items,
                         subtotal=subtotal,
                         discount=discount,
                         total=total,
                         stripe_public_key=app.config['STRIPE_PUBLIC_KEY'])

@app.route('/orders')
@login_required
def view_orders():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template('orders.html', orders=orders)

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        current_user.name = request.form.get('name')
        current_user.phone = request.form.get('phone')
        current_user.address = request.form.get('address')
        
        if request.form.get('password'):
            current_user.password = generate_password_hash(request.form.get('password'))
        
        db.session.commit()
        flash('Profile updated successfully!')
        return redirect(url_for('profile'))
    
    return render_template('profile.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('home'))
        flash('Invalid email or password')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name')
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists')
            return redirect(url_for('register'))
        
        hashed_password = generate_password_hash(password)
        new_user = User(email=email, password=hashed_password, name=name)
        db.session.add(new_user)
        db.session.commit()
        
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/admin')
@admin_required
def admin_dashboard():
    products = Product.query.all()
    return render_template('admin/dashboard.html', products=products)

@app.route('/admin/add-product', methods=['GET', 'POST'])
@admin_required
def add_product():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        price = float(request.form.get('price'))
        category = request.form.get('category')
        
        # Handle image upload
        image = request.files.get('image')
        image_url = None
        
        if image:
            filename = secure_filename(image.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image.save(os.path.join(app.root_path, image_path))
            image_url = f'/static/images/products/{filename}'
        
        new_product = Product(
            name=name,
            description=description,
            price=price,
            category_id=category,
            image_url=image_url
        )
        
        db.session.add(new_product)
        db.session.commit()
        
        flash('Product added successfully!')
        return redirect(url_for('admin_dashboard'))
    
    return render_template('admin/add_product.html')

@app.route('/admin/edit-product/<int:product_id>', methods=['GET', 'POST'])
@admin_required
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    
    if request.method == 'POST':
        product.name = request.form.get('name')
        product.description = request.form.get('description')
        product.price = float(request.form.get('price'))
        product.category_id = request.form.get('category')
        
        image = request.files.get('image')
        if image:
            filename = secure_filename(image.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image.save(os.path.join(app.root_path, image_path))
            product.image_url = f'/static/images/products/{filename}'
        
        db.session.commit()
        flash('Product updated successfully!')
        return redirect(url_for('admin_dashboard'))
    
    return render_template('admin/edit_product.html', product=product)

@app.route('/admin/delete-product/<int:product_id>')
@admin_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash('Product deleted successfully!')
    return redirect(url_for('admin_dashboard'))

@app.route('/promotions')
def promotions():
    active_promotions = Promotion.query.filter(
        Promotion.start_date <= datetime.utcnow(),
        Promotion.end_date >= datetime.utcnow()
    ).all()
    return render_template('promotions.html', promotions=active_promotions)

@app.route('/apply-coupon', methods=['POST'])
@login_required
def apply_coupon():
    code = request.form.get('coupon_code')
    coupon = Coupon.query.filter_by(code=code).first()
    
    if not coupon:
        flash('Invalid coupon code')
        return redirect(url_for('cart'))
        
    if coupon.valid_until and coupon.valid_until < datetime.utcnow():
        flash('Coupon has expired')
        return redirect(url_for('cart'))
        
    if coupon.max_uses and coupon.current_uses >= coupon.max_uses:
        flash('Coupon has reached maximum uses')
        return redirect(url_for('cart'))
    
    session['coupon_id'] = coupon.id
    flash('Coupon applied successfully!')
    return redirect(url_for('cart'))

@app.route('/create-payment-intent', methods=['POST'])
@login_required
def create_payment_intent():
    try:
        data = request.get_json()
        
        # Calculate the order total
        cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
        total = sum(item.quantity * item.product.price for item in cart_items)
        
        # Apply coupon if exists
        if 'coupon_id' in session:
            coupon = Coupon.query.get(session['coupon_id'])
            if coupon:
                total = total * (1 - coupon.discount_percent / 100)
        
        # Create a PaymentIntent with the order amount and currency
        intent = stripe.PaymentIntent.create(
            amount=int(total * 100),  # Convert to cents
            currency='usd',
            automatic_payment_methods={
                'enabled': True,
            },
            metadata={
                'user_id': current_user.id
            }
        )
        
        return jsonify({
            'clientSecret': intent.client_secret
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 403

@app.route('/payment-success')
@login_required
def payment_success():
    payment_intent_id = request.args.get('payment_intent')
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    
    if not cart_items:
        return redirect(url_for('cart'))
    
    subtotal = sum(item.product.price * item.quantity for item in cart_items)
    total = subtotal
    discount = 0
    coupon_id = None
    
    if 'coupon_id' in session:
        coupon = Coupon.query.get(session['coupon_id'])
        if coupon:
            discount = subtotal * (coupon.discount_percent / 100)
            total = subtotal - discount
            coupon_id = coupon.id
            coupon.current_uses += 1
            session.pop('coupon_id')
    
    order = Order(
        user_id=current_user.id,
        subtotal=subtotal,
        discount=discount,
        total=total,
        coupon_id=coupon_id,
        shipping_address=request.form.get('address'),
        phone=request.form.get('phone'),
        status='confirmed',
        payment_intent_id=payment_intent_id,
        payment_status='paid'
    )
    db.session.add(order)
    
    for item in cart_items:
        order_item = OrderItem(
            order_id=order.id,
            product_id=item.product_id,
            quantity=item.quantity,
            price=item.product.price
        )
        db.session.add(order_item)
        db.session.delete(item)
    
    db.session.commit()
    flash('Order placed successfully!')
    return redirect(url_for('order_confirmation', order_id=order.id))

@app.route('/order-confirmation/<int:order_id>')
@login_required
def order_confirmation(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        abort(403)
    return render_template('order_confirmation.html', order=order)

@app.route('/admin/promotions')
@login_required
@admin_required
def admin_promotions():
    promotions = Promotion.query.all()
    return render_template('admin/promotions.html', promotions=promotions)

@app.route('/admin/promotions/add', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_add_promotion():
    if request.method == 'POST':
        promotion = Promotion(
            name=request.form['name'],
            description=request.form['description'],
            discount_percent=float(request.form['discount_percent']),
            start_date=datetime.strptime(request.form['start_date'], '%Y-%m-%d'),
            end_date=datetime.strptime(request.form['end_date'], '%Y-%m-%d'),
            image_url=request.form['image_url']
        )
        db.session.add(promotion)
        db.session.commit()
        flash('Promotion added successfully!')
        return redirect(url_for('admin_promotions'))
    return render_template('admin/add_promotion.html')

@app.route('/admin/promotions/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_edit_promotion(id):
    promotion = Promotion.query.get_or_404(id)
    if request.method == 'POST':
        promotion.name = request.form['name']
        promotion.description = request.form['description']
        promotion.discount_percent = float(request.form['discount_percent'])
        promotion.start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d')
        promotion.end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d')
        promotion.image_url = request.form['image_url']
        db.session.commit()
        flash('Promotion updated successfully!')
        return redirect(url_for('admin_promotions'))
    return render_template('admin/edit_promotion.html', promotion=promotion)

@app.route('/admin/promotions/delete/<int:id>')
@login_required
@admin_required
def admin_delete_promotion(id):
    promotion = Promotion.query.get_or_404(id)
    db.session.delete(promotion)
    db.session.commit()
    flash('Promotion deleted successfully!')
    return redirect(url_for('admin_promotions'))

@app.route('/admin/coupons')
@login_required
@admin_required
def admin_coupons():
    coupons = Coupon.query.all()
    return render_template('admin/coupons.html', coupons=coupons)

@app.route('/admin/coupons/add', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_add_coupon():
    if request.method == 'POST':
        coupon = Coupon(
            code=request.form['code'],
            discount_percent=float(request.form['discount_percent']),
            valid_until=datetime.strptime(request.form['valid_until'], '%Y-%m-%d'),
            max_uses=int(request.form['max_uses'])
        )
        db.session.add(coupon)
        db.session.commit()
        flash('Coupon added successfully!')
        return redirect(url_for('admin_coupons'))
    return render_template('admin/add_coupon.html')

@app.context_processor
def inject_categories():
    categories = Category.query.filter_by(parent_id=None).all()
    return dict(categories=categories)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
