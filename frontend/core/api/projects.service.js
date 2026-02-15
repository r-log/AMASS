/**
 * Projects Service
 * Handles project-related API calls
 */

class ProjectsService {
  constructor(apiClient) {
    this.client = apiClient;
  }

  /**
   * Get projects for current user (workers: assigned only; supervisors: all)
   */
  async getAll() {
    try {
      const response = await this.client.get("/projects");
      return response;
    } catch (error) {
      console.error("❌ Failed to fetch projects:", error.message);
      throw error;
    }
  }

  /**
   * Create new project (supervisor only)
   */
  async create(projectData) {
    try {
      const response = await this.client.post("/projects", projectData);
      return response;
    } catch (error) {
      console.error("❌ Failed to create project:", error.message);
      throw error;
    }
  }

  /**
   * Update project (supervisor only)
   */
  async update(projectId, projectData) {
    try {
      const response = await this.client.put(`/projects/${projectId}`, projectData);
      return response;
    } catch (error) {
      console.error(`❌ Failed to update project ${projectId}:`, error.message);
      throw error;
    }
  }

  /**
   * Get workers assigned to project (supervisor only)
   */
  async getWorkers(projectId) {
    try {
      const response = await this.client.get(`/projects/${projectId}/workers`);
      return response;
    } catch (error) {
      console.error(`❌ Failed to fetch workers for project ${projectId}:`, error.message);
      throw error;
    }
  }

  /**
   * Assign worker to project (supervisor only)
   */
  async assignWorker(projectId, userId) {
    try {
      const response = await this.client.post(`/projects/${projectId}/assign`, { user_id: userId });
      return response;
    } catch (error) {
      console.error(`❌ Failed to assign worker:`, error.message);
      throw error;
    }
  }

  /**
   * Unassign worker from project (supervisor only)
   */
  async unassignWorker(projectId, userId) {
    try {
      const response = await this.client.delete(`/projects/${projectId}/assign/${userId}`);
      return response;
    } catch (error) {
      console.error(`❌ Failed to unassign worker:`, error.message);
      throw error;
    }
  }

  /**
   * Delete project (supervisor or admin only). Creates backup before delete.
   */
  async delete(projectId) {
    try {
      const result = await this.client.delete(`/projects/${projectId}`);
      return result;
    } catch (error) {
      console.error(`❌ Failed to delete project ${projectId}:`, error.message);
      throw error;
    }
  }

  /**
   * Restore project from backup ZIP file (supervisor or admin only).
   */
  async restoreFromBackup(file) {
    const formData = new FormData();
    formData.append("file", file);

    const url = `${this.client.baseUrl}/projects/restore`;
    const token = this.client.authManager?.getToken();
    if (!token) throw new Error("Authentication required");

    const response = await fetch(url, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: formData,
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Restore failed");
    }
    return data;
  }
}

// Create global instance
const projectsService = new ProjectsService(window.apiClient || apiClient);

// Export
if (typeof window !== "undefined") {
  window.ProjectsService = ProjectsService;
  window.projectsService = projectsService;
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { ProjectsService, projectsService };
}
