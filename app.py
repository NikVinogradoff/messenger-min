import datetime
import json
import os

from dotenv import load_dotenv
from flask import Flask, render_template, request, url_for
from flask_login import LoginManager, login_required, current_user
from flask_restful import Api
from waitress import serve
from werkzeug.utils import redirect, secure_filename

from blueprints import auth, chat, channel
from data import db_session
from data.chats import Chat
from data.users import User
from forms.change_password_form import ChangePasswordForm
from resources.chats_resource import ChatsResource, ChatsListResource
from resources.users_resource import UsersResource, UsersListResource

load_dotenv(".env")

app = Flask(__name__)
api = Api(app)
api.add_resource(UsersResource, '/api/users/<int:user_id>')  # /api/users/1?apikey=aaa и аналогично
api.add_resource(UsersListResource, '/api/users/')
api.add_resource(ChatsResource, '/api/chats/<int:chat_id>')
api.add_resource(ChatsListResource, '/api/chats/')

app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]

login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def user_loader(user_id):
    session = db_session.create_session()
    return session.get(User, user_id)


@app.route("/")
def main():
    return redirect("/auth/login")


@app.route("/main_page")
@login_required
def main_page():
    session = db_session.create_session()
    user = session.merge(current_user)
    chats = list(filter(lambda users_chat: users_chat.is_group and not users_chat.is_deleted and
                                           not users_chat.is_channel, user.chats))
    own_chats = list(filter(lambda users_chat: not users_chat.is_group and not users_chat.is_deleted and
                                               not users_chat.is_channel, user.chats))
    channels = list(filter(lambda users_chat: users_chat.is_channel and not users_chat.is_deleted, user.chats))
    public_chats = session.query(Chat).filter(Chat.is_public == True, ~Chat.members.contains(user)).all()
    with open(f'users_settings/user_{user.id}_settings.json', 'r', encoding='utf-8') as settings_json:
        avatars_roundness = int(json.load(settings_json)["avatars_roundness"])
    return render_template("main_page.html", title="Мои чаты", chats=chats, own_chats=own_chats,
                           public_chats=public_chats, channel_chats=channels, user=user,
                           avatars_roundness=avatars_roundness)


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    session = db_session.create_session()
    user = session.merge(current_user)
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
    with open(f'users_settings/user_{user.id}_settings.json', 'r', encoding='utf-8') as settings_json:
        avatars_roundness = int(json.load(settings_json)["avatars_roundness"])
    if os.path.exists(avatar_full_path):
        avatar_url = url_for('static', filename=avatar_path) + "?t=" + str(os.path.getmtime(avatar_full_path))
    return render_template("profile.html", title="Профиль", current_user=user, avatar_url=avatar_url,
                           avatars_roundness=avatars_roundness)


@app.route("/search_person", methods=['GET', 'POST'])
@login_required
def search_person():
    session = db_session.create_session()
    if request.method == 'POST':
        user_id, surname, name, email = request.form.get('user').split()
        user = session.query(User).filter(User.id == user_id).first()
        chatting = Chat(
            title=f"{current_user.name} {current_user.surname}, {current_user.email}; "f"{name} {surname}, {email}",
            creator_id=current_user.id,
            is_public=False,
            is_group=False)
        own_chat = session.query(Chat).filter(
            Chat.is_group == False,
            Chat.is_deleted == False,
            Chat.members.contains(current_user),
            Chat.members.contains(user)).first()
        if own_chat:
            return redirect(f"/chat/{own_chat.id}")
        session.add(chatting)
        session.flush()
        chatting.members.append(user)
        chatting.members.append(session.merge(current_user))
        session.commit()
        with open(f"chats_jsons/chat_{chatting.id}.json", "w", encoding='utf-8') as chat_json:
            json.dump({}, chat_json)
        chatting.json_url = f"chat_{chatting.id}"
        session.commit()
        return redirect(f"/chat/{chatting.id}")
    query = request.args.get("p", "").strip()
    user = session.query(User).filter(User.is_deleted == False, User.email == query).first()
    if not user:
        return render_template("search_person.html", user=None, query=query, user_avatars=None)
    user_avatars = {}
    avatar_path = f"img/avatars/user_{user.id}.png"
    avatar_full_path = os.path.join(app.root_path, 'static', avatar_path)
    if os.path.exists(avatar_full_path):
        user_avatars[user.id] = (url_for('static', filename=avatar_path) +
                                 "?t=" + str(os.path.getmtime(avatar_full_path)))
    else:
        user_avatars[user.id] = None
    return render_template("search_person.html", user=user, query=query, user_avatars=user_avatars,
                           title="Поиск пользователя")


@app.route("/settings/<int:user_id>", methods=['GET', 'POST'])
@login_required
def settings(user_id):
    filename = f"users_settings/user_{user_id}_settings.json"
    dt = str(datetime.datetime.now())[:-7]
    if request.method == 'GET':
        with open(filename, 'r', encoding='utf-8') as json_file:
            settings = json.load(json_file)
        return render_template("settings.html", title="Настройки", text_size=settings['text_size'],
                               messages_roundness=settings['messages_roundness'],
                               avatars_roundness=settings["avatars_roundness"], dt=dt)
    elif request.method == 'POST':
        with open(filename, 'w', encoding='utf-8') as old_json_file:
            settings = {
                "text_size": int(request.form.get("text_size")),
                "messages_roundness": int(request.form.get("messages_roundness")),
                "avatars_roundness": int(request.form.get("avatars_roundness"))
            }
            print(request.form.get("avatars_roundness"))
            json.dump(settings, old_json_file)
        return render_template("settings.html", title="Настройки", text_size=settings['text_size'],
                               messages_roundness=settings['messages_roundness'],
                               avatars_roundness=settings["avatars_roundness"], dt=dt)


@app.route("/update_password/<int:user_id>", methods=['GET', 'POST'])
@login_required
def update_password(user_id):
    change_pw_form = ChangePasswordForm()
    if change_pw_form.validate_on_submit():
        session = db_session.create_session()
        user = session.query(User).filter(
            user_id == User.id
        ).first()
        if user.check_password(request.form.get("old_password")):
            user.hash_password(request.form.get("new_password"))
            session.merge(user)
            session.commit()
            return redirect("/profile")
        return render_template('update_password.html', title='Смена пароля', form=change_pw_form,
                               message="Введён неверный текущий пароль")
    return render_template('update_password.html', title='Смена пароля', form=change_pw_form)


if __name__ == "__main__":
    db_session.global_init("db/messenger_min.db")
    app.register_blueprint(auth.auth_bp)
    app.register_blueprint(chat.chat_bp)
    app.register_blueprint(channel.channel_bp)
    serve(app, host="127.0.0.1", port=8080, threads=32)
