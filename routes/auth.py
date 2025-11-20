from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from werkzeug.security import generate_password_hash, check_password_hash
from app import mongo
from datetime import datetime

auth_bp = Blueprint('auth',__name__)

@auth_bp.route('/register', methods = ['GET', 'POST'])
def register():
    if request.method == "POST":
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm  = request.form.get('confirm')
        
        if not name or not email or not password or not confirm:
            flash("Please fill out all fields", "danger")
            return render_template('auth/register.html', name=name, email=email)
        
        if password != confirm:
            flash("passwords do to match","warning")
            return render_template('auth/register.html', name=name, email=email)
        
        # check existing email
        if mongo.db.users.find_one({"email": email}):
            flash("Email already registered. Try logging in.", "warning")
            return render_template('auth/register.html', name=name, email=email)
        
        if email[0].isdigit():
            flash("Email is not valid", "warning")
            return render_template('auth/register.html', name=name, email=email)
        
        if mongo.db.users.find_one({"username": name}):
            flash("username is already there make unique username", "warning")
            return render_template('auth/register.html', name=name, email=email)

        pass_hash = generate_password_hash(password)
        user_doc = {
            "username": name,
            "email": email,
            "password": pass_hash,
            "created_at": datetime.utcnow()
        }
        
        
        result = mongo.db.users.insert_one(user_doc)
        session['user_id'] = str(result.inserted_id)
        session['username'] = name
        flash("Registration successful. You are now logged in.", "success")
        return redirect(url_for('posts.dashboard'))
    return render_template('auth/register.html')
        
@auth_bp.route('/login',methods = ['GET', 'POST'])
def login():
    if request.method == "POST":
        # email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash("Please fill out all fields", "danger")
            return render_template('auth/login.html')
        
        user = mongo.db.users.find_one({'username': username})
        if user and check_password_hash(user['password'], password):
            session['user_id'] = str(user['_id'])
            session['username'] = user['username']
            flash("Login successful", "success")
            return redirect(url_for('posts.dashboard'))
        else:
            flash("Invalid email or password", "danger")
            return render_template('auth/login.html',username = username)
    return render_template('auth/login.html')

@auth_bp.route("/logout")
def logout():
    session.pop("user_id", None)
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))