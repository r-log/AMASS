/**
 * Authentication Service
 * Handles authentication-related API calls
 */

class AuthService {
  constructor(apiClient) {
    this.client = apiClient;
  }

  /**
   * Login user
   */
  async login(username, password) {
    try {
      const response = await this.client.post("/auth/login", {
        username,
        password,
      });

      console.log("✅ Login successful:", response.user?.username);

      return {
        success: true,
        token: response.token,
        user: response.user,
      };
    } catch (error) {
      console.error("❌ Login failed:", error.message);
      throw error;
    }
  }

  /**
   * Register new user
   */
  async register(userData) {
    try {
      const response = await this.client.post("/auth/register", userData);

      console.log("✅ Registration successful:", response.user?.username);

      return {
        success: true,
        token: response.token,
        user: response.user,
      };
    } catch (error) {
      console.error("❌ Registration failed:", error.message);
      throw error;
    }
  }

  /**
   * Verify authentication token
   */
  async verifyToken() {
    try {
      const response = await this.client.get("/auth/verify");

      return {
        success: response.success || false,
        user: response.user,
      };
    } catch (error) {
      console.error("❌ Token verification failed:", error.message);
      return {
        success: false,
        user: null,
      };
    }
  }

  /**
   * Logout user
   */
  async logout() {
    try {
      await this.client.post("/auth/logout");
      console.log("✅ Logout successful");
      return { success: true };
    } catch (error) {
      console.error("⚠️ Logout API call failed:", error.message);
      // Still return success since local logout can proceed
      return { success: true };
    }
  }

  /**
   * Change password
   */
  async changePassword(oldPassword, newPassword) {
    try {
      const response = await this.client.post("/auth/change-password", {
        old_password: oldPassword,
        new_password: newPassword,
      });

      console.log("✅ Password changed successfully");

      return {
        success: true,
        message: response.message,
      };
    } catch (error) {
      console.error("❌ Password change failed:", error.message);
      throw error;
    }
  }

  /**
   * Request password reset
   */
  async requestPasswordReset(email) {
    try {
      const response = await this.client.post("/auth/reset-password", {
        email,
      });

      console.log("✅ Password reset requested");

      return {
        success: true,
        message: response.message,
      };
    } catch (error) {
      console.error("❌ Password reset request failed:", error.message);
      throw error;
    }
  }

  /**
   * Get current user profile
   */
  async getUserProfile() {
    try {
      const response = await this.client.get("/auth/profile");

      return {
        success: true,
        user: response.user,
      };
    } catch (error) {
      console.error("❌ Failed to get user profile:", error.message);
      throw error;
    }
  }

  /**
   * Update user profile
   */
  async updateProfile(profileData) {
    try {
      const response = await this.client.put("/auth/profile", profileData);

      console.log("✅ Profile updated successfully");

      return {
        success: true,
        user: response.user,
      };
    } catch (error) {
      console.error("❌ Profile update failed:", error.message);
      throw error;
    }
  }
}

// Create global instance
const authService = new AuthService(window.apiClient || apiClient);

// Export for use in other modules
if (typeof module !== "undefined" && module.exports) {
  module.exports = { AuthService, authService };
}

if (typeof window !== "undefined") {
  window.AuthService = AuthService;
  window.authService = authService;
}

console.log("🔐 Authentication service initialized");
