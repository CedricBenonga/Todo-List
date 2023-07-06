from functools import wraps
import sqlalchemy
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_bootstrap import Bootstrap5

# # if Bootstrap5 gives red, please run these two lines of code to the terminal:
    # pip uninstall flask-bootstrap bootstrap-flask
    # pip install bootstrap-flask
# # And, in the interpreter under settings, uninstall both then install bootstrap-flask

from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user
from forms import NewTaskForm, RegisterForm, LoginForm


app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
Bootstrap5(app)

# Connecting to DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///todo-list.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# Creating user Table
class User(UserMixin, db.Model):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(100))


with app.app_context():
    db.create_all()


# Creating task Table
class TaskPost(db.Model):
    __tablename__ = "task"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), unique=True, nullable=False)
    date = db.Column(db.String(250), nullable=False)
    # # Creating a relational database
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))  # To get this line successfully, the User class must be
    # on top of the TaskPost class as the DB is created from the top lines going down. So if the TaskPost comes first,
    # it will crush as the ForeignKey("user.id") won't be found bcz it's not yet created.


with app.app_context():
    db.create_all()


login_manager = LoginManager()
login_manager.init_app(app)


# Creating "registered only" decorator, restriction for none-registered user.
def registered_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # If user did not log in, tell them to Sign In or Sign Up firsts
        if not current_user.is_authenticated:
            flash("Please Sign In or Sign Up first!")
            return redirect(url_for("home"))
        # Else, continue with the route function
        return f(*args, **kwargs)

    return decorated_function


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) no such table: ...
# [SQL: INSERT INTO ... (..., ...) VALUES (?, ?)] [parameters: ('..., ...')]

# # # # # # # # # # # # # # ## # # # # # # # ADDING THE FIRST RECORD # ## # # # # # # # # # # # ## # # # # # # # ##
# In order to add the first record in the database and avoid the above error, your first route where you have the
# index.html should not have anything related to the database on the fist run:
    # @app.route('/')
    # def home():
    #     return render_template("index.html")
# After the first run, and after adding the fist record (from the web), you can now add anything related to the database
# that you want on the home page.


@app.route('/')
def home():
    posts = TaskPost.query.all()

    # informing the user that they have no task on the selected date
    user_tasks = []
    try:
        for post in posts:
            if post.user_id == current_user.id:
                user_tasks.append(post)
    except AttributeError:
        pass
        # flash("Please Sign In or Sign Up first!")
        # return redirect(url_for('date_selector'))

    return render_template("index.html", all_posts=posts, user_tasks=user_tasks)


@app.route("/date_selector", methods=["POST", "GET"])
def date_selector():
    if request.method == 'POST':
        selected_date = request.form["date"]
        posts = TaskPost.query.all()

        date_split = selected_date.split("-")
        print(date_split)
        day = date_split[2]
        month = date_split[1]
        year = date_split[0]

        if month == "01":
            month = "January"
        elif month == "02":
            month = "February"
        elif month == "03":
            month = "March"
        elif month == "04":
            month = "April"
        elif month == "05":
            month = "May"
        elif month == "06":
            month = "June"
        elif month == "07":
            month = "July"
        elif month == "08":
            month = "August"
        elif month == "09":
            month = "September"
        elif month == "10":
            month = "October"
        elif month == "11":
            month = "November"
        else:
            month = "December"

        selected_date = f"{month} {day}, {year}"

        # informing the user that they have no task on the selected date
        no_task = []
        try:
            for post in posts:
                if post.user_id == current_user.id and post.date == selected_date:
                    no_task.append(post)
        except AttributeError:
            flash("Please Sign In or Sign Up first!")
            return redirect(url_for('date_selector'))

        return render_template("date_selector.html", selected_date=selected_date, all_posts=posts, no_task=no_task)
    return render_template("date_selector.html")


@app.route("/edit-task/<int:post_id>", methods=['GET', 'POST'])
@registered_only  # This decorator checks if the user is registered or not
def edit_task(post_id):

    post = TaskPost.query.get(post_id)
    edit_form = NewTaskForm(
        name=post.name,
    )
    if edit_form.validate_on_submit():
        post.name = edit_form.name.data
        post.date = edit_form.date.data.strftime("%B %d, %Y")

        db.session.commit()
        return redirect(url_for("home"))
    return render_template("make-post.html", form=edit_form)


@app.route('/register', methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit() and request.method == "POST":

        # Checking if the user already exists
        if User.query.filter_by(email=request.form.get('email')).first():
            flash("It looks like you've registered already, please login instead!")  # to see this message,
            # you need to add some lines of code in the login.htl right on top of the form (in the same div).
            return redirect(url_for('login'))

        # Checking user's email validity
        if "@" not in request.form.get('email'):
            flash("Invalid email address!")
            return redirect(url_for('register'))

        if "." not in request.form.get('email'):
            flash("Invalid email address!")
            return redirect(url_for('register'))

        # Hashing and salting (encrypting) the user's password
        hashed_and_salted_password = generate_password_hash(
            request.form.get('password'),
            method='pbkdf2:sha256',
            salt_length=8
        )

        # Creating a new user's profile
        new_user = User(
            email=request.form.get('email'),
            name=request.form.get('name'),
            password=hashed_and_salted_password
        )

        # Adding the new user to the database
        db.session.add(new_user)
        db.session.commit()
        # Login and authenticate user after adding details to database.
        login_user(new_user)

        return redirect(url_for("home", name=new_user.name))
    return render_template("register.html", form=form)


@app.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit() and request.method == "POST":

        # Get data entered by the user
        email = request.form.get('email')  # or form.email.data
        password = request.form.get('password')  # or form.password.data

        # Find user in the DB by using the email entered.
        user = User.query.filter_by(email=email).first()

        # If email doesn't exist
        if not user:
            flash("Incorrect email address, please try again.")
            return redirect(url_for('login'))

        # If password incorrect
        elif not check_password_hash(user.password, password):
            flash('Incorrect password, please try again.')
            return redirect(url_for('login'))

        # If email exists in the DB and password correct, authorize access.
        else:
            login_user(user)
            return redirect(url_for('home'))

    return render_template("login.html", form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route("/new-post", methods=['GET', 'POST'])
@registered_only  # This decorator checks if the user is registered or not
def add_new_post():
    try:  # this checks if the user is duplicating a post or not
        form = NewTaskForm()
        if form.validate_on_submit():
            new_task = TaskPost(
                name=form.name.data,
                date=form.date.data.strftime("%B %d, %Y"),
                user_id=current_user.id
            )
            db.session.add(new_task)
            db.session.commit()
            return redirect(url_for("home"))
    except sqlalchemy.exc.IntegrityError:
        flash("Name already exist in the database! Please rename.")  # to see this message,
        # you need to add some lines of code in the make-post.html right on top of the form (in the same div).
        return redirect(url_for('add_new_post'))
    return render_template("make-post.html", form=form)


@app.route("/delete/<int:post_id>")
def delete_post(post_id):
    post_to_delete = TaskPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for("home"))


@app.route("/confirmation/<int:post_id>")
def confirm_delete(post_id):
    post_to_delete = TaskPost.query.get(post_id)
    return render_template("confirm_delete.html", post=post_to_delete)


if __name__ == "__main__":
    app.run(debug=True)
