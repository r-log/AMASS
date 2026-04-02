/**
 * Floors Service
 * Handles floor-related API calls
 */

class FloorsService {
  constructor(apiClient) {
    this.client = apiClient;
  }

  /**
   * Get all floors, optionally filtered by project_id
   */
  async getAll(params = {}) {
    try {
      const response = await this.client.get("/floors", params);
      console.log(`✅ Loaded ${response?.length ?? 0} floors`);
      return response;
    } catch (error) {
      console.error("❌ Failed to fetch floors:", error.message);
      throw error;
    }
  }

  /**
   * Get floor by ID
   */
  async getById(floorId) {
    try {
      const response = await this.client.get(`/floors/${floorId}`);
      console.log(`✅ Loaded floor ${floorId}:`, response.name);
      return response;
    } catch (error) {
      console.error(`❌ Failed to fetch floor ${floorId}:`, error.message);
      throw error;
    }
  }

  /**
   * Create new floor (JSON)
   */
  async create(floorData) {
    try {
      const response = await this.client.post("/floors", floorData);
      return response;
    } catch (error) {
      console.error("❌ Failed to create floor:", error.message);
      throw error;
    }
  }

  /**
   * Create floor with file upload (multipart)
   */
  async createWithUpload(projectId, name, file, opts = {}) {
    const formData = new FormData();
    formData.append("name", name);
    formData.append("project_id", projectId);
    if (file) formData.append("file", file);
    if (opts.width) formData.append("width", opts.width);
    if (opts.height) formData.append("height", opts.height);

    const url = `${this.client.baseUrl}/floors`;
    const headers = {
      Authorization: `Bearer ${this.client.authManager.getToken()}`,
    };
    const response = await (window.offlineQueue
      ? window.offlineQueue.fetchFormData(url, { method: "POST", headers, body: formData })
      : fetch(url, { method: "POST", headers, body: formData }));
    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.error || "Failed to create floor");
    }
    return response.json();
  }

  /**
   * Update floor
   */
  async update(floorId, floorData) {
    try {
      const response = await this.client.put(`/floors/${floorId}`, floorData);
      console.log(`✅ Floor ${floorId} updated:`, response.name);
      return response;
    } catch (error) {
      console.error(`❌ Failed to update floor ${floorId}:`, error.message);
      throw error;
    }
  }

  /**
   * Delete floor
   */
  async delete(floorId) {
    try {
      const response = await this.client.delete(`/floors/${floorId}`);
      console.log(`✅ Floor ${floorId} deleted`);
      return response;
    } catch (error) {
      console.error(`❌ Failed to delete floor ${floorId}:`, error.message);
      throw error;
    }
  }

  /**
   * Get floor statistics
   */
  async getStats(floorId) {
    try {
      const response = await this.client.get(`/floors/${floorId}/stats`);
      return response;
    } catch (error) {
      console.error(
        `❌ Failed to fetch floor ${floorId} stats:`,
        error.message
      );
      throw error;
    }
  }

  /**
   * Batch-import multiple floor plans at once.
   * @param {number} projectId
   * @param {File[]} files - Array of File objects
   * @param {string[]} names - Floor name for each file (same order)
   * @returns {Promise<Object>} { floors, errors, tiles_generating }
   */
  async batchImport(projectId, files, names, onUploadProgress) {
    const formData = new FormData();
    formData.append("project_id", projectId);
    files.forEach((f) => formData.append("files[]", f));
    names.forEach((n) => formData.append("names[]", n));

    const url = `${this.client.baseUrl}/floors/batch-import`;
    const token = this.client.authManager.getToken();

    // Use XMLHttpRequest for upload progress tracking
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open("POST", url);
      xhr.setRequestHeader("Authorization", `Bearer ${token}`);

      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable && onUploadProgress) {
          onUploadProgress(Math.round((e.loaded / e.total) * 100));
        }
      };

      xhr.onload = () => {
        try {
          const data = JSON.parse(xhr.responseText);
          if (xhr.status >= 200 && xhr.status < 300) {
            resolve(data);
          } else {
            reject(new Error(data.error || "Batch import failed"));
          }
        } catch (e) {
          reject(new Error("Invalid server response"));
        }
      };

      xhr.onerror = () => reject(new Error("Upload failed — network error"));
      xhr.send(formData);
    });
  }

  /**
   * Upload floor plan image
   */
  async uploadFloorPlan(floorId, file) {
    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(
        `${this.client.baseUrl}/floors/${floorId}/upload`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${this.client.authManager.getToken()}`,
          },
          body: formData,
        }
      );

      if (!response.ok) {
        throw new Error("Upload failed");
      }

      const result = await response.json();
      console.log(`✅ Floor plan uploaded for floor ${floorId}`);
      return result;
    } catch (error) {
      console.error(`❌ Failed to upload floor plan:`, error.message);
      throw error;
    }
  }
}

// Create global instance
const floorsService = new FloorsService(window.apiClient || apiClient);

// Export for use in other modules
if (typeof module !== "undefined" && module.exports) {
  module.exports = { FloorsService, floorsService };
}

if (typeof window !== "undefined") {
  window.FloorsService = FloorsService;
  window.floorsService = floorsService;
}

console.log("🏢 Floors service initialized");
