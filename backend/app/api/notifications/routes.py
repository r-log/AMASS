"""
Notifications API routes.
"""

from flask import Blueprint, request, jsonify
from app.services.notification_service import NotificationService
from app.utils.decorators import token_required

notifications_bp = Blueprint('notifications', __name__)


@notifications_bp.route('/', methods=['GET'])
@token_required
def get_notifications():
    """Get notifications for the current user."""
    try:
        user_id = request.current_user.get('user_id')

        # Query parameters
        unread_only = request.args.get(
            'unread_only', 'false').lower() == 'true'
        limit = request.args.get('limit', 50, type=int)
        notification_type = request.args.get('type')

        notifications = NotificationService.get_user_notifications(
            user_id=user_id,
            unread_only=unread_only,
            limit=limit
        )

        return jsonify([notif.to_dict() for notif in notifications]), 200

    except Exception as e:
        return jsonify({'error': f'Failed to get notifications: {str(e)}'}), 500


@notifications_bp.route('/<int:notification_id>', methods=['GET'])
@token_required
def get_notification(notification_id):
    """Get a specific notification by ID."""
    try:
        from app.models.notification import Notification

        notification = Notification.find_by_id(notification_id)

        if not notification:
            return jsonify({'error': 'Notification not found'}), 404

        # Check permissions: users can only view their own notifications
        user_id = request.current_user.get('user_id')
        if notification.user_id != user_id:
            return jsonify({'error': 'Access denied'}), 403

        return jsonify(notification.to_dict()), 200

    except Exception as e:
        return jsonify({'error': f'Failed to get notification: {str(e)}'}), 500


@notifications_bp.route('/<int:notification_id>/read', methods=['PUT'])
@token_required
def mark_notification_read(notification_id):
    """Mark a notification as read."""
    try:
        user_id = request.current_user.get('user_id')
        success, message = NotificationService.mark_notification_as_read(
            notification_id, user_id)

        if success:
            return jsonify({'message': message}), 200
        else:
            return jsonify({'error': message}), 400

    except Exception as e:
        return jsonify({'error': f'Failed to mark notification as read: {str(e)}'}), 500


@notifications_bp.route('/read-all', methods=['PUT'])
@token_required
def mark_all_notifications_read():
    """Mark all notifications as read for the current user."""
    try:
        user_id = request.current_user.get('user_id')
        success, message = NotificationService.mark_all_user_notifications_as_read(
            user_id)

        if success:
            return jsonify({'message': message}), 200
        else:
            return jsonify({'error': message}), 400

    except Exception as e:
        return jsonify({'error': f'Failed to mark all as read: {str(e)}'}), 500


@notifications_bp.route('/<int:notification_id>', methods=['DELETE'])
@token_required
def delete_notification(notification_id):
    """Delete a notification."""
    try:
        user_id = request.current_user.get('user_id')
        success, message = NotificationService.delete_notification(
            notification_id, user_id)

        if success:
            return jsonify({'message': message}), 200
        else:
            return jsonify({'error': message}), 400

    except Exception as e:
        return jsonify({'error': f'Failed to delete notification: {str(e)}'}), 500


@notifications_bp.route('/clear-all', methods=['DELETE'])
@token_required
def clear_all_notifications():
    """Clear all notifications for the current user."""
    try:
        user_id = request.current_user.get('user_id')
        # Delete all notifications for the user
        notifications = NotificationService.get_user_notifications(
            user_id, limit=1000)
        deleted_count = 0
        for notif in notifications:
            success, _ = NotificationService.delete_notification(
                notif.id, user_id)
            if success:
                deleted_count += 1

        return jsonify({'message': f'Cleared {deleted_count} notifications'}), 200

    except Exception as e:
        return jsonify({'error': f'Failed to clear notifications: {str(e)}'}), 500


@notifications_bp.route('/unread-count', methods=['GET'])
@token_required
def get_unread_count():
    """Get count of unread notifications."""
    try:
        user_id = request.current_user.get('user_id')
        count = NotificationService.get_unread_count(user_id)

        return jsonify({'count': count}), 200

    except Exception as e:
        return jsonify({'error': f'Failed to get unread count: {str(e)}'}), 500


@notifications_bp.route('/by-type/<notification_type>', methods=['GET'])
@token_required
def get_notifications_by_type(notification_type):
    """Get notifications by type for the current user."""
    try:
        user_id = request.current_user.get('user_id')
        limit = request.args.get('limit', 50, type=int)

        # Filter notifications by type
        all_notifications = NotificationService.get_user_notifications(
            user_id, limit=limit)
        filtered = [n for n in all_notifications if n.type ==
                    notification_type]

        return jsonify([notif.to_dict() for notif in filtered]), 200

    except Exception as e:
        return jsonify({'error': f'Failed to get notifications by type: {str(e)}'}), 500


@notifications_bp.route('/recent', methods=['GET'])
@token_required
def get_recent_notifications():
    """Get recent notifications for the current user."""
    try:
        user_id = request.current_user.get('user_id')
        hours = request.args.get('hours', 24, type=int)

        # Get all notifications and filter by recency
        all_notifications = NotificationService.get_user_notifications(
            user_id, limit=100)
        recent = [n for n in all_notifications if n.is_recent(hours)]

        return jsonify([notif.to_dict() for notif in recent]), 200

    except Exception as e:
        return jsonify({'error': f'Failed to get recent notifications: {str(e)}'}), 500


@notifications_bp.route('/statistics', methods=['GET'])
@token_required
def get_notification_statistics():
    """Get notification statistics for the current user."""
    try:
        user_id = request.current_user.get('user_id')
        stats = NotificationService.get_notification_statistics(user_id)

        return jsonify(stats), 200

    except Exception as e:
        return jsonify({'error': f'Failed to get statistics: {str(e)}'}), 500
