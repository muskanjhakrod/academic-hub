from flask import Flask, render_template
from flask_pymongo import PyMongo
from config import Config
from flask import session, redirect, url_for, flash
from bson.objectid import ObjectId
from dotenv import load_dotenv
load_dotenv()


app = Flask(__name__)
app.config.from_object(Config)

mongo = PyMongo(app)
app.jinja_env.globals.update(str=str)

app.jinja_env.globals['ObjectId'] = ObjectId


# create unique index for email (safe to run on startup)
try:
    mongo.db.users.create_index("email", unique=True)
except Exception:
    # index already exists or something else — ignore at startup
    pass

try:
    mongo.db.posts.create_index([("text_content", "text")])
except Exception:
    pass


from routes.auth import auth_bp
from routes.users import users_bp
from routes.posts import posts_bp
from routes.chat import chat_bp
from routes.notifications import notifications_bp
# from routes.tracks import tracks_bp

app.register_blueprint(auth_bp,url_prefix='/auth')
app.register_blueprint(users_bp,url_prefix='/users')
app.register_blueprint(posts_bp, url_prefix='/')
app.register_blueprint(notifications_bp)
app.register_blueprint(chat_bp)
# app.register_blueprint(tracks_bp, url_prefix="/tracks")



@app.route('/')
def index():
    # return render_template('index.html')
    if 'user_id' in session:
        return redirect(url_for('posts.dashboard'))
    return redirect(url_for('auth.login'))


if __name__ == "__main__":
    app.run(debug=True)

