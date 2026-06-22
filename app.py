from flask import Flask, render_template, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = "stok-secret"

# ---------------- DATABASE ----------------
uri = os.environ.get("DATABASE_URL", "sqlite:///stok.db")

if uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = uri
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ---------------- ADMIN ----------------
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD_HASH = generate_password_hash("53123")


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    stock = db.Column(db.Integer, default=0)


# ---------------- SAFE INT ----------------
def parse_int(value):
    try:
        return int(str(value).replace(".", "").replace(",", "").strip())
    except:
        return 0


# ---------------- ROUTES ----------------
@app.route("/")
def home():
    return redirect("/dashboard") if "user" in session else redirect("/login")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]

        if u == ADMIN_USERNAME and check_password_hash(ADMIN_PASSWORD_HASH, p):
            session["user"] = "admin"
            session["role"] = "admin"
            return redirect("/dashboard")

        return render_template("login.html", error=True)

    return render_template("login.html", error=False)


@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")

    products = Product.query.order_by(Product.id.asc()).all()

    return render_template(
        "dashboard.html",
        user=session["user"],
        products=products,
        total_products=len(products),
        total_stock=sum(p.stock for p in products)
    )


@app.route("/stock", methods=["GET", "POST"])
def stock():
    if "user" not in session:
        return redirect("/login")

    if session.get("role") != "admin":
        return "Yetkin yok"

    if request.method == "POST":
        action = request.form.get("action")

        # ---------------- CREATE ----------------
        if action == "CREATE":
            name = request.form["name"].upper().strip()
            stock_val = parse_int(request.form["stock"])

            existing = Product.query.filter_by(name=name).first()

            if existing:
                # ❌ HATA SAYFASI YOK → geri dön
                return redirect("/stock?error=exists")

            db.session.add(Product(name=name, stock=stock_val))

        # ---------------- UPDATE ----------------
        elif action == "UPDATE":
            product = Product.query.get(request.form["id"])
            amount = parse_int(request.form["amount"])
            mode = request.form["mode"]

            if product:
                if mode == "add":
                    product.stock += amount
                elif mode == "sub":
                    product.stock = max(0, product.stock - amount)

        # ---------------- DELETE ----------------
        elif action == "DELETE":
            product = Product.query.get(request.form["id"])
            if product:
                db.session.delete(product)

        db.session.commit()
        return redirect("/stock")

    products = Product.query.order_by(Product.id.asc()).all()

    return render_template("stock.html", products=products)


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 10000)),
        debug=True,
        use_reloader=True
    )
