/**
 * Critical Sector Integration Methods
 * Add these methods to the Vue app in app-openseadragon.js
 */

// Add to computed properties:
const sectorComputedProperties = {
  // Check if user can manage critical sectors
  canManageSectors() {
    return (
      this.currentUser &&
      (this.currentUser.role === "supervisor" ||
        this.currentUser.role === "admin")
    );
  },
};

// Add these methods to the methods object:
const sectorMethods = {
  // Fetch critical sectors
  async fetchCriticalSectors() {
    try {
      const response = await fetchWithAuth(`${API_BASE}/critical-sectors`);
      this.allSectors = await response.json();

      // Filter sectors for current floor
      if (this.selectedFloor) {
        this.currentFloorSectors = this.allSectors.filter(
          (s) => s.floor_id === this.selectedFloor.id
        );
      }

      // Update map display if drawer is ready
      if (this.sectorDrawer && this.sectorsVisible) {
        this.updateSectorOverlays();
      }
    } catch (error) {
      console.error("Error fetching critical sectors:", error);
    }
  },

  // Start sector drawing
  startSectorDrawing(mode) {
    if (!this.sectorDrawer || !this.viewer) {
      console.warn("Cannot start drawing: viewer or drawer not ready");
      return;
    }

    console.log(`🎨 Starting sector drawing: ${mode}`);
    this.sectorDrawer.startDrawing(mode);
  },

  // Cancel sector drawing
  cancelSectorDrawing() {
    if (this.sectorDrawer) {
      this.sectorDrawer.stopDrawing();
      console.log("Drawing cancelled");
    }
  },

  // Toggle sector visibility
  toggleSectorVisibility() {
    this.sectorsVisible = !this.sectorsVisible;

    if (this.sectorsVisible) {
      this.updateSectorOverlays();
    } else {
      if (this.sectorDrawer) {
        this.sectorDrawer.clearAllSectors();
      }
    }

    console.log(`Sectors ${this.sectorsVisible ? "shown" : "hidden"}`);
  },

  // Open sector save modal (called by drawer)
  openSectorSaveModal(sectorData) {
    console.log("Opening sector save modal:", sectorData);

    this.newSector = {
      sector_name: "",
      floor_id: this.selectedFloor.id,
      priority: "standard",
      type: sectorData.type,
      x_coord: sectorData.x_coord,
      y_coord: sectorData.y_coord,
      radius: sectorData.radius,
      // Include polygon points for polygon type
      points: sectorData.points ? JSON.stringify(sectorData.points) : null,
      // Include width and height for rectangle type
      width: sectorData.bounds?.width || null,
      height: sectorData.bounds?.height || null,
    };

    this.showSectorModal = true;
  },

  // Close sector modal
  closeSectorModal() {
    this.showSectorModal = false;
    this.newSector = {
      sector_name: "",
      floor_id: null,
      priority: "standard",
      type: "",
      x_coord: 0,
      y_coord: 0,
      radius: 0.1,
    };
  },

  // Submit critical sector
  async submitCriticalSector() {
    try {
      const response = await fetchWithAuth(`${API_BASE}/critical-sectors`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(this.newSector),
      });

      if (response.ok) {
        const result = await response.json();
        console.log("✅ Critical sector created:", result);

        // Refresh sectors
        await this.fetchCriticalSectors();

        // Close modal
        this.closeSectorModal();

        alert("Critical sector created successfully!");
      } else {
        const errorData = await response.json();
        alert(`Failed to create sector: ${errorData.error || "Unknown error"}`);
      }
    } catch (error) {
      console.error("Error creating sector:", error);
      alert("Error creating critical sector");
    }
  },

  // View sector details
  viewSectorDetails(sector) {
    console.log("View sector details:", sector);
    alert(
      `Critical Sector: ${sector.sector_name}\nPriority: ${sector.priority}\nFloor: ${sector.floor_name}`
    );
  },

  // Load sectors on map
  async loadSectorsOnMap() {
    if (!this.selectedFloor || !this.sectorDrawer) {
      return;
    }

    // Fetch sectors for this floor
    await this.fetchCriticalSectors();

    // Display them if visible
    if (this.sectorsVisible) {
      this.updateSectorOverlays();
    }
  },

  // Update sector overlays
  updateSectorOverlays() {
    if (!this.sectorDrawer || !this.sectorsVisible) {
      return;
    }

    console.log(
      `🎨 Updating sector overlays: ${this.currentFloorSectors.length} sectors`
    );

    // Clear existing sectors
    this.sectorDrawer.clearAllSectors();

    // Add sectors for current floor
    this.currentFloorSectors.forEach((sector) => {
      this.sectorDrawer.displaySector(sector);
    });

    console.log(`✅ Displayed ${this.sectorDrawer.sectors.size} sectors`);
  },
};

// Instructions for integration:
// 1. Add sectorComputedProperties to the computed object
// 2. Add sectorMethods to the methods object
// 3. Initialize sectorDrawer in the viewer 'open' handler
// 4. Call fetchCriticalSectors() in selectFloor()
// 5. Add sector data properties to data() return object
