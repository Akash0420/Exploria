import os
import datetime

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, usd
from datetime import date

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.route("/")
@login_required
def index():

    # Get all transactions by user
    transactions = db.execute("SELECT * FROM transactions WHERE user_id=:user_id", user_id=session.get("user_id"))

    # Load index page
    return render_template("login1.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":

        # Ensure Username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Ensure Passwords match
        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("passwords must match", 403)

        # Check if username already exists in database
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))

        # If username doesn't exist, add to database
        if len(rows) != 1:
            username = request.form.get("username")
            password = request.form.get("password")
            db.execute("INSERT INTO users (username, hash) VALUES (:username, :password)", username=username, password=generate_password_hash(password))
            return redirect("/")

        # Else return apology
        else:
            return apology("username already exists", 403)

    else:
        return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("Register First", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/choose", methods=["GET", "POST"])
@login_required
def choose():
    if request.method == "POST":

        Country=(request.form.get("country"))

        # Check if symbol is valid
        if Country == None:
          return apology("invalid symbol", 403)

        # Else render html with embedded variables from the lookup
        elif Country == "Switzerland":
            return render_template("swiss.html")

        elif Country == "France":
            return render_template("paris.html")

        elif Country == "Singapore":
            return render_template("singapore.html")

        elif Country == "Japan":
            return render_template("japan.html")
    else:
        return render_template("choose.html")



@app.route("/changepassword", methods=["GET", "POST"])
@login_required
def changePassword():
    if request.method == "GET":
        return render_template("changepassword.html")
    else:
        old_password = request.form.get("old_password")
        if not old_password:
            return apology("Input current password.")

        # query database for user_id
        rows = db.execute("SELECT hash FROM users WHERE id = :user_id", user_id=session["user_id"])
        # ensure current password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], old_password):
            return apology("Invalid password")

        new_password = request.form.get("new_password")
        if not new_password:
            return apology("Please make a new password.")

        confirm_password = request.form.get("confirm_password")
        if new_password != confirm_password:
            return apology("The password didn't match")

        # update database
        password_hash = generate_password_hash(new_password)
        db.execute("UPDATE users SET hash = :password_hash WHERE id = :user_id", user_id=session["user_id"], password_hash = password_hash)

        flash("Password Changed")
        return redirect("/")


@app.route("/add", methods=["GET", "POST"])
@login_required
def add():
    """Add Cash to Account"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Get user info
        user_id = session["user_id"]
        user_info = list(db.execute("SELECT * FROM users WHERE id = (?)", user_id))
        username = user_info[0]["username"]
        cash = float(user_info[0]["cash"])

        # Get submit info
        add_t = request.form.get("amount")

        # Apologize if blank
        if not add_t:
            return apology("specify amount", 402)

        # Apologize if negative
        add = float(add_t)
        if add < 0:
            return apology("why would you want to add negative cash?", 400)

        # Add cash
        cash = cash + add
        db.execute("UPDATE users SET cash = (?) WHERE id = (?)", cash, user_id)

        # Display success
        return render_template("added.html", cash = usd(cash), username = username, amount = usd(add))

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("add.html")



@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():

    if request.method == "POST":

        # Check user has inputted symbol
        if not request.form.get("country"):
            return apology("must select country", 403)

        # Check user has inputted valid quantity
        if not request.form.get("people").isnumeric():
            return apology("invalid people", 403)

        # Get price of country and cost of total package
        price=db.execute("select price from country_packages where country_name=:country", country=request.form.get("country"))[0]["price"]
        cost=price*int(request.form.get("people"))

        # Get current cash user has in account
        cash = db.execute("SELECT cash FROM users WHERE id=:user_id", user_id=session.get("user_id"))[0]["cash"]

        # Check if user has enough cash to buy the stock
        if cost > cash:
            return apology("Insufficient cash to complete transaction. Transaction cancelled.", 403)

        # Buy stocks
        else:
            # Remove cash from user's account
            db.execute("UPDATE users SET cash=:newamount WHERE id=:user_id", newamount=(cash-cost), user_id=session.get("user_id"))

            # Add transaction to database
            db.execute("INSERT INTO user_details (user_id, type, place, from_date, people,price, datetime) VALUES (:user_id, 'booked', :place, :from_date, :people, :price, :datetime)",
            user_id=session.get("user_id"), people=request.form.get("people"),place=request.form.get("country"), from_date=request.form.get("from_date") ,price=price, datetime=datetime.datetime.now())


            # Display success
            newamount=cash-cost

            return render_template("bookingsuccess.html", cash = newamount, country = request.form.get("country"))


    else:
        return render_template("buy.html")


@app.route("/Cancellation", methods=["GET", "POST"])
@login_required
def Cancellation():

    if request.method == "POST":

        # Check user has inputted symbol
        if not request.form.get("country"):
            return apology("must select country", 403)

        price=db.execute("select price from country_packages where country_name=:country", country=request.form.get("country"))[0]["price"]

        # Get all transactions by user for selected symbol
        transactions = db.execute("SELECT * FROM user_details WHERE type='booked' and user_id=:user_id AND upper(place)=:country", user_id=session.get("user_id"), country=(request.form.get("country")).upper())

        # Keep count of shares
        No_of_people=0

        # Check if user has enough shares to sell
        for transaction in transactions:
            #Buy
          #  if transaction["type"] == "booked":
           #     No_of_people+=transaction["people"]
            # Sell
            #else:
             #   No_of_people-=transaction["people"]

              if transaction["type"] == "booked":
                No_of_people=int(request.form.get("quantity"))
                from_date=transaction["from_date"]

                db.execute("INSERT INTO user_details (user_id, type, place, people, price, from_date, datetime) VALUES (:user_id, 'cancelled', :place, :people, :price, :from_date, :datetime)",
                user_id=session.get("user_id"), place=request.form.get("country"), people=No_of_people, price=price, from_date=from_date, datetime=datetime.datetime.now())

            # Get current cash user has in account
                cash = db.execute("SELECT cash FROM users WHERE id=:user_id", user_id=session.get("user_id"))[0]["cash"]


            # Add cash to user's account
                db.execute("UPDATE users SET cash=:newamount WHERE id=:user_id", newamount=(cash+150), user_id=session.get("user_id"))

        # Return to index page
        return redirect("/")

    else:
        # Load owned shares first
        # Get all transactions by user
        transactions = db.execute("SELECT * FROM user_details WHERE user_id=:user_id", user_id=session.get("user_id"))

        # Initialise dictionary to store all owned symbols and quantities
        portfolio = {}

        # For every transaction
        for transaction in transactions:

            # Check if the symbol has an entry in portfolio, make one if not
           if transaction["place"] not in portfolio:
               portfolio[transaction["place"]] = 0

            # Update total
            # Buy
           if transaction["type"] == 'buy':
               portfolio[transaction["place"]] += transaction["people"]
            # Sell
           else:
               portfolio[transaction["place"]] -= transaction["people"]

        # Return sell page, inputting portfolio for select box
        return render_template("Cancellation.html",portfolio=portfolio)

@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    # Get all transactions by user
    transactions=db.execute("SELECT * FROM  user_details WHERE user_id=:user_id", user_id=session.get("user_id"))


    # Return history
    return render_template("history.html", transactions=transactions)




@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
