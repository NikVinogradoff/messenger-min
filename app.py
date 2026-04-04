from flask_restful import abort

from config import *


@login_manager.user_loader
def user_loader(user_id):
    session = db_session.create_session()
    return session.get(User, user_id)


@app.route("/", methods=["GET", "POST"])
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


@app.route("/chat/<int:chat_id>", methods=['GET', 'POST'])
@login_required
def chat(chat_id):
    session = db_session.create_session()
    chatting = session.query(Chat).filter(Chat.id == chat_id).first()
    filename = f"chats_jsons/{chatting.json_url}.json"
    with open(filename, "r") as json_file:
        messages = json.load(json_file)
    if request.method == 'POST':
        with open(filename, "w") as old_json:
            messages[f'message_{len(messages.keys()) + 1}'] = {
                "author_id": current_user.id,
                "author_name": f"{current_user.name} {current_user.surname}",
                "text": request.form.get("text"),
                "datetime": str(datetime.datetime.now())[:-7]
            }
            json.dump(messages, old_json)
    return render_template("chat.html", title=chatting.title, messages=messages)


@app.route("/create_chat", methods=["GET", "POST"])
@login_required
def create_chat():
    if request.method == "POST":
        title = request.form.get("title")
        avatar = request.files.get("avatar")
        if not title:
            return render_template("create_chat.html", error="Введите название чата",
                                   title="Создать чат")
        session = db_session.create_session()
        chat = Chat(title=title)
        user = session.merge(current_user)
        chat.members.append(user)
        if avatar and avatar.filename:
            avatars_dir = os.path.join(app.static_folder, "img", "chat_avatars")
            os.makedirs(avatars_dir, exist_ok=True)
            filename = f"chat_{chat.id or hash(title)}.png"
            filepath = os.path.join(avatars_dir, filename)
            avatar.save(filepath)
            chat.avatar_url = f"img/chat_avatars/{filename}"
        session.add(chat)
        session.commit()
        if not chat.id:
            new_filename = f"chat_{chat.id}.png"
            old_path = os.path.join(avatars_dir, f"chat_{hash(title)}.png")
            new_path = os.path.join(avatars_dir, new_filename)
            if os.path.exists(old_path):
                os.rename(old_path, new_path)
            chat.avatar_url = f"img/chat_avatars/{new_filename}"
            session.commit()
        with open(f"chats_jsons/chat_{chat.id}.json", "w") as chat_json:
            json.dump({}, chat_json)
        chat.json_url = f"chat_{chat.id}"
        session.commit()
        return redirect("/main_page")

    return render_template("create_chat.html", title="Создать чат")


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


@app.route("/confirm_delete/<int:chat_id>")
@login_required
def confirm_delete(chat_id):
    session = db_session.create_session()
    chat = session.query(Chat).get(chat_id)
    if not chat or current_user not in chat.members:
        abort(404)
    return render_template("confirm_delete.html", chat=chat)


@app.route("/delete_chat/<int:chat_id>", methods=["POST"])
@login_required
def delete_chat(chat_id):
    session = db_session.create_session()
    chat = session.query(Chat).get(chat_id)
    if not chat or current_user not in chat.members:
        abort(404)
    chat.is_deleted = True
    session.commit()
    return redirect("/main_page")


if __name__ == "__main__":
    db_session.global_init("db/messenger_min.db")
    serve(app, host="127.0.0.1", port=8080)
