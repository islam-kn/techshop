# TechShop E-Commerce Website

A modern e-commerce website built with Flask for selling tech products online.

## Features

- User authentication (login/register)
- Product catalog with detailed product pages
- Responsive design
- Shopping cart functionality
- Modern UI with animations

## Installation

1. Clone the repository
2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the application:
```bash
python app.py
```

5. Visit `http://localhost:5000` in your web browser

## Technology Stack

- Backend: Python/Flask
- Database: SQLite with SQLAlchemy
- Frontend: HTML5, CSS3, JavaScript
- CSS Framework: Bootstrap 5
- Authentication: Flask-Login

## Project Structure

```
techshop website/
├── app.py              # Main application file
├── requirements.txt    # Python dependencies
├── static/            # Static files (CSS, JS, images)
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── main.js
└── templates/         # HTML templates
    ├── base.html
    ├── index.html
    ├── login.html
    ├── register.html
    └── product_detail.html
```

## Contributing

1. Fork the repository
2. Create a new branch
3. Make your changes
4. Submit a pull request

## License

This project is licensed under the MIT License.
