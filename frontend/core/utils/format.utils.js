/**
 * Format Utilities
 * Helper functions for formatting data display
 */

const FormatUtils = {
  /**
   * Get work type color
   */
  getWorkTypeColor(workType) {
    const config = window.AppConfig || AppConfig;
    return config.workTypes.colors[workType] || config.workTypes.colors.Other;
  },

  /**
   * Get work type badge CSS class
   */
  getWorkTypeBadgeClass(workType) {
    const config = window.AppConfig || AppConfig;
    return (
      config.workTypes.badgeClasses[workType] ||
      config.workTypes.badgeClasses.Other
    );
  },

  /**
   * Get sector priority color
   */
  getSectorPriorityColor(priority) {
    const config = window.AppConfig || AppConfig;
    return (
      config.sectors.priorityColors[priority] ||
      config.sectors.priorityColors.standard
    );
  },

  /**
   * Get sector border color
   */
  getSectorBorderColor(priority) {
    const config = window.AppConfig || AppConfig;
    return (
      config.sectors.borderColors[priority] ||
      config.sectors.borderColors.standard
    );
  },

  /**
   * Format coordinates to display format (percentage with 1 decimal)
   */
  formatCoordinate(coord) {
    if (typeof coord !== "number") return "0.0%";
    return `${(coord * 100).toFixed(1)}%`;
  },

  /**
   * Format coordinates pair
   */
  formatCoordinates(x, y) {
    return `(${this.formatCoordinate(x)}, ${this.formatCoordinate(y)})`;
  },

  /**
   * Truncate text with ellipsis
   */
  truncate(text, maxLength = 50) {
    if (!text) return "";
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength - 3) + "...";
  },

  /**
   * Capitalize first letter
   */
  capitalize(text) {
    if (!text) return "";
    return text.charAt(0).toUpperCase() + text.slice(1).toLowerCase();
  },

  /**
   * Convert to title case
   */
  toTitleCase(text) {
    if (!text) return "";
    return text
      .toLowerCase()
      .split(" ")
      .map((word) => this.capitalize(word))
      .join(" ");
  },

  /**
   * Format file size
   */
  formatFileSize(bytes) {
    if (bytes === 0) return "0 Bytes";

    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + " " + sizes[i];
  },

  /**
   * Format number with thousands separator
   */
  formatNumber(num) {
    if (typeof num !== "number") return "0";
    return num.toLocaleString();
  },

  /**
   * Format percentage
   */
  formatPercentage(value, total) {
    if (total === 0) return "0%";
    return `${Math.round((value / total) * 100)}%`;
  },

  /**
   * Format phone number (US format)
   */
  formatPhoneNumber(phone) {
    if (!phone) return "";

    const cleaned = ("" + phone).replace(/\D/g, "");
    const match = cleaned.match(/^(\d{3})(\d{3})(\d{4})$/);

    if (match) {
      return "(" + match[1] + ") " + match[2] + "-" + match[3];
    }

    return phone;
  },

  /**
   * Format duration in milliseconds to readable format
   */
  formatDuration(ms) {
    const seconds = Math.floor(ms / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);

    if (hours > 0) {
      return `${hours}h ${minutes % 60}m`;
    } else if (minutes > 0) {
      return `${minutes}m ${seconds % 60}s`;
    } else {
      return `${seconds}s`;
    }
  },

  /**
   * Format priority level with icon
   */
  formatPriority(priority) {
    const icons = {
      high: "🔴",
      medium: "🟡",
      standard: "🟢",
    };

    const icon = icons[priority] || icons.standard;
    return `${icon} ${this.capitalize(priority)}`;
  },

  /**
   * Format user role
   */
  formatRole(role) {
    const roleNames = {
      admin: "Administrator",
      supervisor: "Supervisor",
      worker: "Worker",
    };

    return roleNames[role] || this.toTitleCase(role);
  },

  /**
   * Get hex color for assignment/status badge (pending, in-progress, completed, etc.)
   */
  getStatusColor(status) {
    const colors = {
      pending: "#f59e0b",
      "in-progress": "#3b82f6",
      completed: "#10b981",
      failed: "#ef4444",
    };
    return colors[status] || "#6b7280";
  },

  /**
   * Format status with color
   */
  formatStatus(status) {
    const statusConfig = {
      completed: { text: "Completed", color: "green" },
      in_progress: { text: "In Progress", color: "blue" },
      pending: { text: "Pending", color: "yellow" },
      failed: { text: "Failed", color: "red" },
    };

    return statusConfig[status] || { text: status, color: "gray" };
  },

  /**
   * Sanitize HTML to prevent XSS
   */
  sanitizeHtml(html) {
    const div = document.createElement("div");
    div.textContent = html;
    return div.innerHTML;
  },

  /**
   * Format array to comma-separated string
   */
  formatList(arr, conjunction = "and") {
    if (!arr || arr.length === 0) return "";
    if (arr.length === 1) return arr[0];
    if (arr.length === 2) return `${arr[0]} ${conjunction} ${arr[1]}`;

    const last = arr[arr.length - 1];
    const rest = arr.slice(0, -1).join(", ");
    return `${rest}, ${conjunction} ${last}`;
  },

  /**
   * Generate initials from name
   */
  getInitials(name) {
    if (!name) return "";

    return name
      .split(" ")
      .map((word) => word.charAt(0).toUpperCase())
      .join("")
      .substring(0, 2);
  },

  /**
   * Format boolean to Yes/No
   */
  formatBoolean(value) {
    return value ? "Yes" : "No";
  },

  /**
   * Format zoom level as percentage
   */
  formatZoom(zoomLevel) {
    return `${Math.round(zoomLevel * 100)}%`;
  },

  /**
   * Create URL-friendly slug
   */
  slugify(text) {
    return text
      .toString()
      .toLowerCase()
      .trim()
      .replace(/\s+/g, "-")
      .replace(/[^\w\-]+/g, "")
      .replace(/\-\-+/g, "-");
  },

  /**
   * Format error message for display
   */
  formatError(error) {
    if (typeof error === "string") return error;
    if (error.message) return error.message;
    if (error.data && error.data.message) return error.data.message;
    return "An unexpected error occurred";
  },
};

// Export for use in other modules
if (typeof module !== "undefined" && module.exports) {
  module.exports = FormatUtils;
}

if (typeof window !== "undefined") {
  window.FormatUtils = FormatUtils;
}

console.log("🎨 Format utilities loaded");
