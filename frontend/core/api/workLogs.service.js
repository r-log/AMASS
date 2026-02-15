/**
 * Work Logs Service
 * Handles work log-related API calls
 */

class WorkLogsService {
  constructor(apiClient) {
    this.client = apiClient;
  }

  /**
   * Get all work logs with optional filters
   */
  async getAll(filters = {}) {
    try {
      const response = await this.client.get("/work-logs", filters);
      console.log(`✅ Loaded ${response.length} work logs`);
      return response;
    } catch (error) {
      console.error("❌ Failed to fetch work logs:", error.message);
      throw error;
    }
  }

  /**
   * Get work logs for a specific floor
   */
  async getByFloor(floorId) {
    try {
      const response = await this.client.get("/work-logs", {
        floor_id: floorId,
      });
      console.log(`✅ Loaded ${response.length} logs for floor ${floorId}`);
      return response;
    } catch (error) {
      console.error(
        `❌ Failed to fetch logs for floor ${floorId}:`,
        error.message
      );
      throw error;
    }
  }

  /**
   * Get work log by ID
   */
  async getById(logId) {
    try {
      const response = await this.client.get(`/work-logs/${logId}`);
      console.log(`✅ Loaded work log ${logId}`);
      return response;
    } catch (error) {
      console.error(`❌ Failed to fetch work log ${logId}:`, error.message);
      throw error;
    }
  }

  /**
   * Create enhanced work log (with cable details)
   */
  async createEnhanced(workLogData) {
    try {
      const response = await this.client.post("/work-logs/enhanced", workLogData);
      console.log("✅ Enhanced work log created");
      return response;
    } catch (error) {
      console.error("❌ Failed to create enhanced work log:", error.message);
      throw error;
    }
  }

  /**
   * Create new work log
   */
  async create(workLogData) {
    try {
      const response = await this.client.post("/work-logs", workLogData);
      console.log("✅ Work log created:", response.id);
      return response;
    } catch (error) {
      console.error("❌ Failed to create work log:", error.message);
      throw error;
    }
  }

  /**
   * Update work log
   */
  async update(logId, workLogData) {
    try {
      const response = await this.client.put(
        `/work-logs/${logId}`,
        workLogData
      );
      console.log(`✅ Work log ${logId} updated`);
      return response;
    } catch (error) {
      console.error(`❌ Failed to update work log ${logId}:`, error.message);
      throw error;
    }
  }

  /**
   * Delete work log
   */
  async delete(logId) {
    try {
      const response = await this.client.delete(`/work-logs/${logId}`);
      console.log(`✅ Work log ${logId} deleted`);
      return response;
    } catch (error) {
      console.error(`❌ Failed to delete work log ${logId}:`, error.message);
      throw error;
    }
  }

  /**
   * Get work logs by date range
   */
  async getByDateRange(startDate, endDate, floorId = null) {
    try {
      const params = {
        start_date: startDate,
        end_date: endDate,
      };

      if (floorId) {
        params.floor_id = floorId;
      }

      const response = await this.client.get("/work-logs", params);
      console.log(
        `✅ Loaded ${response.length} logs for date range ${startDate} to ${endDate}`
      );
      return response;
    } catch (error) {
      console.error("❌ Failed to fetch logs by date range:", error.message);
      throw error;
    }
  }

  /**
   * Get work logs by work type
   */
  async getByWorkType(workType, floorId = null) {
    try {
      const params = { work_type: workType };

      if (floorId) {
        params.floor_id = floorId;
      }

      const response = await this.client.get("/work-logs", params);
      console.log(
        `✅ Loaded ${response.length} logs for work type ${workType}`
      );
      return response;
    } catch (error) {
      console.error(
        `❌ Failed to fetch logs by work type ${workType}:`,
        error.message
      );
      throw error;
    }
  }

  /**
   * Get work logs by worker name
   */
  async getByWorker(workerName, floorId = null) {
    try {
      const params = { worker_name: workerName };

      if (floorId) {
        params.floor_id = floorId;
      }

      const response = await this.client.get("/work-logs", params);
      console.log(`✅ Loaded ${response.length} logs for worker ${workerName}`);
      return response;
    } catch (error) {
      console.error(
        `❌ Failed to fetch logs by worker ${workerName}:`,
        error.message
      );
      throw error;
    }
  }

  /**
   * Get dashboard statistics
   */
  async getDashboardStats() {
    try {
      const response = await this.client.get("/work-logs/dashboard");
      console.log("✅ Dashboard statistics loaded");
      return response;
    } catch (error) {
      console.error("❌ Failed to fetch dashboard stats:", error.message);
      throw error;
    }
  }

  /**
   * Search work logs by description
   */
  async search(searchTerm, floorId = null) {
    try {
      const params = { search: searchTerm };

      if (floorId) {
        params.floor_id = floorId;
      }

      const response = await this.client.get("/work-logs", params);
      console.log(`✅ Found ${response.length} logs matching "${searchTerm}"`);
      return response;
    } catch (error) {
      console.error("❌ Failed to search work logs:", error.message);
      throw error;
    }
  }

  /**
   * Batch create work logs
   */
  async batchCreate(workLogsArray) {
    try {
      const response = await this.client.post("/work-logs/batch", {
        logs: workLogsArray,
      });
      console.log(`✅ Created ${workLogsArray.length} work logs in batch`);
      return response;
    } catch (error) {
      console.error("❌ Failed to batch create work logs:", error.message);
      throw error;
    }
  }

  /**
   * Export work logs to CSV
   */
  async exportToCsv(filters = {}) {
    try {
      const params = new URLSearchParams(filters).toString();
      const url = `${this.client.baseUrl}/work-logs/export?${params}`;

      const response = await fetch(url, {
        headers: {
          Authorization: `Bearer ${this.client.authManager.getToken()}`,
        },
      });

      if (!response.ok) {
        throw new Error("Export failed");
      }

      const blob = await response.blob();
      console.log("✅ Work logs exported to CSV");
      return blob;
    } catch (error) {
      console.error("❌ Failed to export work logs:", error.message);
      throw error;
    }
  }
}

// Create global instance
const workLogsService = new WorkLogsService(window.apiClient || apiClient);

// Export for use in other modules
if (typeof module !== "undefined" && module.exports) {
  module.exports = { WorkLogsService, workLogsService };
}

if (typeof window !== "undefined") {
  window.WorkLogsService = WorkLogsService;
  window.workLogsService = workLogsService;
}

console.log("📋 Work Logs service initialized");
