from decimal import Decimal, InvalidOperation
import os
import sqlite3
import uuid

from flask import Flask, current_app, flash, g, redirect, render_template, request, send_from_directory, url_for
from werkzeug.utils import secure_filename


def create_app(test_config=None):
    app = Flask(__name__)
    base_dir = os.path.abspath(os.path.dirname(__file__))
    app.config.from_mapping(
        SECRET_KEY="dev",
        DATABASE=os.path.join(base_dir, "instance", "catalog.db"),
        UPLOAD_FOLDER=os.path.join(base_dir, "static", "uploads"),
    )

    if test_config:
        app.config.update(test_config)

    os.makedirs(os.path.dirname(app.config["DATABASE"]), exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    init_db(app)

    @app.teardown_appcontext
    def close_db(_error):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    @app.route("/")
    def index():
        db = get_db()
        products = db.execute(
            "SELECT id, description, category, price, image_filename FROM products ORDER BY id DESC"
        ).fetchall()
        return render_template("index.html", products=products)

    @app.route("/products/new", methods=["GET", "POST"])
    def create_product():
        if request.method == "POST":
            description = request.form.get("description", "").strip()
            category = request.form.get("category", "").strip()
            price_value = request.form.get("price", "").strip()
            image = request.files.get("image")
            error = None

            if not description:
                error = "Description is required."
            elif not category:
                error = "Category is required."
            elif not price_value:
                error = "Price is required."
            elif image is None or not image.filename:
                error = "Product image is required."
            else:
                try:
                    price = Decimal(price_value)
                    if not price.is_finite() or price < 0:
                        raise InvalidOperation
                except InvalidOperation:
                    error = "Price must be a non-negative number."

            if error is None:
                filename = secure_filename(image.filename)
                if not filename:
                    flash("Product image filename is invalid.")
                    return render_template("create_product.html")
                unique_filename = f"{uuid.uuid4().hex}_{filename}"
                image.save(os.path.join(app.config["UPLOAD_FOLDER"], unique_filename))

                db = get_db()
                db.execute(
                    "INSERT INTO products (description, category, price, image_filename) VALUES (?, ?, ?, ?)",
                    (description, category, f"{price:.2f}", unique_filename),
                )
                db.commit()
                return redirect(url_for("index"))

            flash(error)

        return render_template("create_product.html")

    @app.route("/uploads/<path:filename>")
    def uploaded_file(filename):
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

    return app


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


def init_db(app):
    with app.app_context():
        db = sqlite3.connect(app.config["DATABASE"])
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                description TEXT NOT NULL,
                category TEXT NOT NULL,
                price TEXT NOT NULL,
                image_filename TEXT NOT NULL
            )
            """
        )
        db.commit()
        db.close()


app = create_app()


if __name__ == "__main__":
    app.run()
