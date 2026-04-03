from flask import Flask, render_template
from werkzeug.utils import redirect

from data import db_session
from data.users import User

from forms.login_form import LoginForm
from forms.register_form import RegisterForm
from flask_login import LoginManager, login_user, login_required, logout_user



app = Flask(__name__)


app.config["SECRET_KEY"] = "password123"

login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def user_loader(user_id):
    session = db_session.create_session()
    return session.get(User, user_id)


@app.route("/")
def main():
    return render_template("base.html", title="Главная")


@app.route("/register", methods=['GET', 'POST'])
def register():
    reg_form = RegisterForm()
    if reg_form.validate_on_submit():
        session = db_session.create_session()

        guy = User(
            surname=reg_form.surname.data,
            name=reg_form.name.data,
            email=reg_form.email.data,
        )
        guy.hash_password(reg_form.password.data)
        session.add(guy)
        session.commit()
        return redirect("/login")
    return render_template("register.html", form=reg_form, title="Регистрация")


@app.route("/login", methods=["GET", "POST"])
def login():
    login_form = LoginForm()
    if login_form.validate_on_submit():
        session = db_session.create_session()
        user = session.query(User).filter(
            User.email == login_form.email.data
        ).first()
        if user and user.check_password(login_form.password.data):
            login_user(user, login_form.remember_me)
            return redirect("/")
        return render_template("login.html", form=login_form, message="Пользователь не существует")
    return render_template("login.html", form=login_form, title="Авторизация")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/")


if __name__ == "__main__":
    db_session.global_init("db/messenger_min.db")
    app.run("127.0.0.1", 8080)