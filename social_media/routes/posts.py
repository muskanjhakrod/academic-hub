from flask import Blueprint, render_template, session, redirect, url_for, flash, request
from app import mongo # <-- Correctly imports the Flask-PyMongo instance
from datetime import datetime
from bson.objectid import ObjectId
from functools import wraps

# 🚨 All Data Logic is imported from data_access.py 🚨
from .data_access import (
    get_user_by_username, get_posts_by_author_id, create_post, 
    get_recent_posts, get_post_by_id, update_post, get_user_by_id,
    delete_post_by_id, toggle_like, add_comment, search_users
)

posts_bp = Blueprint("posts", __name__)

# --- Decorator ---
def login_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access that page.", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return wrapped


# --- Routes (Views) ---

@posts_bp.route('/')
@login_required
def dashboard():
    """Main feed/dashboard view."""
    recent_posts = get_recent_posts(limit=20)
    # The 'author_id_str' field is now correctly in 'recent_posts'
    return render_template('dashboard.html', posts=recent_posts)

@posts_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_new_post():
    """Allows a user to create a new post."""
    if request.method == 'POST':
        content = request.form.get('content')
        
        if not content:
            flash("Post content cannot be empty!", 'danger')
            return redirect(url_for('posts.create_new_post'))

        try:
            author_id = ObjectId(session['user_id']) # Convert string ID from session to ObjectId
            post_id = create_post(author_id, content)
            flash("Post published successfully!", 'success')
            return redirect(url_for('posts.dashboard'))
        except Exception as e:
            flash(f"Error publishing post: {e}", 'danger')
            
    return render_template('post_form.html', action='Create')
    
@posts_bp.route('/edit/<post_id>', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    user_id = session['user_id']
    post = get_post_by_id(post_id) 

    if not post:
        flash("Post not found.", 'danger')
        return redirect(url_for('posts.dashboard'))

    # Compare string IDs for authorization
    if str(post['author_id']) != user_id:
        flash("You are not authorized to edit this post.", 'danger')
        return redirect(url_for('posts.dashboard'))

    if request.method == 'POST':
        new_content = request.form.get('content')
        
        if not new_content:
            flash("Post content cannot be empty!", 'danger')
            return redirect(url_for('posts.edit_post', post_id=post_id))

        if update_post(post_id, user_id, new_content):
            flash("Post updated successfully!", 'success')
            return redirect(url_for('posts.dashboard'))
        else:
            flash("Update failed. Please try again.", 'danger')
            
    return render_template('post_form.html',
                           action='Edit',
                           post=post,
                           post_id=post_id)

@posts_bp.route('/search', methods=['GET'])
@login_required
def unified_search():
    """Handles searching for both users and posts."""
    query = request.args.get('q', '').strip()
    
    if not query:
        flash("Please enter a search term.", "warning")
        return redirect(url_for('posts.dashboard'))

    # 1. Search Posts (Uses Text Index)
    raw_posts = list(mongo.db.posts.find(
        {"$text": {"$search": query}}
    ).sort([('score', {'$meta': 'textScore'})])) # Sort by relevance
    
    # 2. Enrich Posts (Add author info and string IDs)
    for post in raw_posts:
        post['author_id_str'] = str(post['author_id']) 
        post['_id_str'] = str(post['_id'])
        author_doc = mongo.db.users.find_one({"_id": post.get('author_id')}, {"username": 1})
        post['author_username'] = author_doc.get('username', 'Deleted User') if author_doc else 'Deleted User'
        
    # 3. Search Users
    found_users = search_users(query)
    
    return render_template('search_results.html', 
                           posts=raw_posts, 
                           users=found_users,
                           query=query)
    

# In routes/posts.py (Under Routes section)

@posts_bp.route('/like/<post_id>', methods=['POST'])
@login_required
def like_post(post_id):
    """Handles the user request to like or unlike a post."""
    user_id = session['user_id']
    
    # Check if the request is coming from a form/POST request
    # NOTE: We use a POST request here because GET should not be used to modify data!
    if request.method == 'POST':
        result = toggle_like(post_id, user_id)
        
        if result is True:
            flash("Insight liked!", 'success')
        elif result is False:
            flash("Insight unliked.", 'info')
        else:
            flash("Could not process like/unlike request.", 'danger')
            
    # Redirect back to the page the user came from (or dashboard if unknown)
    return redirect(request.referrer or url_for('posts.dashboard'))

# In routes/posts.py (Under Routes section)

@posts_bp.route('/comment/<post_id>', methods=['POST'])
@login_required
def post_comment(post_id):
    """Handles the form submission for adding a comment to a post."""
    user_id = session['user_id']
    comment_text = request.form.get('comment_text', '').strip()
    
    if not comment_text:
        flash("Comment cannot be empty.", 'warning')
        # Redirect back to the page the user came from
        return redirect(request.referrer or url_for('posts.dashboard')) 

    if add_comment(post_id, user_id, comment_text):
        flash("Comment posted successfully!", 'success')
    else:
        flash("Failed to post comment. Please try again.", 'danger')
        
    # Redirect back to the post/profile page
    return redirect(request.referrer or url_for('posts.dashboard'))


@posts_bp.route('/delete/<post_id>', methods=['GET','POST'])
@login_required
def delete_post(post_id):
    user_id = session['user_id']
    
    if delete_post_by_id(post_id, user_id):
        flash("Post successfully deleted.", 'success')
    else:
        flash("Error: Failed to delete post. Check permissions or ID.", 'danger')
        
    return redirect(url_for('posts.dashboard'))


@posts_bp.route('/profile/<username>')
@login_required
def user_profile(username):
    """Displays the profile page for a specific user."""
    
    profile_user = get_user_by_username(username)
    
    if not profile_user:
        flash(f"User @{username} not found.", 'danger')
        return redirect(url_for('posts.dashboard'))
    
    # Get all posts made by this user
    user_posts = get_posts_by_author_id(str(profile_user['_id']))
    
    # Determine if the currently logged-in user is viewing their own profile
    is_current_user = (session.get('user_id') == str(profile_user['_id']))
    
    return render_template('profile.html', 
                           profile=profile_user, 
                           posts=user_posts,
                           is_current_user=is_current_user)
