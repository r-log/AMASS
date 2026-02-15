/**
 * API Client - Base HTTP client with authentication
 * Handles all API communication with automatic token injection and error handling
 */

class ApiClient {
  constructor(config) {
    this.baseUrl = config.api.baseUrl;
    this.timeout = config.api.timeout;
    this.retryAttempts = config.api.retryAttempts;
    this.retryDelay = config.api.retryDelay;
    this.authManager = null;
  }

  /**
   * Set authentication manager
   */
  setAuthManager(authManager) {
    this.authManager = authManager;
  }

  /**
   * Build full URL
   */
  buildUrl(endpoint) {
    // Remove leading slash if present
    const cleanEndpoint = endpoint.startsWith("/")
      ? endpoint.slice(1)
      : endpoint;
    return `${this.baseUrl}/${cleanEndpoint}`;
  }

  /**
   * Build headers with authentication
   */
  buildHeaders(customHeaders = {}) {
    const headers = {
      "Content-Type": "application/json",
      ...customHeaders,
    };

    // Add authentication token if available
    if (this.authManager && this.authManager.getToken()) {
      headers["Authorization"] = `Bearer ${this.authManager.getToken()}`;
    }

    return headers;
  }

  /**
   * Handle HTTP errors
   */
  async handleResponse(response) {
    // Check for authentication errors
    if (response.status === 401) {
      console.error("🔒 Authentication failed or token expired");

      if (this.authManager) {
        this.authManager.clearAuth();
        // Redirect to login
        if (typeof window !== "undefined") {
          window.location.href = "login.html";
        }
      }

      throw new ApiError("Authentication required", 401, {
        message: "Your session has expired. Please log in again.",
      });
    }

    // Check for other error status codes
    if (!response.ok) {
      let errorData;
      try {
        errorData = await response.json();
      } catch (e) {
        errorData = { message: response.statusText };
      }

      throw new ApiError(
        errorData.error || errorData.message || "Request failed",
        response.status,
        errorData
      );
    }

    // Parse successful response
    try {
      return await response.json();
    } catch (e) {
      // If response is not JSON, return empty object
      return {};
    }
  }

  /**
   * Generic request method with retry logic
   */
  async request(endpoint, options = {}, retryCount = 0) {
    const url = this.buildUrl(endpoint);
    const headers = this.buildHeaders(options.headers);

    try {
      // Create abort controller for timeout
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), this.timeout);

      const response = await fetch(url, {
        ...options,
        headers,
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      return await this.handleResponse(response);
    } catch (error) {
      // Handle abort/timeout
      if (error.name === "AbortError") {
        console.error(`⏱️ Request timeout: ${endpoint}`);
        throw new ApiError("Request timeout", 408, { endpoint });
      }

      // Retry logic for network errors
      if (retryCount < this.retryAttempts && this.shouldRetry(error)) {
        console.warn(
          `🔄 Retrying request (${retryCount + 1}/${
            this.retryAttempts
          }): ${endpoint}`
        );
        await this.delay(this.retryDelay * (retryCount + 1));
        return this.request(endpoint, options, retryCount + 1);
      }

      // Re-throw API errors
      if (error instanceof ApiError) {
        throw error;
      }

      // Wrap network errors
      console.error(`❌ API request failed: ${endpoint}`, error);
      throw new ApiError("Network error", 0, {
        message: error.message,
        endpoint,
      });
    }
  }

  /**
   * Determine if request should be retried
   */
  shouldRetry(error) {
    // Don't retry on 4xx errors (client errors)
    if (
      error instanceof ApiError &&
      error.status >= 400 &&
      error.status < 500
    ) {
      return false;
    }

    // Retry on network errors and 5xx errors
    return true;
  }

  /**
   * Delay helper for retry logic
   */
  delay(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  /**
   * GET request
   */
  async get(endpoint, params = {}) {
    // Build query string from params
    const queryString = new URLSearchParams(params).toString();
    const fullEndpoint = queryString ? `${endpoint}?${queryString}` : endpoint;

    return this.request(fullEndpoint, {
      method: "GET",
    });
  }

  /**
   * POST request
   */
  async post(endpoint, data = {}) {
    return this.request(endpoint, {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  /**
   * PUT request
   */
  async put(endpoint, data = {}) {
    return this.request(endpoint, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  }

  /**
   * DELETE request
   */
  async delete(endpoint) {
    return this.request(endpoint, {
      method: "DELETE",
    });
  }

  /**
   * PATCH request
   */
  async patch(endpoint, data = {}) {
    return this.request(endpoint, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  }
}

/**
 * Custom API Error class
 */
class ApiError extends Error {
  constructor(message, status, data = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }

  isAuthError() {
    return this.status === 401 || this.status === 403;
  }

  isNotFoundError() {
    return this.status === 404;
  }

  isValidationError() {
    return this.status === 422;
  }

  isServerError() {
    return this.status >= 500;
  }
}

// Create global API client instance
const apiClient = new ApiClient(window.AppConfig || AppConfig);

// Export for use in other modules
if (typeof module !== "undefined" && module.exports) {
  module.exports = { ApiClient, ApiError, apiClient };
}

if (typeof window !== "undefined") {
  window.ApiClient = ApiClient;
  window.ApiError = ApiError;
  window.apiClient = apiClient;
}

console.log("🌐 API Client initialized");
