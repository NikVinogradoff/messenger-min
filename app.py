from config import *


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


@app.route("/main_page")
@login_required
def main_page():
    return render_template("main_page.html", title="Главная страница")

@app.route("/chat")
@login_required
def chat():
    return render_template("chat.html", title="Чат")

@app.route("/profile")
@login_required
def profile():
    session = db_session.create_session()
    user = session.query(User).filter(User.id == current_user.id).first()
    return render_template("profile.html", title="Профиль", current_user=user)

if __name__ == "__main__":
    db_session.global_init("db/messenger_min.db")
    app.run("127.0.0.1", 8080)
