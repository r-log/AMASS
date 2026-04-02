/**
 * Tiles Service
 * Handles tile generation and management API calls
 */

class TilesService {
  constructor(apiClient) {
    this.client = apiClient;
  }

  /**
   * Check tile status for a floor
   */
  async getStatus(floorId) {
    try {
      const response = await this.client.get(`/tiles/status/${floorId}`);
      console.log(`✅ Tile status for floor ${floorId}:`, response.tiles_exist);
      return response;
    } catch (error) {
      console.error(
        `❌ Failed to check tile status for floor ${floorId}:`,
        error.message
      );
      throw error;
    }
  }

  /**
   * Generate tiles for a specific floor (optionally with image_path)
   */
  async generate(floorId, imagePath = null) {
    try {
      const body = imagePath
        ? { floor_id: floorId, image_path: imagePath }
        : { floor_id: floorId };
      const response = await this.client.post(`/tiles/generate/${floorId}`, body);
      console.log(`✅ Tile generation started for floor ${floorId}`);
      return response;
    } catch (error) {
      console.error(
        `❌ Failed to generate tiles for floor ${floorId}:`,
        error.message
      );
      throw error;
    }
  }

  /**
   * Batch generate tiles for all floors
   */
  async batchGenerate() {
    try {
      const response = await this.client.post("/tiles/batch-generate");
      console.log("✅ Batch tile generation started");
      return response;
    } catch (error) {
      console.error("❌ Failed to batch generate tiles:", error.message);
      throw error;
    }
  }

  /**
   * Delete tiles for a specific floor
   */
  async delete(floorId) {
    try {
      const response = await this.client.delete(`/tiles/${floorId}`);
      console.log(`✅ Tiles deleted for floor ${floorId}`);
      return response;
    } catch (error) {
      console.error(
        `❌ Failed to delete tiles for floor ${floorId}:`,
        error.message
      );
      throw error;
    }
  }

  /**
   * Get tile URL for OpenSeadragon
   */
  getTileUrl(floorId) {
    return `${this.client.baseUrl}/tiles/${floorId}/floor-${floorId}.dzi`;
  }

  /**
   * Get tile generation progress
   */
  async getProgress(floorId) {
    try {
      const response = await this.client.get(`/tiles/progress/${floorId}`);
      return response;
    } catch (error) {
      console.error(
        `❌ Failed to get tile progress for floor ${floorId}:`,
        error.message
      );
      throw error;
    }
  }

  /**
   * Regenerate tiles for a floor (delete and generate)
   */
  async regenerate(floorId) {
    try {
      // Delete existing tiles first
      try {
        await this.delete(floorId);
      } catch (deleteError) {
        console.warn(
          "⚠️ No existing tiles to delete or delete failed:",
          deleteError.message
        );
      }

      // Generate new tiles
      const response = await this.generate(floorId);
      console.log(`✅ Tile regeneration started for floor ${floorId}`);
      return response;
    } catch (error) {
      console.error(
        `❌ Failed to regenerate tiles for floor ${floorId}:`,
        error.message
      );
      throw error;
    }
  }

  /**
   * Optimize tiles (recompress PNGs, remove empty dirs). Admin only.
   * @param {Object} options - { floor_id?: number, recompress?: boolean, compress_level?: number }
   */
  async optimize(options = {}) {
    try {
      const response = await this.client.post("/tiles/optimize", options, {
        timeout: 300000, // 5 min - tile recompression can take a long time
      });
      console.log("✅ Tile optimization completed:", response.result);
      return response;
    } catch (error) {
      console.error("❌ Failed to optimize tiles:", error.message);
      throw error;
    }
  }

  /**
   * Check if tiles exist for all floors
   */
  async checkAllStatuses() {
    try {
      const response = await this.client.get("/tiles/status");
      console.log("✅ Checked tile status for all floors");
      return response;
    } catch (error) {
      console.error("❌ Failed to check all tile statuses:", error.message);
      throw error;
    }
  }
}

// Create global instance
const tilesService = new TilesService(window.apiClient || apiClient);

// Export for use in other modules
if (typeof module !== "undefined" && module.exports) {
  module.exports = { TilesService, tilesService };
}

if (typeof window !== "undefined") {
  window.TilesService = TilesService;
  window.tilesService = tilesService;
}

console.log("🗺️ Tiles service initialized");
