/**
 * Login Vue.js Application
 * Handles user authentication for the Electrician Work Log System
 */

const { createApp } = Vue;

// API_BASE is already defined globally in auth.js (no need to redeclare)

createApp({
  data() {
    return {
      credentials: {
        username: "",
        password: "",
      },
      rememberMe: false,
      showPassword: false,
      isLoading: false,
      errorMessage: "",
      loginError: false,
    };
  },

  mounted() {
    // Check if user is already logged in
    this.checkExistingAuth();

    // Focus on username field
    this.$nextTick(() => {
      document.getElementById("username").focus();
    });
  },

  methods: {
    async checkExistingAuth() {
      // Use authManager if available
      if (window.authManager && window.authManager.isAuthenticated()) {
        try {
          const isValid = await window.authManager.verifyToken();
          if (isValid) {
            console.log("User already authenticated, redirecting...");
            this.redirectToMainApp();
            return;
          }
        } catch (error) {
          console.log("Token verification failed:", error);
        }
      }
    },

    async login() {
      if (this.isLoading) return;

      this.isLoading = true;
      this.errorMessage = "";
      this.loginError = false;

      try {
        console.log("Attempting login for user:", this.credentials.username);

        // Use authService if available, otherwise fallback to direct API call
        let result;
        if (window.authService) {
          result = await window.authService.login(
            this.credentials.username,
            this.credentials.password
          );
        } else {
          // Fallback to direct API call
          const response = await fetch(`${API_BASE}/auth/login`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              username: this.credentials.username,
              password: this.credentials.password,
            }),
          });

          result = await response.json();
        }

        if (result.success && result.token && result.user) {
          console.log("Login successful:", result.user);

          // Store token using authManager
          if (window.authManager) {
            window.authManager.setAuth(result.token, result.user);
          } else {
            // Fallback storage
            this.storeToken(result.token, result.user);
          }

          // Show success message briefly
          this.showSuccessAndRedirect(result.user);
        } else {
          // Login failed
          this.handleLoginError(result.error || "Login failed");
        }
      } catch (error) {
        console.error("Login error:", error);
        const errorMsg = window.FormatUtils
          ? window.FormatUtils.formatError(error)
          : "Network error. Please check your connection and try again.";
        this.handleLoginError(errorMsg);
      } finally {
        this.isLoading = false;
      }
    },

    handleLoginError(message) {
      this.errorMessage = message;
      this.loginError = true;

      // Remove shake effect after animation
      setTimeout(() => {
        this.loginError = false;
      }, 500);

      // Clear password field
      this.credentials.password = "";

      // Focus back on username or password field
      this.$nextTick(() => {
        if (!this.credentials.username) {
          document.getElementById("username").focus();
        } else {
          document.getElementById("password").focus();
        }
      });
    },

    showSuccessAndRedirect(user) {
      // Clear error message
      this.errorMessage = "";

      // Show success state
      const button = document.querySelector(".login-button");
      if (button) {
        button.innerHTML = `
                    <span class="flex items-center justify-center">
                        <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                        </svg>
                        Welcome, ${user.full_name}!
                    </span>
                `;
        button.style.background =
          "linear-gradient(135deg, #10b981 0%, #059669 100%)";
      }

      // Redirect after short delay
      setTimeout(() => {
        this.redirectToMainApp();
      }, 1500);
    },

    storeToken(token, user) {
      const storage = this.rememberMe ? localStorage : sessionStorage;

      storage.setItem("auth_token", token);
      storage.setItem("user_data", JSON.stringify(user));

      console.log(
        `Token stored in ${this.rememberMe ? "localStorage" : "sessionStorage"}`
      );
    },

    getStoredToken() {
      return (
        localStorage.getItem("auth_token") ||
        sessionStorage.getItem("auth_token")
      );
    },

    removeStoredToken() {
      localStorage.removeItem("auth_token");
      localStorage.removeItem("user_data");
      sessionStorage.removeItem("auth_token");
      sessionStorage.removeItem("user_data");
    },

    redirectToMainApp() {
      // Get user data to determine role
      const userData = JSON.parse(
        localStorage.getItem("user_data") ||
          sessionStorage.getItem("user_data") ||
          "{}"
      );

      // Redirect based on user role
      if (userData.role === "worker") {
        window.location.href = "worker_dashboard.html";
      } else if (userData.role === "supervisor") {
        window.location.href = "supervisor_dashboard.html";
      } else if (userData.role === "admin") {
        window.location.href = "admin_dashboard.html";
      } else {
        // Default fallback
        window.location.href = "index.html";
      }
    },

    // Handle Enter key in form fields
    handleKeyPress(event) {
      if (event.key === "Enter") {
        this.login();
      }
    },
  },
}).mount("#app");

console.log("🔐 Login application initialized");
