import datetime
import json
import os

from flask import render_template, request, url_for, Blueprint, Flask
from flask_login import login_required, current_user
from flask_restful import abort
from werkzeug.utils import redirect, secure_filename

from data import db_session
from data.chats import Chat
from data.users import User

chat_app = Flask("__main__")

chat_bp = Blueprint('chat', __name__, url_prefix='/chat')


@chat_bp.route("/<int:chat_id>", methods=['GET', 'POST'])
@login_required
def chat(chat_id):
    session = db_session.create_session()
    user = session.merge(current_user)
    chatting = session.query(Chat).filter(Chat.id == chat_id).first()
    if not chatting or (not chatting.is_public and user not in chatting.members):
        abort(403)
    with open(f"users_settings/user_{user.id}_settings.json", 'r', encoding='utf-8') as style_json:
        style_values = json.load(style_json)
        text_size = style_values["text_size"]
        mess_roundness = style_values["messages_roundness"]
        avatars_roundness = style_values["avatars_roundness"]
    moderated_chats_id = list(map(lambda x: int(str(x).split()[1]), user.moderated_chats))
    can_send = not chatting.is_channel or user.id == chatting.creator_id or chatting.id in moderated_chats_id
    filename = f"chats_jsons/{chatting.json_url}.json"
    with open(filename, "r", encoding='utf-8') as json_file:
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
                                           text_size=text_size, messages_roundness=mess_roundness,
                                           avatars_roundness=avatars_roundness,
                                           message_error="Разрешены только: PNG, JPG, JPEG, GIF, TXT, MP4")
                chat_files_dir = os.path.join(chat_app.static_folder, "chat_files", str(chatting.id))
                os.makedirs(chat_files_dir, exist_ok=True)
                safe_filename = secure_filename(file.filename)
                filepath = os.path.join(chat_files_dir, safe_filename)
                file.save(filepath)
                file_url = url_for('static', filename=f"chat_files/{chatting.id}/{safe_filename}")
        with open(filename, "w", encoding='utf-8') as old_json:
            message_key = f'message_{len(messages.keys()) + 1}'
            messages[message_key] = {
                "author_id": user.id,
                "author_name": f"{user.name} {user.surname}",
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
        avatar_full_path = os.path.join(chat_app.root_path, 'static', avatar_path)
        if os.path.exists(avatar_full_path):
            user_avatars[member.id] = (url_for('static', filename=avatar_path) +
                                       "?t=" + str(os.path.getmtime(avatar_full_path)))
        else:
            user_avatars[member.id] = None
    return render_template("chat.html", title=chatting.title, messages=messages, chatting=chatting,
                           user_avatars=user_avatars, user=current_user, can_send=can_send,
                           text_size=text_size, messages_roundness=mess_roundness, avatars_roundness=avatars_roundness)


@chat_bp.route("/create_chat", methods=["GET", "POST"])
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
        chat = Chat(title=title, creator_id=user.id, is_public=is_public, is_channel=False)
        chat.members.append(user)
        if avatar and avatar.filename:
            avatars_dir = os.path.join(chat_app.static_folder, "img", "chat_avatars")
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
        with open(f"chats_jsons/chat_{chat.id}.json", "w", encoding='utf-8') as chat_json:
            json.dump({}, chat_json)
        chat.json_url = f"chat_{chat.id}"
        session.commit()
        return redirect("/main_page")
    return render_template("create_chat.html", title="Создать чат")

@chat_bp.route("/confirm_delete/<int:chat_id>")
@login_required
def confirm_delete(chat_id):
    session = db_session.create_session()
    user = session.merge(current_user)
    chat = session.get(Chat, chat_id)
    if not chat or user not in chat.members or chat.creator_id != user.id:
        abort(404)
    return render_template("confirm_delete.html", chat=chat, title="Подтверждение удаления")


@chat_bp.route("/delete_chat/<int:chat_id>", methods=["POST"])
@login_required
def delete_chat(chat_id):
    session = db_session.create_session()
    user = session.merge(current_user)
    chat = session.get(Chat, chat_id)
    if not chat or chat.creator_id != user.id:
        abort(403)
    chat.is_deleted = True
    session.commit()
    return redirect("/main_page")


@chat_bp.route("/<int:chat_id>/add_user", methods=["GET", "POST"])
@login_required
def add_user_to_chat(chat_id):
    session = db_session.create_session()
    user = session.merge(current_user)
    chat = session.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        abort(404)
    if user not in chat.members:
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
    return render_template("add_user.html", chat=chat, error=error, title="Добавление пользователя")


@chat_bp.route("/<int:chat_id>/leave", methods=["POST"])
@login_required
def leave_chat(chat_id):
    session = db_session.create_session()
    user = session.merge(current_user)
    chat = session.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        abort(404)
    if user not in chat.members:
        abort(403)
    chat.members.remove(user)
    session.commit()
    if len(chat.members) == 0:
        chat.is_deleted = True
    return redirect("/main_page")


@chat_bp.route("/confirm_leave_chat/<int:chat_id>")
@login_required
def confirm_leave_chat(chat_id):
    session = db_session.create_session()
    user = session.merge(current_user)
    chat = session.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        abort(404)
    if user not in chat.members:
        abort(403)
    if chat_id in user.moderated_chats:
        user.moderated_chats.remove(chat_id)
    return render_template("confirm_leave_chat.html", chat=chat, title="Подтверждение выхода")


@chat_bp.route("/<int:chat_id>/remove_user/<int:user_id>", methods=["POST"])
@login_required
def remove_user_from_chat(chat_id, user_id):
    session = db_session.create_session()
    user = session.merge(current_user)
    chat = session.query(Chat).filter(Chat.id == chat_id).first()
    user_to_remove = session.query(User).filter(User.id == user_id).first()
    if not chat or not user_to_remove:
        abort(404)
    if user.id != chat.creator_id:
        abort(403)
    if user.id == user_to_remove.id:
        abort(400, description="Нельзя выгнать самого себя. Используйте 'Выйти из чата'.")
    if user_to_remove not in chat.members:
        abort(400, description="Пользователь не состоит в этом чате.")
    chat.members.remove(user_to_remove)
    session.commit()
    return redirect(f"/chat/{chat_id}")


@chat_bp.route("/<int:chat_id>/members")
@login_required
def chat_members(chat_id):
    session = db_session.create_session()
    user = session.merge(current_user)
    chat = session.query(Chat).filter(Chat.id == chat_id).first()

    if not chat:
        abort(404)
    if user not in chat.members:
        abort(403)

    with open(f'users_settings/user_{user.id}_settings.json', 'r', encoding='utf-8') as settings_json:
        avatars_roundness = int(json.load(settings_json)["avatars_roundness"])

    return render_template("chat_members.html", chat=chat, title="Участники чата",
                           avatars_roundness=avatars_roundness)


@chat_bp.route("/join_public_chat/<int:chat_id>", methods=["POST"])
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


@chat_bp.route("/<int:chat_id>/confirm_remove/<int:user_id>")
@login_required
def confirm_remove_user(chat_id, user_id):
    session = db_session.create_session()
    user = session.merge(current_user)
    chat = session.query(Chat).filter(Chat.id == chat_id).first()
    user_to_remove = session.query(User).filter(User.id == user_id).first()

    if not chat or not user_to_remove:
        abort(404)
    if user.id != chat.creator_id:
        abort(403)
    if chat_id in user_to_remove.moderated_chats:
        user_to_remove.moderated_chats.remove(chat_id)

    return render_template("confirm_remove_user.html", chat=chat, user=user_to_remove,
                           title="Подтверждение удаления")


@chat_bp.route("/<int:chat_id>/edit", methods=["GET", "POST"])
@login_required
def edit_chat(chat_id):
    session = db_session.create_session()
    user = session.merge(current_user)
    chat = session.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        abort(404)
    if user.id != chat.creator_id:
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
                avatars_dir = os.path.join(chat_app.static_folder, "img", "chat_avatars")
                os.makedirs(avatars_dir, exist_ok=True)
                filename = f"chat_{chat.id}.png"
                filepath = os.path.join(avatars_dir, filename)
                if os.path.exists(filepath):
                    os.remove(filepath)
                avatar.save(filepath)
                chat.avatar_url = f"img/chat_avatars/{filename}"

            session.commit()
            return redirect(f"/chat/{chat_id}")

    return render_template("edit_chat.html", chat=chat, error=error, title="Редактирование чата")


@chat_bp.route("/search_chats", methods=["GET"])
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

    return render_template("search_results.html", chats=chats, query=query, title="Поиск чата")


@chat_bp.route("/<int:chat_id>/edit/<message_key>", methods=["POST"])
@login_required
def edit_message(chat_id, message_key):
    session = db_session.create_session()
    user = session.merge(current_user)
    chatting = session.query(Chat).filter(Chat.id == chat_id).first()
    if not chatting or user not in chatting.members:
        abort(403)
    filename = f"chats_jsons/{chatting.json_url}.json"
    with open(filename, "r", encoding='utf-8') as json_file:
        messages = json.load(json_file)
    if message_key not in messages:
        abort(404)
    if messages[message_key]["author_id"] != user.id:
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
    with open(filename, "w", encoding='utf-8') as f:
        json.dump(messages, f)
    return redirect(f"/chat/{chat_id}")


@chat_bp.route("/<int:chat_id>/delete/<message_key>", methods=["POST"])
@login_required
def delete_message(chat_id, message_key):
    session = db_session.create_session()
    user = session.merge(current_user)
    chatting = session.query(Chat).filter(Chat.id == chat_id).first()
    if not chatting or user not in chatting.members:
        abort(403)
    filename = f"chats_jsons/{chatting.json_url}.json"
    with open(filename, "r", encoding='utf-8') as json_file:
        messages = json.load(json_file)
    if message_key not in messages:
        abort(404)
    if messages[message_key]["author_id"] != user.id and user.id != chatting.creator_id:
        abort(403)
    del messages[message_key]
    with open(filename, "w", encoding='utf-8') as f:
        json.dump(messages, f)
    return redirect(f"/chat/{chat_id}")


@chat_bp.route("/<int:chat_id>/give_creator", methods=["POST"])
@login_required
def give_creator(chat_id):
    session = db_session.create_session()
    user = session.merge(current_user)
    chat = session.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        abort(404)
    if user.id != chat.creator_id:
        abort(403)
    new_creator_id = request.form.get("user_id", type=int)
    if not new_creator_id:
        abort(400)
    new_creator = session.query(User).filter(User.id == new_creator_id).first()
    if not new_creator or new_creator not in chat.members:
        abort(400, description="Пользователь не найден или не состоит в чате.")
    chat.creator_id = new_creator.id
    session.commit()

    return redirect(f"/chat/{chat_id}")
