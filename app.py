import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///final.db")
mb = SQL("sqlite:///movies.db")



@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def home():
    log = db.execute("SELECT id, username, title, score, review, date FROM reviews ORDER BY date DESC LIMIT 30")
    return render_template("homes.html", logs=log)


@app.route("/profile")
@login_required
def profile():
    posts = db.execute("SELECT title, score, review FROM reviews WHERE id = ?", session["user_id"])
    print(posts)
    users = db.execute("SELECT username, birthday, email FROM users WHERE id = ?", session["user_id"])
    print(users)
    return render_template("profile.html", post=posts, user=users)


@app.route("/review", methods=["GET", "POST"])
@login_required
def review():
    """Add Movies"""
    if request.method == "GET":
        return render_template("review.html")
    else:
        rating = request.form.get("rating")
        review = request.form.get("review")
        title = request.form.get("title")
        name = db.execute("SELECT username FROM users WHERE id = ?", session["user_id"])
        names = name[0]["username"]
        print(names)
        db.execute("INSERT INTO reviews (id, username, title, score, review) VALUES (?,?,?,?,?)", session["user_id"], names, title, rating, review)
        return redirect("/")



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
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "GET":
        return render_template("register.html")

    else:
        username = request.form.get("username")
        password = request.form.get("password")
        birthday = request.form.get("birthday")
        email = request.form.get("email")
        confirmation = request.form.get("confirmation")
        check = db.execute("SELECT username FROM users")
        if username == "NULL":
            return apology("please enter a valid username", 403)
        elif password != confirmation:
            return apology("passwords do not match", 403)
        elif username in check:
            db.close
            return apology("username taken", 403)
        else:
            # hashes the users password and stores all information in an SQL database
            hashpass = generate_password_hash(password)
            db.execute("INSERT into users (username, hash, birthday, email) VALUES (?,?,?,?)", username, hashpass, birthday, email)
            rows = db.execute("SELECT id FROM users WHERE username = ?", request.form.get("username"))
            session["user_id"] = rows[0]["id"]
            return render_template("login.html")


@app.route("/search", methods=["GET", "POST"])
def search():
    if request.method == "GET":
        return render_template("search.html")
    else:
        query = request.form.get("search")
        movies = db.execute("SELECT title FROM reviews")
        results = db.execute("SELECT username, title, score, review FROM reviews WHERE title = ?", query)
        summaries = mb.execute("SELECT DISTINCT title, year FROM movies, people JOIN ratings ON ratings.movie_id = movies.id WHERE title = ? LIMIT 1", query)
        star = mb.execute("SELECT points FROM ratings JOIN movies ON movies.id = ratings.movie_id WHERE title = ? LIMIT 1", query)
        for movie in movies:
            if query == movie["title"]:
                return render_template("searched.html", result=results, summary=summaries, stars=star)
        for short in summaries:
            if query == short["title"]:
                return render_template("searched.html", result=results, summary=summaries, stars=star)
        return apology("movie not found", 403)


@app.route("/watch", methods=["GET", "POST"])
def watch():
    if request.method == "GET":
        return render_template("watch.html")
    else:
        answer = request.form.get("filter")
        if answer == "director":
            director = request.form.get("search")
            suggestions = mb.execute("SELECT title FROM movies JOIN directors ON directors.movie_id = movies.id JOIN people ON people.id = directors.person_id JOIN ratings ON ratings.movie_id = movies.id WHERE name = ? ORDER BY points DESC LIMIT 5", director)
            print(suggestions)
            return render_template("recs.html", rec=suggestions)
        elif answer == "year":
            year = request.form.get("search")
            suggestions = mb.execute("SELECT title FROM movies JOIN ratings ON ratings.movie_id = movies.id WHERE year = ? ORDER BY points DESC LIMIT 5", year)
            return render_template("recs.html", rec=suggestions)
        elif answer == "actor":
            actor = request.form.get("search")
            suggestions = mb.execute("SELECT title FROM movies JOIN stars ON stars.movie_id = movies.id JOIN people ON people.id = stars.person_id JOIN ratings ON ratings.movie_id = movies.id WHERE name = ? ORDER BY points DESC LIMIT 5", actor)
            return render_template("recs.html", rec=suggestions)



def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
