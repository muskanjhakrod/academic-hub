from flask import Blueprint, render_template, session, redirect, url_for, flash, request
from app import mongo # <-- Correctly imports the Flask-PyMongo instance
from datetime import datetime
from bson.objectid import ObjectId
from functools import wraps
from typing import List, Optional, Dict, Any


# --- CRUD Functions (Data Layer) ---

def get_user_by_id(user_id_str):
    """Retrieves a user document by its string ID."""
    try:
        return mongo.db.users.find_one({"_id": ObjectId(user_id_str)}, {"password": 0})
    except Exception:
        return None

# for profile viewing
def get_user_by_username(username):
    """Retrieves a user document by username (for profile viewing)."""
    # Exclude the hashed password for safety
    return mongo.db.users.find_one({"username": username}, {"password": 0})

# In routes/posts.py
def get_posts_by_author_id(author_id_str):
    """Retrieves all posts for a specific author, ordered newest first."""
    
    # 🚨 SAFETY CHECK: Ensure the string can be converted to ObjectId 🚨
    try:
        author_id = ObjectId(author_id_str)
    except Exception:
        # If the string ID is invalid, return empty list immediately
        return []
        
    posts = list(mongo.db.posts.find({"author_id": author_id}).sort("timestamp", -1))
    
    # Enrich posts with string IDs (Crucial for Edit/Delete links)
    for post in posts:
        # We need to ensure the _id keys actually exist before casting to str
        if post.get('_id'):
            post['_id_str'] = str(post['_id'])
        else:
            post['_id_str'] = '' # Failsafe
            
        if post.get('author_id'):
            post['author_id_str'] = str(post['author_id'])
        else:
            post['author_id_str'] = '' # Failsafe
    
    return posts

def update_user_profile(user_id_str: str, updates: Dict[str, Any]) -> bool:
    """Updates a user's profile information (bio, profession, tags)."""
    try:
        user_id = ObjectId(user_id_str)
        
        # Process tags field (Converts comma-separated string to a list of strings)
        if 'tags' in updates and updates['tags']:
            # Strip spaces from each tag and filter out empty strings
            tags_list = [tag.strip() for tag in updates['tags'].split(',') if tag.strip()]
            updates['tags'] = tags_list
        else:
            # If tags field is empty, ensure the array is cleared in the database
            updates['tags'] = []
            
        # Clean up the dictionary: only include fields with actual non-None values
        updates = {k: v for k, v in updates.items() if v is not None and k not in ['username', 'email']}
        
        result = mongo.db.users.update_one(
            {"_id": user_id},
            {"$set": updates}
        )
        return result.modified_count > 0
    except Exception as e:
        print(f"Error updating user profile: {e}")
        return False

def create_post(author_id, text_content, image_url=None):
    """Creates a new post."""
    post_data = {
        "author_id": author_id, # This is an ObjectId
        "text_content": text_content,
        "image_url": image_url,
        "timestamp": datetime.now(),
        "likes": [],
        "comments": []
    }
    result = mongo.db.posts.insert_one(post_data)
    return result.inserted_id

def get_recent_posts(limit=20):
    """Retrieves posts, enriches them with author username and string IDs."""
    posts = list(mongo.db.posts.find().sort("timestamp", -1).limit(limit))
    
    for post in posts:
        # 🚨 FIX 1: Convert IDs to string for template comparison and URLs
        post['author_id_str'] = str(post['author_id']) 
        post['_id_str'] = str(post['_id'])
        
        # Enrich posts with author username
        author_doc = mongo.db.users.find_one(
            {"_id": post.get('author_id')}, 
            {"username": 1}
        )
        post['author_username'] = author_doc.get('username', 'Deleted User') if author_doc else 'Deleted User'
            
    return posts

def get_post_by_id(post_id_str):
    """Retrieves a single post document by its ID."""
    try:
        return mongo.db.posts.find_one({"_id": ObjectId(post_id_str)})
    except Exception:
        return None

# routes/posts.py (under CRUD Functions section)

def search_users(query):
    """Searches for users whose username starts with the query string (case-insensitive)."""
    # Use $regex for partial, case-insensitive match (faster on indexed fields)
    regex_query = {"$regex": f"^{query}", "$options": "i"}
    
    users = list(mongo.db.users.find(
        {"username": regex_query},
        {"username": 1, "created_at": 1, "email": 1}
    ).limit(10)) 
    
    
    
    return users

        
def update_post(post_id_str, user_id_str, new_content):
    """Updates the content of a post if the user is the author."""
    try:
        post_id = ObjectId(post_id_str)
        author_id = ObjectId(user_id_str)
        
        result = mongo.db.posts.update_one(
            {
                "_id": post_id,
                "author_id": author_id
            },
            {
                "$set": {
                    "text_content": new_content,
                    "updated_at": datetime.now()
                }
            }
        )
        return result.modified_count > 0
    except Exception as e:
        print(f"Error updating post: {e}")
        return False

def delete_post_by_id(post_id_str, user_id_str):
    """Deletes a post document if the user is the author."""
    try:
        post_id = ObjectId(post_id_str)
        author_id = ObjectId(user_id_str)
        
        # Security: Delete only if the _id and author_id match
        result = mongo.db.posts.delete_one({
            "_id": post_id,
            "author_id": author_id 
        })
        return result.deleted_count > 0
    except Exception as e:
        print(f"Error deleting post: {e}")
        return False


# In routes/posts.py (Under CRUD Functions)

def toggle_like(post_id_str, user_id_str):
    """
    Adds or removes a user's ID from the post's 'likes' array.
    Returns True if a like was added, False if a like was removed.
    """
    try:
        post_id = ObjectId(post_id_str)
        user_id = ObjectId(user_id_str)
        
        # 1. Check if the user has already liked the post
        post = mongo.db.posts.find_one({"_id": post_id, "likes": user_id})

        if post:
            # User has already liked it -> UNLIKE (pull the user ID from the array)
            mongo.db.posts.update_one(
                {"_id": post_id},
                {"$pull": {"likes": user_id}}
            )
            return False # Indicate Unlike
        else:
            # User has not liked it -> LIKE (add the user ID to the set)
            # $addToSet prevents duplicate user IDs in the array
            mongo.db.posts.update_one(
                {"_id": post_id},
                {"$addToSet": {"likes": user_id}}
            )
            return True # Indicate Like
            
    except Exception as e:
        print(f"Error toggling like: {e}")
        return None # Indicate failure
    

# In routes/posts.py (Under CRUD Functions)

def insert_comment_to_db(post_id_str, user_id_str, comment_text):
    """Adds an embedded comment document to the post's comments array."""
    try:
        post_id = ObjectId(post_id_str)
        user_id = ObjectId(user_id_str)
        
        # 1. Look up the author's username for display in the comment feed
        user = mongo.db.users.find_one({"_id": user_id}, {"username": 1})
        if not user:
            return None 

        # 2. Create the embedded comment document
        comment_doc = {
            "comment_id": ObjectId(), # Unique ID for the comment (useful for deletion later)
            "author_id": user_id,
            "username": user['username'],
            "text": comment_text,
            "timestamp": datetime.utcnow()
        }
        
        # 3. Use $push to add the document to the post's 'comments' array
        result = mongo.db.posts.update_one(
            {"_id": post_id},
            {"$push": {"comments": comment_doc}}
        )
        return result.modified_count > 0
        
    except Exception as e:
        print(f"Error adding comment: {e}")
        return None

def create_notification(user_to_notify_id, sender_id, post_id, notif_type, message):
    # This function inserts a document into your 'notifications' collection
    try:
        if not user_to_notify_id or not sender_id:
            print("---FATAL NOTIF DEBUG: Missing Recipient or Sender ID. Insertion aborted.---")
            return
        notification_doc = {
            'user_id': ObjectId(user_to_notify_id),  # Recipient (Muskan)
            'sender_id': ObjectId(sender_id),        # Sender (Tina)
            'post_id': ObjectId(post_id),            # Post ID
            'type': notif_type,
            'message': message,
            'read': False,
            'timestamp': datetime.utcnow()
        }
        
        mongo.db.notifications.insert_one(notification_doc)
        print("---SUCCESS: Notification inserted---")
    except Exception as e:
        # 🚨 THIS WILL CATCH ERRORS LIKE InvalidId or Database Connection Issues 🚨
        print(f"---FATAL DB ERROR: Could not insert notification: {e}")
    
