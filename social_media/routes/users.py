from flask import Blueprint, render_template, session, redirect, url_for, flash
from app import mongo

users_bp = Blueprint("users", __name__)

# simple login_required decorator
from functools import wraps
def login_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access that page.", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return wrapped

# @users_bp.route("/")
# @login_required
# def list_users():
#     # find all users, exclude password when showing
#     users_cursor = mongo.db.users.find({}, {"password": 0})
#     users = list(users_cursor)
#     return render_template("users/list.html", users=users)

# --- The list_users Function and Route ---
@users_bp.route('/')
@login_required
def list_users():
    """
    Fetches and displays a list of all registered users, excluding the current user.
    This function renders the 'users/list.html' template.
    """
    current_user_id = session.get('user_id')
    
    try:
        # Use $ne (not equal) to exclude the currently logged-in user from the directory
        users = list(mongo.db.users.find(
            {"_id": {"$ne": ObjectId(current_user_id)}},
            # Fetch all required fields for the user list table (username, email, created_at)
            {"password": 0, "username": 1, "email": 1, "created_at": 1} 
        ))
    except Exception as e:
        # Log the error if the ID conversion fails or database access fails
        print(f"Error fetching user list: {e}")
        users = []
        
    # CRITICAL FIX: Ensures the correct template 'users/list.html' is rendered 
    return render_template('users/list.html', users=users)