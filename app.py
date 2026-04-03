from flask import Flask

from data import db_session


app = Flask(__name__)


@app.route("/")
def main():
    return "Мессенджер Min"


if __name__ == "__main__":
    db_session.global_init("db/messenger_min.db")
    app.run("127.0.0.1", 8080)