/**
 * Dashboard Service
 * Handles dashboard stats API calls
 */

class DashboardService {
  constructor(apiClient) {
    this.client = apiClient;
  }

  async getSupervisorStats() {
    try {
      const response = await this.client.get("/dashboard/supervisor");
      return response;
    } catch (error) {
      console.error("❌ Failed to fetch supervisor dashboard stats:", error.message);
      throw error;
    }
  }
}

const dashboardService = new DashboardService(window.apiClient || apiClient);

if (typeof window !== "undefined") {
  window.DashboardService = DashboardService;
  window.dashboardService = dashboardService;
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { DashboardService, dashboardService };
}
