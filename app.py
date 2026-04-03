from config import *


@login_manager.user_loader
def user_loader(user_id):
    session = db_session.create_session()
    return session.get(User, user_id)


@app.route("/")
@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect("/main_page")
    login_form = LoginForm()
    if login_form.validate_on_submit():
        session = db_session.create_session()
        user = session.query(User).filter(
            User.email == login_form.email.data
        ).first()
        if user and user.check_password(login_form.password.data):
            login_user(user, login_form.remember_me)
            return redirect("/main_page")
        return render_template("login.html", form=login_form, message="Пользователь не существует")
    return render_template("login.html", form=login_form, title="Авторизация")


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


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/")

@app.route("/main_page")
def main_page():
    session = db_session.create_session()
    user = session.query(User).filter(User.id == current_user.id).first()
    if not user:
        logout_user()
        return redirect("/login")
    chats = user.chats
    return render_template("main_page.html", title="Мои чаты", chats=chats)

@app.route("/chat")
@login_required
def chat():
    return render_template("chat.html", title="Чат")

@app.route("/create_chat", methods=["GET", "POST"])
def create_chat():
    pass

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    session = db_session.create_session()
    user = session.query(User).filter(User.id == current_user.id).first()
    if not user:
        logout_user()
        return redirect("/login")
    avatar_folder = os.path.join(app.root_path, 'static', 'img', 'avatars')
    os.makedirs(avatar_folder, exist_ok=True)
    avatar_url = None
    if request.method == "POST":
        if 'avatar' in request.files:
            file = request.files['avatar']
            if file and file.filename != '':
                old_avatar = os.path.join(avatar_folder, f"user_{user.id}.png")
                if os.path.exists(old_avatar):
                    os.remove(old_avatar)
                filename = secure_filename(f"user_{user.id}.png")
                file.save(os.path.join(avatar_folder, filename))
    avatar_path = f"img/avatars/user_{user.id}.png"
    avatar_full_path = os.path.join(app.root_path, 'static', avatar_path)
    if os.path.exists(avatar_full_path):
        avatar_url = url_for('static', filename=avatar_path) + "?t=" + str(os.path.getmtime(avatar_full_path))
    return render_template("profile.html", title="Профиль", current_user=user, avatar_url=avatar_url)


if __name__ == "__main__":
    db_session.global_init("db/messenger_min.db")
    app.run("127.0.0.1", 8080)
