/**
 * Critical Sectors Service
 * Handles critical sector-related API calls
 */

class CriticalSectorsService {
  constructor(apiClient) {
    this.client = apiClient;
  }

  /**
   * Get all critical sectors
   */
  async getAll() {
    try {
      const response = await this.client.get("/critical-sectors");
      console.log(`✅ Loaded ${response.length} critical sectors`);
      return response;
    } catch (error) {
      console.error("❌ Failed to fetch critical sectors:", error.message);
      throw error;
    }
  }

  /**
   * Get critical sectors for a specific floor
   */
  async getByFloor(floorId) {
    try {
      const response = await this.client.get("/critical-sectors", {
        floor_id: floorId,
      });
      console.log(
        `✅ Loaded ${response.length} critical sectors for floor ${floorId}`
      );
      return response;
    } catch (error) {
      console.error(
        `❌ Failed to fetch sectors for floor ${floorId}:`,
        error.message
      );
      throw error;
    }
  }

  /**
   * Get critical sector by ID
   */
  async getById(sectorId) {
    try {
      const response = await this.client.get(`/critical-sectors/${sectorId}`);
      console.log(`✅ Loaded critical sector ${sectorId}`);
      return response;
    } catch (error) {
      console.error(
        `❌ Failed to fetch critical sector ${sectorId}:`,
        error.message
      );
      throw error;
    }
  }

  /**
   * Create new critical sector
   */
  async create(sectorData) {
    try {
      const response = await this.client.post("/critical-sectors", sectorData);
      console.log("✅ Critical sector created:", response.sector_name);
      return response;
    } catch (error) {
      console.error("❌ Failed to create critical sector:", error.message);
      throw error;
    }
  }

  /**
   * Update critical sector
   */
  async update(sectorId, sectorData) {
    try {
      const response = await this.client.put(
        `/critical-sectors/${sectorId}`,
        sectorData
      );
      console.log(`✅ Critical sector ${sectorId} updated`);
      return response;
    } catch (error) {
      console.error(
        `❌ Failed to update critical sector ${sectorId}:`,
        error.message
      );
      throw error;
    }
  }

  /**
   * Delete critical sector
   */
  async delete(sectorId) {
    try {
      const response = await this.client.delete(
        `/critical-sectors/${sectorId}`
      );
      console.log(`✅ Critical sector ${sectorId} deleted`);
      return response;
    } catch (error) {
      console.error(
        `❌ Failed to delete critical sector ${sectorId}:`,
        error.message
      );
      throw error;
    }
  }

  /**
   * Get sectors by priority level
   */
  async getByPriority(priority, floorId = null) {
    try {
      const params = { priority };

      if (floorId) {
        params.floor_id = floorId;
      }

      const response = await this.client.get("/critical-sectors", params);
      console.log(
        `✅ Loaded ${response.length} sectors with priority ${priority}`
      );
      return response;
    } catch (error) {
      console.error(
        `❌ Failed to fetch sectors by priority ${priority}:`,
        error.message
      );
      throw error;
    }
  }

  /**
   * Get high priority sectors
   */
  async getHighPriority(floorId = null) {
    return this.getByPriority("high", floorId);
  }

  /**
   * Get sectors by type
   */
  async getByType(type, floorId = null) {
    try {
      const params = { type };

      if (floorId) {
        params.floor_id = floorId;
      }

      const response = await this.client.get("/critical-sectors", params);
      console.log(`✅ Loaded ${response.length} sectors of type ${type}`);
      return response;
    } catch (error) {
      console.error(
        `❌ Failed to fetch sectors by type ${type}:`,
        error.message
      );
      throw error;
    }
  }

  /**
   * Check if coordinates are within any critical sector
   */
  async checkIntersection(floorId, x, y) {
    try {
      const response = await this.client.post("/critical-sectors/check", {
        floor_id: floorId,
        x_coord: x,
        y_coord: y,
      });

      if (response.in_sector) {
        console.log(
          `⚠️ Coordinates (${x}, ${y}) are within critical sector: ${response.sector.sector_name}`
        );
      }

      return response;
    } catch (error) {
      console.error("❌ Failed to check sector intersection:", error.message);
      throw error;
    }
  }

  /**
   * Get statistics about critical sectors
   */
  async getStats() {
    try {
      const response = await this.client.get("/critical-sectors/stats");
      console.log("✅ Critical sectors statistics loaded");
      return response;
    } catch (error) {
      console.error(
        "❌ Failed to fetch critical sectors stats:",
        error.message
      );
      throw error;
    }
  }

  /**
   * Batch delete sectors for a floor
   */
  async deleteAllForFloor(floorId) {
    try {
      const sectors = await this.getByFloor(floorId);
      const deletePromises = sectors.map((sector) => this.delete(sector.id));

      await Promise.all(deletePromises);

      console.log(
        `✅ Deleted all ${sectors.length} sectors for floor ${floorId}`
      );
      return { success: true, deleted: sectors.length };
    } catch (error) {
      console.error(
        `❌ Failed to delete all sectors for floor ${floorId}:`,
        error.message
      );
      throw error;
    }
  }
}

// Create global instance
const criticalSectorsService = new CriticalSectorsService(
  window.apiClient || apiClient
);

// Export for use in other modules
if (typeof module !== "undefined" && module.exports) {
  module.exports = { CriticalSectorsService, criticalSectorsService };
}

if (typeof window !== "undefined") {
  window.CriticalSectorsService = CriticalSectorsService;
  window.criticalSectorsService = criticalSectorsService;
}

console.log("🎨 Critical Sectors service initialized");
