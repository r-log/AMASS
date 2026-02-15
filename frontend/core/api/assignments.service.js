/**
 * Assignments Service
 * Handles assignment-related API calls
 */

class AssignmentsService {
  constructor(apiClient) {
    this.client = apiClient;
  }

  async getAll(params = {}) {
    try {
      const response = await this.client.get("/assignments", params);
      return response;
    } catch (error) {
      console.error("❌ Failed to fetch assignments:", error.message);
      throw error;
    }
  }

  async getById(assignmentId) {
    try {
      const response = await this.client.get(`/assignments/${assignmentId}`);
      return response;
    } catch (error) {
      console.error(`❌ Failed to fetch assignment ${assignmentId}:`, error.message);
      throw error;
    }
  }

  async create(data) {
    try {
      const response = await this.client.post("/assignments", data);
      return response;
    } catch (error) {
      console.error("❌ Failed to create assignment:", error.message);
      throw error;
    }
  }

  async update(assignmentId, data) {
    try {
      const response = await this.client.put(`/assignments/${assignmentId}`, data);
      return response;
    } catch (error) {
      console.error(`❌ Failed to update assignment ${assignmentId}:`, error.message);
      throw error;
    }
  }

  async delete(assignmentId) {
    try {
      await this.client.delete(`/assignments/${assignmentId}`);
    } catch (error) {
      console.error(`❌ Failed to delete assignment ${assignmentId}:`, error.message);
      throw error;
    }
  }

  async updateStatus(assignmentId, status) {
    try {
      const response = await this.client.put(`/assignments/${assignmentId}/status`, { status });
      return response;
    } catch (error) {
      console.error(`❌ Failed to update assignment status:`, error.message);
      throw error;
    }
  }
}

const assignmentsService = new AssignmentsService(window.apiClient || apiClient);

if (typeof window !== "undefined") {
  window.AssignmentsService = AssignmentsService;
  window.assignmentsService = assignmentsService;
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { AssignmentsService, assignmentsService };
}
