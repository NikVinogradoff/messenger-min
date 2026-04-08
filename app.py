import json

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
        login_user(guy, reg_form.remember_me)
        im = Image.open('static/img/min_logo.png')
        im.save(f"static/img/avatars/user_{guy.id}.png")
        saved_messages = Chat(
            title="Избранное",
            creator_id=guy.id,
            avatar_url="img/saved_messages_icon.png",
            is_public=False,
            is_group=False
        )
        session.add(saved_messages)
        session.commit()
        saved_messages.json_url = f"chat_{saved_messages.id}"
        saved_messages.members.append(guy)
        session.commit()
        with open(f"chats_jsons/chat_{saved_messages.id}.json", "w") as saved_json:
            json.dump({}, saved_json)
        return redirect("/main_page")
    return render_template("register.html", form=reg_form, title="Регистрация")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/")


@app.route("/main_page")
@login_required
def main_page():
    session = db_session.create_session()
    user = session.query(User).filter(User.id == current_user.id).first()
    if not user:
        logout_user()
        return redirect("/login")
    chats = list(filter(lambda users_chat: users_chat.is_group, user.chats))
    own_chats = list(filter(lambda users_chat: not users_chat.is_group, user.chats))
    public_chats = session.query(Chat).filter(Chat.is_public == True, ~Chat.members.contains(user)).all()
    return render_template("main_page.html", title="Мои чаты", chats=chats, own_chats=own_chats,
                           public_chats=public_chats, user=user)


@app.route("/chat/<int:chat_id>", methods=['GET', 'POST'])
@login_required
def chat(chat_id):
    session = db_session.create_session()
    chatting = session.query(Chat).filter(Chat.id == chat_id).first()
    if not chatting or (not chatting.is_public and current_user not in chatting.members):
        abort(403)
    filename = f"chats_jsons/{chatting.json_url}.json"
    with open(filename, "r") as json_file:
        messages = json.load(json_file)
    if request.method == 'POST':
        raw_text = request.form.get("text", "").strip()
        if len(raw_text) > 500:
            raw_text = raw_text[:500]
        lines = raw_text.split('\n')
        wrapped_lines = []
        for line in lines:
            while len(line) > 60:
                wrapped_lines.append(line[:60])
                line = line[60:]
            wrapped_lines.append(line)
        formatted_text = '\n'.join(wrapped_lines)
        file_url = None
        safe_filename = None
        if 'file' in request.files:
            file = request.files['file']
            if file and file.filename != '':
                allowed = file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.txt', '.mp4'))
                if not allowed:
                    return render_template("chat.html", title=chatting.title, messages=messages,
                                           chatting=chatting, user_avatars={},
                                           message_error="Разрешены только: PNG, JPG, JPEG, GIF, TXT, MP4")
                chat_files_dir = os.path.join(app.static_folder, "chat_files", str(chatting.id))
                os.makedirs(chat_files_dir, exist_ok=True)
                safe_filename = secure_filename(file.filename)
                filepath = os.path.join(chat_files_dir, safe_filename)
                file.save(filepath)
                file_url = url_for('static', filename=f"chat_files/{chatting.id}/{safe_filename}")
        with open(filename, "w") as old_json:
            message_key = f'message_{len(messages.keys()) + 1}'
            messages[message_key] = {
                "author_id": current_user.id,
                "author_name": f"{current_user.name} {current_user.surname}",
                "text": formatted_text,
                "datetime": str(datetime.datetime.now())[:-7],
                "file_url": file_url,
                "filename": safe_filename
            }
            json.dump(messages, old_json)
        return redirect(f"/chat/{chat_id}")
    user_avatars = {}
    for member in chatting.members:
        avatar_path = f"img/avatars/user_{member.id}.png"
        avatar_full_path = os.path.join(app.root_path, 'static', avatar_path)
        if os.path.exists(avatar_full_path):
            user_avatars[member.id] = url_for('static', filename=avatar_path) + \
                                      "?t=" + str(os.path.getmtime(avatar_full_path))
        else:
            user_avatars[member.id] = None
    return render_template("chat.html", title=chatting.title, messages=messages, chatting=chatting,
                           user_avatars=user_avatars, user=current_user)



@app.route("/create_chat", methods=["GET", "POST"])
@login_required
def create_chat():
    if request.method == "POST":
        title = request.form.get("title")
        avatar = request.files.get("avatar")
        is_public = bool(request.form.get("is_public"))
        if not title:
            return render_template("create_chat.html", error="Введите название чата",
                                   title="Создать чат")
        session = db_session.create_session()
        user = session.merge(current_user)
        chat = Chat(title=title, creator_id=user.id, is_public=is_public)
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
    if not chat or current_user not in chat.members or chat.creator_id != current_user.id:
        abort(404)
    return render_template("confirm_delete.html", chat=chat)


@app.route("/delete_chat/<int:chat_id>", methods=["POST"])
@login_required
def delete_chat(chat_id):
    session = db_session.create_session()
    chat = session.query(Chat).get(chat_id)
    if not chat or chat.creator_id != current_user.id:
        abort(403)
    chat.is_deleted = True
    session.commit()
    return redirect("/main_page")


@app.route("/chat/<int:chat_id>/add_user", methods=["GET", "POST"])
@login_required
def add_user_to_chat(chat_id):
    session = db_session.create_session()
    chat = session.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        abort(404)
    if current_user not in chat.members:
        abort(403)
    error = None
    if request.method == "POST":
        email = request.form.get("email")
        if not email:
            error = "Введите email пользователя"
        else:
            user_to_add = session.query(User).filter(User.email == email).first()
            if not user_to_add:
                error = "Пользователь с таким email не найден"
            elif user_to_add in chat.members:
                error = "Пользователь уже состоит в этом чате"
            else:
                chat.members.append(user_to_add)
                session.commit()
                return redirect(f"/chat/{chat_id}")
    return render_template("add_user.html", chat=chat, error=error)


@app.route("/chat/<int:chat_id>/leave", methods=["POST"])
@login_required
def leave_chat(chat_id):
    session = db_session.create_session()
    chat = session.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        abort(404)
    if current_user not in chat.members:
        abort(403)
    chat.members.remove(current_user)
    session.commit()
    if len(chat.members) == 0:
        chat.is_deleted = True
    return redirect("/main_page")


@app.route("/confirm_leave_chat/<int:chat_id>")
@login_required
def confirm_leave_chat(chat_id):
    session = db_session.create_session()
    chat = session.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        abort(404)
    if current_user not in chat.members:
        abort(403)
    return render_template("confirm_leave_chat.html", chat=chat)


@app.route("/chat/<int:chat_id>/remove_user/<int:user_id>", methods=["POST"])
@login_required
def remove_user_from_chat(chat_id, user_id):
    session = db_session.create_session()
    chat = session.query(Chat).filter(Chat.id == chat_id).first()
    user_to_remove = session.query(User).filter(User.id == user_id).first()
    if not chat or not user_to_remove:
        abort(404)
    if current_user.id != chat.creator_id:
        abort(403)
    if current_user.id == user_to_remove.id:
        abort(400, description="Нельзя выгнать самого себя. Используйте 'Выйти из чата'.")
    if user_to_remove not in chat.members:
        abort(400, description="Пользователь не состоит в этом чате.")
    chat.members.remove(user_to_remove)
    session.commit()
    return redirect(f"/chat/{chat_id}")


@app.route("/chat/<int:chat_id>/members")
@login_required
def chat_members(chat_id):
    session = db_session.create_session()
    chat = session.query(Chat).filter(Chat.id == chat_id).first()

    if not chat:
        abort(404)
    if current_user not in chat.members:
        abort(403)

    return render_template("chat_members.html", chat=chat)


@app.route("/join_public_chat/<int:chat_id>", methods=["POST"])
@login_required
def join_public_chat(chat_id):
    session = db_session.create_session()
    chat = session.query(Chat).filter(Chat.id == chat_id, Chat.is_public == True).first()
    if not chat:
        abort(404)
    user = session.merge(current_user)
    if user not in chat.members:
        chat.members.append(user)
        session.commit()
    return redirect(f"/chat/{chat_id}")


@app.route("/chat/<int:chat_id>/confirm_remove/<int:user_id>")
@login_required
def confirm_remove_user(chat_id, user_id):
    session = db_session.create_session()
    chat = session.query(Chat).filter(Chat.id == chat_id).first()
    user_to_remove = session.query(User).filter(User.id == user_id).first()

    if not chat or not user_to_remove:
        abort(404)
    if current_user.id != chat.creator_id:
        abort(403)

    return render_template("confirm_remove_user.html", chat=chat, user=user_to_remove)


@app.route("/chat/<int:chat_id>/edit", methods=["GET", "POST"])
@login_required
def edit_chat(chat_id):
    session = db_session.create_session()
    chat = session.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        abort(404)
    if current_user.id != chat.creator_id:
        abort(403)

    error = None
    if request.method == "POST":
        title = request.form.get("title")
        avatar = request.files.get("avatar")
        is_public = bool(request.form.get("is_public"))

        if not title:
            error = "Введите название чата"
        else:
            chat.title = title
            chat.is_public = is_public

            if avatar and avatar.filename:
                avatars_dir = os.path.join(app.static_folder, "img", "chat_avatars")
                os.makedirs(avatars_dir, exist_ok=True)
                filename = f"chat_{chat.id}.png"
                filepath = os.path.join(avatars_dir, filename)
                if os.path.exists(filepath):
                    os.remove(filepath)
                avatar.save(filepath)
                chat.avatar_url = f"img/chat_avatars/{filename}"

            session.commit()
            return redirect(f"/chat/{chat_id}")

    return render_template("edit_chat.html", chat=chat, error=error)


@app.route("/search_chats", methods=["GET"])
@login_required
def search_chats():
    query = request.args.get("q", "").strip()
    session = db_session.create_session()
    user = session.merge(current_user)
    chats = session.query(Chat).filter(
        Chat.is_public == True,
        Chat.is_deleted == False,
        Chat.title.ilike(f"%{query}%"),
        ~Chat.members.contains(user)
    ).all()

    return render_template("search_results.html", chats=chats, query=query)


@app.route("/chat/<int:chat_id>/edit/<message_key>", methods=["POST"])
@login_required
def edit_message(chat_id, message_key):
    session = db_session.create_session()
    chatting = session.query(Chat).filter(Chat.id == chat_id).first()
    if not chatting or current_user not in chatting.members:
        abort(403)
    filename = f"chats_jsons/{chatting.json_url}.json"
    with open(filename, "r") as json_file:
        messages = json.load(json_file)
    if message_key not in messages:
        abort(404)
    if messages[message_key]["author_id"] != current_user.id:
        abort(403)
    raw_text = request.form.get("text", "").strip()
    if len(raw_text) > 500:
        raw_text = raw_text[:500]
    lines = raw_text.split('\n')
    wrapped_lines = []
    for line in lines:
        while len(line) > 60:
            wrapped_lines.append(line[:60])
            line = line[60:]
        wrapped_lines.append(line)
    formatted_text = '\n'.join(wrapped_lines)
    messages[message_key]["text"] = formatted_text
    messages[message_key]["edited"] = True
    messages[message_key]["edit_time"] = str(datetime.datetime.now())[:-7]
    with open(filename, "w") as f:
        json.dump(messages, f)
    return redirect(f"/chat/{chat_id}")


@app.route("/chat/<int:chat_id>/delete/<message_key>", methods=["POST"])
@login_required
def delete_message(chat_id, message_key):
    session = db_session.create_session()
    chatting = session.query(Chat).filter(Chat.id == chat_id).first()
    if not chatting or current_user not in chatting.members:
        abort(403)
    filename = f"chats_jsons/{chatting.json_url}.json"
    with open(filename, "r") as json_file:
        messages = json.load(json_file)
    if message_key not in messages:
        abort(404)
    if messages[message_key]["author_id"] != current_user.id and current_user.id != chatting.creator_id:
        abort(403)
    del messages[message_key]
    with open(filename, "w") as f:
        json.dump(messages, f)
    return redirect(f"/chat/{chat_id}")


@app.route("/search_person", methods=['GET', 'POST'])
@login_required
def search_person():
    session = db_session.create_session()
    if request.method == 'POST':
        user_id, surname, name, email = request.form.get('user').split()
        chatting = Chat(title=f"{current_user.name} {current_user.surname}, {current_user.email}; "
                              f"{name} {surname}, {email}",
                        creator_id=current_user.id,
                        is_public=False,
                        is_group=False)
        user = session.query(User).filter(User.id == user_id).first()
        own_chat = session.query(Chat).filter(Chat.is_group == False,
                                               Chat.is_deleted == False,
                                               Chat.members.contains(current_user),
                                               Chat.members.contains(user)).first()
        if own_chat:
            return redirect(f"/chat/{own_chat.id}")
        chatting.members.append(user)
        chatting.members.append(current_user)
        session.add(chatting)
        session.commit()
        with open(f"chats_jsons/chat_{chatting.id}.json", "w") as chat_json:
            json.dump({}, chat_json)
        chatting.json_url = f"chat_{chatting.id}"
        session.commit()
        return redirect(f"/chat/{chatting.id}")
    query = request.args.get("p").strip()
    user = session.query(User).filter(
        User.is_deleted == False,
        User.email == query
    ).first()
    if not user:
        return render_template("search_person.html", user=None, query=query, user_avatars=None)
    user_avatars = {}
    avatar_path = f"img/avatars/user_{user.id}.png"
    avatar_full_path = os.path.join(app.root_path, 'static', avatar_path)
    if os.path.exists(avatar_full_path):
        user_avatars[user.id] = url_for('static', filename=avatar_path) + \
                                        "?t=" + str(os.path.getmtime(avatar_full_path))
    else:
        user_avatars[user.id] = None
    return render_template("search_person.html", user=user, query=query, user_avatars=user_avatars)


if __name__ == "__main__":
    db_session.global_init("db/messenger_min.db")
    serve(app, host="127.0.0.1", port=8080, threads=32)
