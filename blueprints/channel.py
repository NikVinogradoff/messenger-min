import json
import os

from flask import render_template, request, Blueprint, Flask
from flask_login import login_required, current_user
from flask_restful import abort
from werkzeug.utils import redirect

from data import db_session
from data.chats import Chat
from data.users import User

channel_app = Flask("__main__")

channel_bp = Blueprint('channel', __name__, url_prefix='/channel')


@channel_bp.route("/search_channels", methods=["GET"])
@login_required
def search_channels():
    query = request.args.get("q", "").strip()
    session = db_session.create_session()
    user = session.merge(current_user)

    # Ищем только публичные каналы по названию
    channels = session.query(Chat).filter(
        Chat.is_public == True,
        Chat.is_deleted == False,
        Chat.is_channel == True,
        Chat.title.like(f"%{query}%"),
        ~Chat.members.contains(user)
    ).all()

    return render_template("search_channels_results.html", channels=channels, q=query,
                           title="Поиск канала")


@channel_bp.route("/create_channel", methods=["GET", "POST"])
@login_required
def create_channel():
    if request.method == "POST":
        title = request.form.get("title")
        avatar = request.files.get("avatar")
        is_public = bool(request.form.get("is_public"))
        if not title:
            return render_template("create_channel.html", error="Введите название канала",
                                   title="Создать канал")
        session = db_session.create_session()
        user = session.merge(current_user)
        chat = Chat(title=title, creator_id=user.id, is_public=is_public, is_channel=True)
        chat.members.append(user)
        if avatar and avatar.filename:
            avatars_dir = os.path.join(channel_app.static_folder, "img", "chat_avatars")
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
    return render_template("create_channel.html", title="Создать канал")


@channel_bp.route("/<int:chat_id>/make_moderator", methods=["POST"])
@login_required
def make_moderator(chat_id):
    session = db_session.create_session()
    user = session.merge(current_user)
    chat = session.query(Chat).filter(Chat.id == chat_id).first()
    if not chat or not chat.is_channel or user.id != chat.creator_id:
        abort(403)
    user_id = request.form.get("user_id", type=int)
    user = session.query(User).filter(User.id == user_id).first()
    if not user or user not in chat.members:
        abort(400)
    if user in chat.moderators:
        return redirect(f"/chat/{chat_id}")
    chat.moderators.append(user)
    session.commit()
    return redirect(f"/chat/{chat_id}")


@channel_bp.route("/<int:chat_id>/remove_moderator", methods=["POST"])
@login_required
def remove_moderator(chat_id):
    session = db_session.create_session()
    user = session.merge(current_user)
    chat = session.query(Chat).filter(Chat.id == chat_id).first()
    if not chat or not chat.is_channel or user.id != chat.creator_id:
        abort(403)

    user_id = request.form.get("user_id", type=int)
    user = session.query(User).filter(User.id == user_id).first()
    if not user or user not in chat.moderators:
        abort(400)

    chat.moderators.remove(user)
    session.commit()
    return redirect(f"/chat/{chat_id}")