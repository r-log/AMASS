/**
 * Notifications Service
 * Handles notification-related API calls
 */

class NotificationsService {
  constructor(apiClient) {
    this.client = apiClient;
  }

  async getAll(params = {}) {
    try {
      const response = await this.client.get("/notifications", params);
      // Normalize: API may return array directly or wrapped in { data }
      if (Array.isArray(response)) return response;
      if (response?.data && Array.isArray(response.data)) return response.data;
      if (response?.notifications && Array.isArray(response.notifications)) return response.notifications;
      return [];
    } catch (error) {
      console.error("❌ Failed to fetch notifications:", error.message);
      throw error;
    }
  }

  async getById(notificationId) {
    try {
      const response = await this.client.get(`/notifications/${notificationId}`);
      return response;
    } catch (error) {
      console.error(`❌ Failed to fetch notification ${notificationId}:`, error.message);
      throw error;
    }
  }

  async markAsRead(notificationId) {
    try {
      await this.client.put(`/notifications/${notificationId}/read`);
    } catch (error) {
      console.error(`❌ Failed to mark notification ${notificationId} as read:`, error.message);
      throw error;
    }
  }

  async markAllAsRead() {
    try {
      await this.client.put("/notifications/read-all");
    } catch (error) {
      console.error("❌ Failed to mark all notifications as read:", error.message);
      throw error;
    }
  }

  async delete(notificationId) {
    try {
      await this.client.delete(`/notifications/${notificationId}`);
    } catch (error) {
      console.error(`❌ Failed to delete notification ${notificationId}:`, error.message);
      throw error;
    }
  }
}

const notificationsService = new NotificationsService(window.apiClient || apiClient);

if (typeof window !== "undefined") {
  window.NotificationsService = NotificationsService;
  window.notificationsService = notificationsService;
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { NotificationsService, notificationsService };
}
