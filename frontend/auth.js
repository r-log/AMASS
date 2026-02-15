/**
 * Authentication Manager (Updated to use Service Layer)
 * Simplified wrapper around authService with backward compatibility
 */

class AuthManager {
  constructor() {
    this.token = null;
    this.user = null;
    this.loadStoredAuth();

    // Connect to API client once it's available
    if (window.apiClient) {
      this.setupApiClient();
    }
  }

  setupApiClient() {
    // Link apiClient with this auth manager
    window.apiClient.setAuthManager(this);
  }

  loadStoredAuth() {
    const config = window.AppConfig || {
      auth: { tokenKey: "auth_token", userDataKey: "user_data" },
    };

    // Check both localStorage and sessionStorage for token
    this.token =
      localStorage.getItem(config.auth.tokenKey) ||
      sessionStorage.getItem(config.auth.tokenKey);

    if (this.token) {
      const userData =
        localStorage.getItem(config.auth.userDataKey) ||
        sessionStorage.getItem(config.auth.userDataKey);
      if (userData) {
        try {
          this.user = JSON.parse(userData);
        } catch (e) {
          console.error("Error parsing user data:", e);
          this.clearAuth();
        }
      }
    }
  }

  isAuthenticated() {
    return !!this.token;
  }

  getToken() {
    return this.token;
  }

  getUser() {
    return this.user;
  }

  setAuth(token, user) {
    const config = window.AppConfig || {
      auth: { tokenKey: "auth_token", userDataKey: "user_data" },
    };

    this.token = token;
    this.user = user;

    // Store in localStorage for persistence
    if (token && user) {
      localStorage.setItem(config.auth.tokenKey, token);
      localStorage.setItem(config.auth.userDataKey, JSON.stringify(user));
    }

    this._notifyUserUpdate();
  }

  clearAuth() {
    const config = window.AppConfig || {
      auth: { tokenKey: "auth_token", userDataKey: "user_data" },
    };

    this.token = null;
    this.user = null;
    localStorage.removeItem(config.auth.tokenKey);
    localStorage.removeItem(config.auth.userDataKey);
    sessionStorage.removeItem(config.auth.tokenKey);
    sessionStorage.removeItem(config.auth.userDataKey);
    this._notifyUserUpdate();
  }

  /** Notify listeners that user data changed (for reactive UI updates) */
  _notifyUserUpdate() {
    if (typeof window !== "undefined" && window.dispatchEvent) {
      window.dispatchEvent(new CustomEvent("auth:user-updated", { detail: this.user }));
    }
  }

  async verifyToken() {
    if (!this.token) {
      return false;
    }

    try {
      // Use authService if available, otherwise fallback
      if (window.authService) {
        const result = await window.authService.verifyToken();
        if (result.success) {
          this.user = result.user;
          this._notifyUserUpdate();
          return true;
        }
      }
    } catch (error) {
      console.error("Token verification failed:", error);
    }

    // Token is invalid
    this.clearAuth();
    return false;
  }

  async logout() {
    try {
      // Use authService if available
      if (window.authService) {
        await window.authService.logout();
      }
    } catch (error) {
      console.error("Logout API call failed:", error);
    }

    // Clear local auth data
    this.clearAuth();

    // Redirect to login
    window.location.href = "login.html";
  }

  async makeAuthenticatedRequest(url, options = {}) {
    if (!this.token) {
      throw new Error("No authentication token available");
    }

    // Always use direct fetch to maintain backward compatibility with existing code
    // The old app code expects Response objects with .ok and .json() methods
    const headers = {
      "Content-Type": "application/json",
      Authorization: `Bearer ${this.token}`,
      ...options.headers,
    };

    const response = await fetch(url, {
      ...options,
      headers,
    });

    // Check if token is expired vs insufficient permissions
    if (response.status === 401 || response.status === 403) {
      // Try to determine if this is a permission issue or expired token
      try {
        const errorData = await response.clone().json();
        const errorMsg = (
          errorData.error ||
          errorData.message ||
          ""
        ).toLowerCase();

        // If error message indicates permission/role issue, don't log out
        if (
          errorMsg.includes("permission") ||
          errorMsg.includes("role") ||
          errorMsg.includes("supervisor") ||
          errorMsg.includes("admin") ||
          errorMsg.includes("insufficient") ||
          errorMsg.includes("forbidden")
        ) {
          console.warn("⚠️ Insufficient permissions for this action");
          // Return response so caller can handle the permission error
          return response;
        }
      } catch (e) {
        // If we can't parse error, only log out for 401, not 403
        if (response.status === 403) {
          console.warn("⚠️ Access forbidden");
          return response;
        }
      }

      // Only log out for 401 that we couldn't determine is a permission issue
      if (response.status === 401) {
        console.log("🔐 Token expired, redirecting to login");
        this.clearAuth();
        window.location.href = "login.html";
        throw new Error("Authentication expired");
      }
    }

    return response;
  }

  redirectToLogin() {
    window.location.href = "login.html";
  }

  hasRole(role) {
    return this.user && this.user.role === role;
  }

  hasAnyRole(roles) {
    return this.user && roles.includes(this.user.role);
  }

  isAdmin() {
    return this.hasRole("admin");
  }

  isSupervisor() {
    return this.hasRole("supervisor");
  }

  isWorker() {
    return this.hasRole("worker");
  }

  canManageUsers() {
    return this.isAdmin();
  }

  canDeleteAnyLog() {
    return this.hasAnyRole(["admin", "supervisor"]);
  }

  canEditAnyLog() {
    return this.hasAnyRole(["admin", "supervisor"]);
  }
}

// Global auth manager instance
const authManager = new AuthManager();

// Setup API client connection - needs to happen after both are loaded
window.addEventListener("DOMContentLoaded", () => {
  if (window.apiClient && authManager) {
    authManager.setupApiClient();
    console.log("✅ API Client linked to AuthManager");
  }
});

// Also try immediate connection if apiClient already exists
if (window.apiClient) {
  authManager.setupApiClient();
  console.log("✅ API Client linked to AuthManager (immediate)");
}

// Authentication guard function
async function requireAuth() {
  if (!authManager.isAuthenticated()) {
    console.log("No token found, redirecting to login");
    authManager.redirectToLogin();
    return false;
  }

  const isValid = await authManager.verifyToken();
  if (!isValid) {
    console.log("Token invalid, redirecting to login");
    authManager.redirectToLogin();
    return false;
  }

  return true;
}

// Helper function for checking authentication
async function checkAuth() {
  if (!authManager.isAuthenticated()) {
    return null;
  }

  const isValid = await authManager.verifyToken();
  if (!isValid) {
    return null;
  }

  return authManager.getUser();
}

// Helper function for making authenticated fetch requests
async function fetchWithAuth(url, options = {}) {
  return authManager.makeAuthenticatedRequest(url, options);
}

// Helper function for logout
function logout() {
  authManager.logout();
}

// Export for use in other files
window.authManager = authManager;
window.requireAuth = requireAuth;
window.checkAuth = checkAuth;
window.fetchWithAuth = fetchWithAuth;
window.logout = logout;
window.API_BASE =
  (window.AppConfig && window.AppConfig.api.baseUrl) ||
  "http://localhost:5000/api";

console.log("🔐 Authentication manager initialized (using service layer)");
