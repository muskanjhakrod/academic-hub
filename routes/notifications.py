from flask import Blueprint, render_template, session, redirect, url_for, flash
from app import mongo
from bson.objectid import ObjectId
from flask import jsonify


# routes/notifications.py
# ... imports ...
notifications_bp = Blueprint('notifications', __name__)

@notifications_bp.route('/api/notifications/count')
def get_unread_count():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'count': 0})
        
    count = mongo.db.notifications.count_documents({
        'user_id': ObjectId(user_id),
        'read': False
    })
    return jsonify({'count': count})

# social_media/routes/notifications.py

# ... imports ...

@notifications_bp.route('/notifications')
def list_notifications():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login'))

    try:
        # 🚨 STEP 1: MARK ALL UNREAD NOTIFICATIONS AS READ 🚨
        result = mongo.db.notifications.update_many(
            {'user_id': ObjectId(user_id), 'read': False},
            {'$set': {'read': True}}
        )
        print(f"DEBUG: Marked {result.modified_count} notifications as read for user {user_id}")

        # STEP 2: Fetch the list (now mostly read)
        notifications = list(mongo.db.notifications.find({'user_id': ObjectId(user_id)})
                             .sort('timestamp', -1))
        
        # STEP 3: Render the template
        return render_template('notifications.html', notifications=notifications)
        
    except Exception as e:
        print(f"Error listing and updating notifications: {e}")
        return render_template('notifications.html', notifications=[], error="Could not load notifications.")