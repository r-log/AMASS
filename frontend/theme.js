// Theme Management System
class ThemeManager {
  constructor() {
    this.currentTheme = this.getStoredTheme() || "light";
    this.init();
  }

  init() {
    // Apply stored theme on page load
    this.applyTheme(this.currentTheme);

    // Create and add theme toggle button
    this.createThemeToggle();

    // Listen for system theme changes
    this.watchSystemTheme();
  }

  getStoredTheme() {
    return localStorage.getItem("electrician-theme");
  }

  setStoredTheme(theme) {
    localStorage.setItem("electrician-theme", theme);
  }

  applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    this.currentTheme = theme;
    this.setStoredTheme(theme);
    this.updateToggleButton();
  }

  toggleTheme() {
    const newTheme = this.currentTheme === "light" ? "dark" : "light";
    this.applyTheme(newTheme);

    // Add a subtle animation effect
    document.body.style.transition = "all 0.3s ease";
    setTimeout(() => {
      document.body.style.transition = "";
    }, 300);
  }

  createThemeToggle() {
    // Use existing theme toggle button if it exists
    const existingToggle = document.querySelector("#theme-toggle");
    if (existingToggle) {
      this.toggleButton = existingToggle;
      this.toggleIcon = existingToggle.querySelector(".theme-toggle-icon");
      // Only look for text span if it exists (for backwards compatibility)
      this.toggleText = existingToggle.querySelector(
        "span:not(.theme-toggle-icon)"
      );

      // Add click event listener
      existingToggle.addEventListener("click", () => this.toggleTheme());

      this.updateToggleButton();
      return;
    }

    // Fallback: create button if none exists
    const toggle = document.createElement("button");
    toggle.className = "theme-toggle";
    toggle.setAttribute("aria-label", "Toggle theme");
    toggle.setAttribute("title", "Toggle between light and dark theme");

    const icon = document.createElement("span");
    icon.className = "theme-toggle-icon";

    const text = document.createElement("span");
    text.className = "theme-toggle-text";

    toggle.appendChild(icon);
    toggle.appendChild(text);

    toggle.addEventListener("click", () => this.toggleTheme());

    document.body.appendChild(toggle);

    this.toggleButton = toggle;
    this.toggleIcon = icon;
    this.toggleText = text;

    this.updateToggleButton();
  }

  updateToggleButton() {
    if (!this.toggleButton) return;

    if (this.currentTheme === "dark") {
      this.toggleIcon.textContent = "☀️";
      if (this.toggleText) this.toggleText.textContent = "Light";
      this.toggleButton.setAttribute("title", "Switch to light theme");
    } else {
      this.toggleIcon.textContent = "🌙";
      if (this.toggleText) this.toggleText.textContent = "Dark";
      this.toggleButton.setAttribute("title", "Switch to dark theme");
    }
  }

  watchSystemTheme() {
    // Listen for system theme changes
    if (window.matchMedia) {
      const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
      mediaQuery.addListener((e) => {
        // Only auto-switch if user hasn't manually set a preference
        if (!this.getStoredTheme()) {
          this.applyTheme(e.matches ? "dark" : "light");
        }
      });
    }
  }

  // Utility method to get current theme
  getCurrentTheme() {
    return this.currentTheme;
  }

  // Method to check if dark theme is active
  isDarkTheme() {
    return this.currentTheme === "dark";
  }

  // Method to programmatically set theme (useful for other scripts)
  setTheme(theme) {
    if (theme === "light" || theme === "dark") {
      this.applyTheme(theme);
    }
  }
}

// Auto-initialize theme manager when DOM is loaded
document.addEventListener("DOMContentLoaded", () => {
  window.themeManager = new ThemeManager();
});

// Also initialize immediately if DOM is already loaded
if (document.readyState === "loading") {
  // DOM is still loading
} else {
  // DOM is already loaded
  window.themeManager = new ThemeManager();
}

// Export for use in other scripts
if (typeof module !== "undefined" && module.exports) {
  module.exports = ThemeManager;
}
