/**
 * Application Configuration
 * Central configuration for the Electrician Work Log System
 */

const AppConfig = {
  // API Configuration
  api: {
    baseUrl: "http://localhost:5000/api",
    timeout: 30000,
    retryAttempts: 3,
    retryDelay: 1000,
  },

  // Authentication Configuration
  auth: {
    tokenKey: "auth_token",
    userDataKey: "user_data",
    tokenExpiryBuffer: 300, // 5 minutes before expiry
  },

  // Map Configuration
  map: {
    minZoom: 0.5,
    maxZoom: 20,
    defaultZoom: 1,
    zoomPerClick: 2,
    zoomPerScroll: 1.3,
    tileSize: 512,
  },

  // UI Configuration
  ui: {
    debounceDelay: 300,
    animationDuration: 400,
    toastDuration: 3000,
  },

  // Work Type Colors
  workTypes: {
    colors: {
      Electrical: "#ef4444",
      Lighting: "#3b82f6",
      Maintenance: "#10b981",
      Installation: "#eab308",
      Inspection: "#8b5cf6",
      Repair: "#f97316",
      Other: "#8b5cf6",
    },
    badgeClasses: {
      Electrical: "bg-red-100 text-red-800",
      Lighting: "bg-blue-100 text-blue-800",
      Maintenance: "bg-green-100 text-green-800",
      Installation: "bg-yellow-100 text-yellow-800",
      Inspection: "bg-purple-100 text-purple-800",
      Repair: "bg-orange-100 text-orange-800",
      Other: "bg-purple-100 text-purple-800",
    },
  },

  // Critical Sector Configuration
  sectors: {
    priorityColors: {
      high: "rgba(239, 68, 68, 0.3)",
      medium: "rgba(245, 158, 11, 0.3)",
      standard: "rgba(16, 185, 129, 0.3)",
    },
    borderColors: {
      high: "#ef4444",
      medium: "#f59e0b",
      standard: "#10b981",
    },
  },

  // PDF Rendering Configuration
  pdf: {
    maxDimension: 1500,
    workerSrc:
      "https://cdn.jsdelivr.net/npm/pdfjs-dist@3.11.174/build/pdf.worker.min.js",
  },

  // Feature Flags
  features: {
    enableCriticalSectors: true,
    enableNotifications: true,
    enableAssignments: true,
    enableDateFilter: true,
  },
};

// Freeze config to prevent modifications
Object.freeze(AppConfig);

// Export for use in other modules
if (typeof module !== "undefined" && module.exports) {
  module.exports = AppConfig;
}

if (typeof window !== "undefined") {
  window.AppConfig = AppConfig;
}

console.log("⚙️ Application configuration loaded");
