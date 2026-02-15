/**
 * Vue.js Application with OpenSeadragon Integration
 * Provides high-performance tile-based viewing of floor plans
 */

const { createApp } = Vue;

// API_BASE is now imported from auth.js

/**
 * MarkerManager - Handles all marker operations with OpenSeadragon
 * Uses MouseTracker for reliable event handling across all devices
 */
class MarkerManager {
  constructor(viewer, vueInstance) {
    this.viewer = viewer;
    this.vue = vueInstance;
    this.markers = new Map(); // id -> {overlay, tracker, data, element}
    this.selectedMarker = null;

    // Click detection settings
    this.clickTimeThreshold = 300; // ms
    this.clickDistThreshold = 8; // pixels

    console.log("🎯 MarkerManager initialized");
  }

  /**
   * Add a new marker for a work log
   */
  addMarker(log) {
    if (!this.viewer || !this.viewer.world.getItemCount()) {
      console.warn("🚫 Cannot add marker: viewer not ready");
      return false;
    }

    console.log(
      `📍 Adding marker for log ${log.id}: ${log.worker_name} - ${log.work_type}`
    );

    // Create marker element
    const element = this.createMarkerElement(log);

    // Calculate viewport coordinates
    const viewportPoint = this.logCoordsToViewport(log);

    // Add overlay to viewer
    const overlay = this.viewer.addOverlay({
      element: element,
      location: viewportPoint,
      placement: OpenSeadragon.Placement.CENTER,
      checkResize: false,
      rotationMode: OpenSeadragon.OverlayRotationMode.NO_ROTATION,
    });

    // Create MouseTracker for this marker
    const tracker = new OpenSeadragon.MouseTracker({
      element: element,
      clickTimeThreshold: this.clickTimeThreshold,
      clickDistThreshold: this.clickDistThreshold,

      enterHandler: (event) => {
        this.onMarkerEnter(log.id, event);
      },

      leaveHandler: (event) => {
        this.onMarkerExit(log.id, event);
      },

      clickHandler: (event) => {
        this.onMarkerClick(log.id, event);
      },

      dragHandler: (event) => {
        // Prevent accidental drags
        event.preventDefaultAction = true;
      },
    });

    // Store all marker data
    this.markers.set(log.id, {
      overlay: overlay,
      tracker: tracker,
      data: log,
      element: element,
      viewportPoint: viewportPoint,
    });

    console.log(`✅ Marker ${log.id} added successfully`);
    return true;
  }

  /**
   * Remove a marker
   */
  removeMarker(logId) {
    const marker = this.markers.get(logId);
    if (!marker) {
      console.warn(`🚫 Marker ${logId} not found for removal`);
      return false;
    }

    console.log(`🗑️ Removing marker ${logId}`);

    // Clean up MouseTracker
    if (marker.tracker) {
      marker.tracker.destroy();
    }

    // Remove overlay from viewer
    if (this.viewer && marker.element) {
      this.viewer.removeOverlay(marker.element);
    }

    // Clear selection if this was selected
    if (this.selectedMarker === logId) {
      this.selectedMarker = null;
    }

    // Remove from map
    this.markers.delete(logId);

    console.log(`✅ Marker ${logId} removed successfully`);
    return true;
  }

  /**
   * Update marker data and visual representation
   */
  updateMarker(log) {
    const marker = this.markers.get(log.id);
    if (!marker) {
      console.warn(`🚫 Marker ${log.id} not found for update`);
      return false;
    }

    console.log(`📝 Updating marker ${log.id}`);

    // Update stored data
    marker.data = log;

    // Update visual appearance
    this.updateMarkerElement(marker.element, log);

    // Update position if coordinates changed
    const newViewportPoint = this.logCoordsToViewport(log);
    if (
      newViewportPoint.x !== marker.viewportPoint.x ||
      newViewportPoint.y !== marker.viewportPoint.y
    ) {
      marker.viewportPoint = newViewportPoint;
      this.viewer.updateOverlay(marker.element, newViewportPoint);
    }

    console.log(`✅ Marker ${log.id} updated successfully`);
    return true;
  }

  /**
   * Clear all markers
   */
  clearAllMarkers() {
    console.log(`🧹 Clearing ${this.markers.size} markers`);

    for (const [logId, marker] of this.markers) {
      // Clean up MouseTracker
      if (marker.tracker) {
        marker.tracker.destroy();
      }

      // Remove overlay
      if (this.viewer && marker.element) {
        this.viewer.removeOverlay(marker.element);
      }
    }

    this.markers.clear();
    this.selectedMarker = null;

    console.log("✅ All markers cleared");
  }

  /**
   * Create DOM element for marker
   */
  createMarkerElement(log) {
    const element = document.createElement("div");
    element.className = "work-marker-overlay";
    element.style.cssText = `
      background: ${this.vue.getWorkTypeColor(log.work_type)};
      border: 2px solid white;
      border-radius: 50%;
      width: 20px;
      height: 20px;
      cursor: pointer;
      transition: all 0.2s ease;
      box-shadow: 0 2px 4px rgba(0,0,0,0.3);
      z-index: 10;
    `;
    element.title = `${log.worker_name} - ${log.work_type}`;
    element.setAttribute("data-log-id", log.id);

    return element;
  }

  /**
   * Update marker element appearance
   */
  updateMarkerElement(element, log) {
    element.style.background = this.vue.getWorkTypeColor(log.work_type);
    element.title = `${log.worker_name} - ${log.work_type}`;
  }

  /**
   * Convert log coordinates to viewport coordinates
   */
  logCoordsToViewport(log) {
    if (!this.viewer.world.getItemCount()) {
      return new OpenSeadragon.Point(0, 0);
    }

    const tiledImage = this.viewer.world.getItemAt(0);
    const imageRect = tiledImage.getContentSize();

    // Convert percentage coordinates (0-1) to image coordinates
    const imagePoint = new OpenSeadragon.Point(
      log.x_coord * imageRect.x,
      log.y_coord * imageRect.y
    );

    // Convert to viewport coordinates
    return tiledImage.imageToViewportCoordinates(imagePoint);
  }

  /**
   * Handle marker mouse enter
   */
  onMarkerEnter(logId, event) {
    const marker = this.markers.get(logId);
    if (!marker) return;

    console.log(`🖱️ Mouse enter marker ${logId}`);

    // Add hover effect
    marker.element.style.transform = "scale(1.2)";
    marker.element.style.boxShadow = "0 3px 8px rgba(0,0,0,0.4)";
    marker.element.style.zIndex = "15";
  }

  /**
   * Handle marker mouse exit
   */
  onMarkerExit(logId, event) {
    const marker = this.markers.get(logId);
    if (!marker) return;

    console.log(`🖱️ Mouse exit marker ${logId}`);

    // Remove hover effect
    marker.element.style.transform = "scale(1)";
    marker.element.style.boxShadow = "0 2px 4px rgba(0,0,0,0.3)";
    marker.element.style.zIndex = "10";
  }

  /**
   * Handle marker click - this is the reliable click detection
   */
  onMarkerClick(logId, event) {
    const marker = this.markers.get(logId);
    if (!marker) return;

    console.log(`🎯 Marker ${logId} clicked! Opening details modal`);
    console.log(
      `📋 Worker: ${marker.data.worker_name}, Type: ${marker.data.work_type}`
    );

    // Prevent canvas click from firing
    event.preventDefaultAction = true;

    // Set selected marker
    this.selectedMarker = logId;

    // Show details modal via Vue instance
    this.vue.showLogDetails(marker.data);
  }

  /**
   * Get marker by log ID
   */
  getMarker(logId) {
    return this.markers.get(logId);
  }

  /**
   * Get all markers
   */
  getAllMarkers() {
    return Array.from(this.markers.values());
  }
}

createApp({
  data() {
    return {
      // View management
      currentView: "map",

      // Floor data
      floors: [],
      selectedFloor: null,

      // OpenSeadragon viewer instance
      viewer: null,

      // Tile generation status
      tileStatuses: {},
      tileGenerationStatus: null,

      // Work logs
      currentFloorLogs: [],
      allLogs: [],

      // Modals
      showModal: false,
      showDetailsModal: false,
      selectedLogDetails: null,
      clickCoordinates: null,

      // Edit mode tracking
      editMode: false,
      editingLog: null,

      // New/Edit log form
      newLog: {
        floor_id: null,
        x_coord: 0,
        y_coord: 0,
        work_date: new Date().toISOString().split("T")[0],
        worker_name: "",
        work_type: "",
        description: "",
      },

      // Admin dashboard
      stats: {
        total_logs: 0,
        recent_logs: 0,
        logs_by_floor: [],
        work_types: [],
      },
      filters: {
        floor_id: "",
        start_date: "",
        end_date: "",
      },

      // Batch generation
      batchGenerating: false,
      batchResults: [],

      // MarkerManager instance
      markerManager: null,

      // Critical Sector Drawer instance
      sectorDrawer: null,

      // Interaction Mode - 'normal' or 'drawing-sector'
      interactionMode: "normal",

      // Critical Sectors
      allSectors: [],
      currentFloorSectors: [],
      sectorsVisible: true,
      showSectorModal: false,
      showSectorDetailsModal: false,
      selectedSectorDetails: null,
      newSector: {
        sector_name: "",
        floor_id: null,
        priority: "standard",
        type: "",
        x_coord: 0,
        y_coord: 0,
        radius: 0.1,
      },

      // Date filtering
      selectedDate: new Date().toISOString().split("T")[0],
      dateFilterEnabled: false,

      // Authentication
      currentUser: null,
      isAuthenticated: false,

      // Sidebar navigation
      sidebarOpen: false,

      // Custom fullscreen mode
      isCustomFullscreen: false,

      // Collapsible sections
      sectionsExpanded: {
        floors: true,
        quickStats: true,
        mapControls: true,
        dateFilter: true,
        shortcuts: false,
        sectors: true,
      },

      // Chart instances for proper cleanup
      chartInstances: {
        workType: null,
        timeline: null,
      },
    };
  },

  watch: {
    // Initialize charts when switching to admin view
    currentView(newView) {
      if (newView === "admin") {
        console.log("📊 Dashboard view activated - initializing charts");
        this.initializeCharts();
      }
    },
  },

  beforeUnmount() {
    window.removeEventListener("auth:user-updated", this._onUserUpdated);
  },

  computed: {
    activeFloorsCount() {
      // Add null safety check to prevent errors when stats data isn't loaded yet
      return this.stats.logs_by_floor?.filter((f) => f.count > 0).length || 0;
    },

    // Sort floors in descending order for stacked display (highest floor at top)
    sortedFloors() {
      return [...this.floors].sort((a, b) => {
        // Extract floor numbers from names like "Floor 1", "Floor 2", etc.
        const aNum = parseInt(a.name.replace(/\D/g, "")) || 0;
        const bNum = parseInt(b.name.replace(/\D/g, "")) || 0;
        return bNum - aNum; // Descending order (Floor 6, Floor 5, Floor 4, etc.)
      });
    },

    // Get unique dates from current floor logs (sorted)
    availableDates() {
      if (!this.currentFloorLogs || this.currentFloorLogs.length === 0) {
        return [];
      }
      const dates = [
        ...new Set(this.currentFloorLogs.map((log) => log.work_date)),
      ];
      return dates.sort();
    },

    // Get earliest date with logs
    earliestDate() {
      return this.availableDates.length > 0 ? this.availableDates[0] : null;
    },

    // Get latest date with logs
    latestDate() {
      return this.availableDates.length > 0
        ? this.availableDates[this.availableDates.length - 1]
        : null;
    },

    // Check if there's a previous date available
    hasPreviousDate() {
      if (!this.dateFilterEnabled || this.availableDates.length === 0)
        return false;
      const currentIndex = this.availableDates.indexOf(this.selectedDate);
      return currentIndex > 0;
    },

    // Check if there's a next date available
    hasNextDate() {
      if (!this.dateFilterEnabled || this.availableDates.length === 0)
        return false;
      const currentIndex = this.availableDates.indexOf(this.selectedDate);
      return (
        currentIndex < this.availableDates.length - 1 && currentIndex !== -1
      );
    },

    // Filter logs by selected date
    filteredFloorLogs() {
      if (!this.dateFilterEnabled) {
        return this.currentFloorLogs;
      }
      return this.currentFloorLogs.filter(
        (log) => log.work_date === this.selectedDate
      );
    },

    // Get the logs to display (filtered or all)
    displayLogs() {
      return this.dateFilterEnabled
        ? this.filteredFloorLogs
        : this.currentFloorLogs;
    },

    // Check if user can manage critical sectors
    canManageSectors() {
      return (
        this.currentUser &&
        (this.currentUser.role === "supervisor" ||
          this.currentUser.role === "admin")
      );
    },

    // Check if in drawing mode
    isDrawingMode() {
      return this.interactionMode === "drawing-sector";
    },

    // Get mode display text
    modeDisplayText() {
      return this.isDrawingMode ? "Drawing Critical Sectors" : "Normal Mode";
    },
  },

  async mounted() {
    // Check authentication first
    const isAuthenticated = await requireAuth();
    if (!isAuthenticated) {
      return; // Will redirect to login
    }

    // Set current user from auth manager
    this.refreshCurrentUser();
    this.isAuthenticated = true;

    // Admin users land on dashboard view instead of map
    if (this.currentUser && this.currentUser.role === "admin") {
      this.currentView = "admin";
    }

    // Listen for auth user updates (e.g. after role change or token verify)
    this._onUserUpdated = () => this.refreshCurrentUser();
    window.addEventListener("auth:user-updated", this._onUserUpdated);

    console.log("🔐 User authenticated:", this.currentUser);

    await this.fetchFloors();
    await this.fetchStats();
    await this.fetchLogs();
    await this.checkAllTileStatuses();

    // Set up keyboard shortcuts for date navigation
    this.setupKeyboardShortcuts();

    // Listen for fullscreen changes
    this.setupFullscreenListener();

    // Set initial body class based on current view
    if (this.currentView === "map") {
      document.body.classList.add("map-view");
    }
  },

  methods: {
    refreshCurrentUser() {
      this.currentUser = authManager.getUser();
    },

    // API calls
    async fetchFloors() {
      try {
        console.log("🔍 Fetching floors with authentication...");
        const response = await fetchWithAuth(`${API_BASE}/floors`);
        if (response.ok) {
          this.floors = await response.json();
          console.log("✅ Floors loaded:", this.floors.length);
        } else {
          console.error("❌ Failed to fetch floors, status:", response.status);
        }
      } catch (error) {
        console.error("Error fetching floors:", error);
      }
    },

    async fetchStats() {
      try {
        console.log("📊 Fetching stats...");
        const response = await fetchWithAuth(`${API_BASE}/work-logs/dashboard`);
        if (response.ok) {
          this.stats = await response.json();
          console.log("✅ Stats loaded");
        } else {
          console.warn("Stats endpoint not available, using defaults");
          this.stats = {
            total_logs: this.allLogs.length,
            recent_logs: 0,
            logs_by_floor: [],
            work_types: [],
          };
        }
      } catch (error) {
        console.error("Error fetching stats:", error);
      }
    },

    async fetchLogs() {
      try {
        const params = new URLSearchParams();
        if (this.filters.floor_id)
          params.append("floor_id", this.filters.floor_id);
        if (this.filters.start_date)
          params.append("start_date", this.filters.start_date);
        if (this.filters.end_date)
          params.append("end_date", this.filters.end_date);

        console.log("📋 Fetching work logs...");
        const response = await fetchWithAuth(`${API_BASE}/work-logs?${params}`);
        if (response.ok) {
          this.allLogs = await response.json();
          console.log("✅ Work logs loaded:", this.allLogs.length);
        }
      } catch (error) {
        console.error("Error fetching logs:", error);
      }
    },

    async fetchFloorLogs(floorId) {
      try {
        console.log(`📋 Fetching logs for floor ${floorId}...`);
        const response = await fetchWithAuth(
          `${API_BASE}/work-logs?floor_id=${floorId}`
        );
        if (response.ok) {
          this.currentFloorLogs = await response.json();
          console.log("✅ Floor logs loaded:", this.currentFloorLogs.length);
          this.updateMarkerOverlays();
        }
      } catch (error) {
        console.error("Error fetching floor logs:", error);
      }
    },

    // Tile management
    async checkAllTileStatuses() {
      for (const floor of this.floors) {
        await this.checkTileStatus(floor.id);
      }
    },

    async checkTileStatus(floorId) {
      try {
        const response = await fetchWithAuth(
          `${API_BASE}/tiles/status/${floorId}`
        );
        if (response.ok) {
          const status = await response.json();
          this.tileStatuses[floorId] = status;
          return status;
        }
        return { tiles_exist: false };
      } catch (error) {
        console.error("Error checking tile status:", error);
        return { tiles_exist: false };
      }
    },

    async generateTilesForFloor(floorId) {
      this.tileGenerationStatus = { generating: true };

      try {
        const response = await fetchWithAuth(
          `${API_BASE}/tiles/generate/${floorId}`,
          {
            method: "POST",
          }
        );

        const result = await response.json();

        if (result.success) {
          this.tileGenerationStatus = { success: true };
          await this.checkTileStatus(floorId);

          // Load tiles after generation
          setTimeout(() => {
            this.loadFloorInViewer(this.selectedFloor);
            this.tileGenerationStatus = null;
          }, 1500);
        } else {
          this.tileGenerationStatus = {
            error: result.error || "Failed to generate tiles",
          };
        }
      } catch (error) {
        console.error("Error generating tiles:", error);
        this.tileGenerationStatus = {
          error: "Network error generating tiles",
        };
      }
    },

    async generateAllTiles() {
      this.batchGenerating = true;
      this.batchResults = [];

      try {
        const response = await fetchWithAuth(
          `${API_BASE}/tiles/batch-generate`,
          {
            method: "POST",
          }
        );

        const result = await response.json();
        this.batchResults = result.results || [];

        // Refresh tile statuses
        await this.checkAllTileStatuses();
      } catch (error) {
        console.error("Error in batch generation:", error);
        alert("Failed to generate tiles");
      } finally {
        this.batchGenerating = false;
      }
    },

    // OpenSeadragon viewer management
    async selectFloor(floor) {
      console.log("🏢 Selecting floor:", floor.name);
      this.selectedFloor = floor;

      // Fetch logs for this floor
      await this.fetchFloorLogs(floor.id);

      // Check tile status
      const status = await this.checkTileStatus(floor.id);

      if (status.tiles_exist) {
        // Tiles exist, load them
        await this.loadFloorInViewer(floor);
      } else {
        // Tiles don't exist - check if user can generate them
        const canGenerateTiles =
          this.currentUser &&
          (this.currentUser.role === "supervisor" ||
            this.currentUser.role === "admin");

        if (canGenerateTiles) {
          // User has permission - generate tiles
          console.log("🔑 User has permission to generate tiles");
          this.initializeViewer();
          await this.generateTilesForFloor(floor.id);
        } else {
          // User doesn't have permission
          console.warn("🚫 User lacks permission to generate tiles");
          this.initializeViewer();
          this.tileGenerationStatus = {
            error:
              "Tiles not available for this floor. Please contact a supervisor or admin to generate them.",
            noPermission: true,
          };
          alert(
            "Tiles for this floor have not been generated yet.\n\nPlease contact a supervisor or administrator to generate the floor tiles."
          );
        }
      }
    },

    initializeViewer() {
      console.log("🔧 Initializing viewer...");

      // Safely destroy existing viewer if any
      if (this.viewer) {
        try {
          console.log("🗑️ Destroying existing viewer");
          this.viewer.destroy();
        } catch (error) {
          console.warn("⚠️ Error destroying viewer:", error);
        }
        this.viewer = null;
      }

      // Ensure container exists and is ready
      const container = document.getElementById("openseadragon-viewer");
      if (!container) {
        console.error("❌ Viewer container not found!");
        return false;
      }

      // Clear the container safely
      try {
        while (container.firstChild) {
          container.removeChild(container.firstChild);
        }
        console.log("✅ Viewer container cleared");
      } catch (error) {
        console.warn("⚠️ Error clearing container:", error);
      }

      return true;
    },

    async loadFloorInViewer(floor) {
      console.log("📐 Loading floor in OpenSeadragon:", floor.name);

      // Initialize viewer safely
      const initSuccess = this.initializeViewer();
      if (!initSuccess) {
        console.error("❌ Failed to initialize viewer");
        alert("Failed to load map viewer. Please refresh the page.");
        return;
      }

      // Wait for DOM to be ready
      await this.$nextTick();

      // Verify container still exists
      const container = document.getElementById("openseadragon-viewer");
      if (!container) {
        console.error("❌ Viewer container disappeared!");
        alert("Map container not found. Please refresh the page.");
        return;
      }

      try {
        // Get authentication token for AJAX requests - use defensive retrieval
        const authToken =
          authManager?.getToken?.() ||
          localStorage.getItem("auth_token") ||
          sessionStorage.getItem("auth_token") ||
          "";

        if (!authToken) {
          console.error("❌ No auth token available for tile loading!");
          alert("Authentication token not found. Please log in again.");
          window.location.href = "login.html";
          return;
        }

        console.log(
          "🔑 Using auth token for tiles (length:",
          authToken.length,
          ")"
        );

        // PRE-FETCH DZI FILE WITH AUTHENTICATION
        console.log("📥 Pre-fetching DZI file with authentication...");
        const dziUrl = `${API_BASE}/tiles/${floor.id}/floor-${floor.id}.dzi`;
        const dziResponse = await fetchWithAuth(dziUrl);

        if (!dziResponse.ok) {
          throw new Error(`Failed to fetch DZI: ${dziResponse.status}`);
        }

        const dziXml = await dziResponse.text();
        console.log("✅ DZI file fetched successfully");

        // PARSE DZI XML
        const parser = new DOMParser();
        const doc = parser.parseFromString(dziXml, "text/xml");
        const imageElement = doc.querySelector("Image");
        const sizeElement = doc.querySelector("Size");

        if (!imageElement || !sizeElement) {
          throw new Error("Invalid DZI format");
        }

        const width = parseInt(sizeElement.getAttribute("Width"));
        const height = parseInt(sizeElement.getAttribute("Height"));
        const tileSize = parseInt(imageElement.getAttribute("TileSize"));
        const overlap = parseInt(imageElement.getAttribute("Overlap"));
        const format = imageElement.getAttribute("Format");

        console.log("📐 DZI parsed:", {
          width,
          height,
          tileSize,
          overlap,
          format,
        });

        // CREATE CUSTOM TILE SOURCE WITH AUTHENTICATION
        const tileSource = {
          width: width,
          height: height,
          tileSize: tileSize,
          tileOverlap: overlap,
          minLevel: 0,
          // CRITICAL: Include auth headers in TileSource for tile image requests
          ajaxHeaders: {
            Authorization: `Bearer ${authToken}`,
          },
          getTileUrl: function (level, x, y) {
            return `${API_BASE}/tiles/${floor.id}/floor-${floor.id}_files/${level}/${x}_${y}.${format}`;
          },
        };

        console.log("🎨 Custom TileSource created with auth headers");

        // OVERRIDE OpenSeadragon's AJAX mechanism to always include auth headers
        const originalMakeAjaxRequest = OpenSeadragon.makeAjaxRequest;
        OpenSeadragon.makeAjaxRequest = function (options) {
          options.headers = options.headers || {};
          if (!options.headers["Authorization"]) {
            options.headers["Authorization"] = `Bearer ${authToken}`;
          }
          return originalMakeAjaxRequest.call(OpenSeadragon, options);
        };
        console.log(
          "🔐 OpenSeadragon AJAX override applied for authentication"
        );

        // Create OpenSeadragon viewer
        this.viewer = OpenSeadragon({
          id: "openseadragon-viewer",
          tileSources: tileSource,
          prefixUrl:
            "https://cdn.jsdelivr.net/npm/openseadragon@4.1.0/build/openseadragon/images/",

          // AJAX settings for authenticated tile loading
          loadTilesWithAjax: true,
          ajaxHeaders: {
            Authorization: `Bearer ${authToken}`,
          },

          // Navigation settings
          showNavigator: true,
          navigatorPosition: "TOP_RIGHT",
          navigatorSizeRatio: 0.15,

          // Zoom settings - optimized for ultra-HD tiles
          minZoomLevel: 0.5,
          maxZoomLevel: 20, // Increased for 1200 DPI content
          defaultZoomLevel: 1,
          zoomPerClick: 2,
          zoomPerScroll: 1.3, // Slightly faster zoom for better control
          zoomPerSecond: 1.2,

          // Display options
          visibilityRatio: 0.8, // Load more tiles for smoother experience
          constrainDuringPan: true,
          minPixelRatio: 0.5,
          maxPixelRatio: 2, // Support high-DPI displays

          // Performance optimizations
          immediateRender: true,
          useCanvas: true,
          preserveImageSizeOnResize: true,

          // Image quality settings - critical for sharp display
          smoothTileEdgesMinZoom: 3.5, // Adjusted for 512px tiles
          subPixelRoundingEnabled: false, // Disable for sharper rendering
          pixelDensityRatio: window.devicePixelRatio || 1,

          // Enhanced tile loading
          imageLoaderLimit: 6, // More concurrent loads
          timeout: 180000, // Longer timeout for larger tiles
          maxImageCacheCount: 500, // Cache more tiles

          // Smoother animations
          animationTime: 0.4, // Slightly faster
          springStiffness: 8.0, // More responsive

          // Blending settings
          blendTime: 0.2, // Faster blend
          alwaysBlend: false,
          placeholderFillStyle: "#f0f0f0",

          // Preloading strategy
          preload: true,
          preserveViewport: true,
          preserveOverlays: true,

          // UI Controls
          showRotationControl: false,
          showZoomControl: true,
          showHomeControl: true,
          showFullPageControl: true,

          // Gesture handling
          gestureSettingsMouse: {
            clickToZoom: false, // Disable click to zoom so we can handle clicks
          },
        });

        console.log("✅ OpenSeadragon viewer created successfully");

        // Add event handlers
        this.viewer.addHandler("open", () => {
          console.log("✅ OpenSeadragon viewer opened");
          const tiledImage = this.viewer.world.getItemAt(0);
          console.log("📐 Image info:", {
            width: tiledImage.getContentSize().x,
            height: tiledImage.getContentSize().y,
            levels: this.viewer.source.maxLevel + 1,
            tileSize: this.viewer.source.tileSize || 512,
            format: this.viewer.source.fileFormat || "png",
            dpi: Math.round((tiledImage.getContentSize().x / 11) * 1.2), // Approximate DPI
          });

          // Initialize MarkerManager
          this.markerManager = new MarkerManager(this.viewer, this);
          console.log("🎯 MarkerManager initialized for viewer");

          // Initialize CriticalSectorDrawer for all users (visibility for everyone, edit for supervisors/admins)
          this.sectorDrawer = new CriticalSectorDrawer(this.viewer, this);
          console.log("🎨 CriticalSectorDrawer initialized for viewer");

          // Load sectors for this floor
          this.loadSectorsOnMap();

          this.setupViewerEventHandlers();
          this.setupDebugHandlers();

          // UPDATED: Delay marker updates to ensure viewer and MarkerManager are ready
          setTimeout(() => {
            console.log("🕐 Delayed marker update after viewer ready");
            this.updateMarkerOverlays();
          }, 500);
        });

        // Add handler for when the world viewport changes (zoom/pan complete)
        this.viewer.addHandler("animation-finish", () => {
          // Refresh markers if they should be visible and MarkerManager is available
          if (
            this.markerManager &&
            this.currentFloorLogs.length > 0 &&
            this.markerManager.markers.size === 0
          ) {
            console.log("🔄 Refreshing markers after animation");
            this.updateMarkerOverlays();
          }
        });

        this.viewer.addHandler("open-failed", (event) => {
          console.error("❌ Failed to open viewer:", event);
          this.tileGenerationStatus = {
            error: "Failed to load tiles. Try regenerating.",
          };
        });
      } catch (error) {
        console.error("❌ Error creating OpenSeadragon viewer:", error);
        alert("Failed to create map viewer. Please refresh the page.");

        // Clean up on error
        if (this.viewer) {
          try {
            this.viewer.destroy();
          } catch (e) {
            console.warn("⚠️ Error during cleanup:", e);
          }
          this.viewer = null;
        }
      }
    },

    setupViewerEventHandlers() {
      if (!this.viewer) return;

      console.log("🔧 Setting up viewer event handlers");

      // SIMPLIFIED: Canvas clicks only for creating new logs
      // MarkerManager handles marker clicks via MouseTracker
      this.viewer.addHandler("canvas-click", (event) => {
        // Skip if in sector drawing mode - let sectorDrawer handle clicks
        if (this.interactionMode === "drawing-sector") {
          console.log("🎨 In drawing mode - skipping work log creation");
          return;
        }

        console.log("🖱️ Canvas click event fired:", {
          quick: event.quick,
          originalEvent: event.originalEvent?.target?.className,
        });

        // Only handle quick clicks (not drags)
        if (!event.quick) {
          console.log(
            "🚫 Canvas click ignored - was a drag, not a quick click"
          );
          return;
        }

        // Get click coordinates
        const webPoint = event.position;
        const viewportPoint = this.viewer.viewport.pointFromPixel(webPoint);
        const imagePoint =
          this.viewer.viewport.viewportToImageCoordinates(viewportPoint);

        // Get image dimensions
        const imageSize = this.viewer.world.getItemAt(0).getContentSize();

        // Convert to percentage coordinates
        const clickX = imagePoint.x / imageSize.x;
        const clickY = imagePoint.y / imageSize.y;

        console.log(
          `📍 Click position: ${(clickX * 100).toFixed(1)}%, ${(
            clickY * 100
          ).toFixed(1)}%`
        );

        // MarkerManager will handle marker clicks, so this is only for empty areas
        console.log("📝 Canvas clicked on empty area - opening create modal");
        this.openWorkLogModal(clickX, clickY);
      });
    },

    setupDebugHandlers() {
      if (!this.viewer) return;

      console.log("🔧 Debug handlers enabled (minimal logging)");

      // Only keep essential handlers for marker debugging
      // Removed verbose zoom, tile loading, and animation logging
    },

    updateMarkerOverlays() {
      if (!this.markerManager) {
        console.log("🚫 Cannot update markers: MarkerManager not initialized");
        return;
      }

      // Use filtered logs based on date selection
      const logsToDisplay = this.displayLogs;

      console.log(
        `🎯 Updating markers: ${logsToDisplay.length} of ${
          this.currentFloorLogs.length
        } logs (date filter: ${this.dateFilterEnabled ? "ON" : "OFF"})`
      );

      // Clear existing markers
      this.markerManager.clearAllMarkers();

      // Add markers for each log using MarkerManager
      logsToDisplay.forEach((log, index) => {
        console.log(
          `📍 Adding marker ${index + 1}: Floor ${log.floor_id}, Date ${
            log.work_date
          }, Position (${log.x_coord}, ${log.y_coord}), Type: ${log.work_type}`
        );
        this.markerManager.addMarker(log);
      });

      console.log(
        `✅ Added ${this.markerManager.markers.size} markers using MarkerManager`
      );
    },

    // Date Navigation Methods
    previousDay() {
      if (!this.hasPreviousDate) return;

      const currentIndex = this.availableDates.indexOf(this.selectedDate);
      if (currentIndex > 0) {
        this.selectedDate = this.availableDates[currentIndex - 1];
        console.log(`📅 Previous day: ${this.selectedDate}`);
        this.updateMarkerOverlays();
      }
    },

    nextDay() {
      if (!this.hasNextDate) return;

      const currentIndex = this.availableDates.indexOf(this.selectedDate);
      if (
        currentIndex < this.availableDates.length - 1 &&
        currentIndex !== -1
      ) {
        this.selectedDate = this.availableDates[currentIndex + 1];
        console.log(`📅 Next day: ${this.selectedDate}`);
        this.updateMarkerOverlays();
      }
    },

    goToToday() {
      const today = new Date().toISOString().split("T")[0];
      this.selectedDate = today;

      // Enable date filtering if not already enabled
      if (!this.dateFilterEnabled) {
        this.dateFilterEnabled = true;
      }

      console.log(`📅 Go to today: ${this.selectedDate}`);
      this.updateMarkerOverlays();
    },

    showAllDates() {
      this.dateFilterEnabled = !this.dateFilterEnabled;

      if (this.dateFilterEnabled) {
        // When enabling filter, show the most recent date with logs
        if (this.availableDates.length > 0) {
          this.selectedDate =
            this.availableDates[this.availableDates.length - 1];
        }
        console.log(`📅 Date filtering enabled, showing: ${this.selectedDate}`);
      } else {
        console.log("📅 Date filtering disabled, showing all dates");
      }

      this.updateMarkerOverlays();
    },

    onDateChange() {
      // Enable date filtering when user manually selects a date
      if (!this.dateFilterEnabled) {
        this.dateFilterEnabled = true;
      }

      console.log(`📅 Manual date change: ${this.selectedDate}`);
      this.updateMarkerOverlays();
    },

    formatDateFull(dateString) {
      const date = new Date(dateString);
      return date.toLocaleDateString("en-US", {
        weekday: "long",
        year: "numeric",
        month: "long",
        day: "numeric",
      });
    },

    // Keyboard shortcuts for date and floor navigation
    setupKeyboardShortcuts() {
      console.log("⌨️ Setting up keyboard shortcuts for navigation");

      document.addEventListener("keydown", (event) => {
        // Only handle shortcuts when not typing in inputs
        if (
          event.target.tagName === "INPUT" ||
          event.target.tagName === "TEXTAREA" ||
          event.target.tagName === "SELECT"
        ) {
          return;
        }

        // Only handle shortcuts when on map view
        if (this.currentView !== "map") {
          return;
        }

        // Floor navigation shortcuts (1-6)
        if (event.key >= "1" && event.key <= "6") {
          event.preventDefault();
          const floorNumber = parseInt(event.key);
          const floor = this.floors.find((f) =>
            f.name.includes(`Floor ${floorNumber}`)
          );
          if (floor) {
            this.selectFloor(floor);
            console.log(`⌨️ Keyboard shortcut: Jump to Floor ${floorNumber}`);
          }
          return;
        }

        // Date navigation shortcuts require a selected floor
        if (!this.selectedFloor || this.availableDates.length === 0) {
          return;
        }

        switch (event.key) {
          case "ArrowLeft":
            // Previous day
            if (this.dateFilterEnabled && this.hasPreviousDate) {
              event.preventDefault();
              this.previousDay();
            } else if (!this.dateFilterEnabled) {
              // Enable filtering and go to latest date
              event.preventDefault();
              this.dateFilterEnabled = true;
              this.selectedDate =
                this.availableDates[this.availableDates.length - 1];
              this.updateMarkerOverlays();
            }
            break;

          case "ArrowRight":
            // Next day
            if (this.dateFilterEnabled && this.hasNextDate) {
              event.preventDefault();
              this.nextDay();
            } else if (!this.dateFilterEnabled) {
              // Enable filtering and go to earliest date
              event.preventDefault();
              this.dateFilterEnabled = true;
              this.selectedDate = this.availableDates[0];
              this.updateMarkerOverlays();
            }
            break;

          case "t":
          case "T":
            // Go to today
            event.preventDefault();
            this.goToToday();
            console.log("⌨️ Keyboard shortcut: Go to today");
            break;

          case "a":
          case "A":
            // Toggle show all dates
            event.preventDefault();
            this.showAllDates();
            console.log(
              `⌨️ Keyboard shortcut: ${
                this.dateFilterEnabled
                  ? "Date filter enabled"
                  : "Show all dates"
              }`
            );
            break;

          case "Escape":
            // Disable date filtering (show all)
            if (this.dateFilterEnabled) {
              event.preventDefault();
              this.dateFilterEnabled = false;
              this.updateMarkerOverlays();
              console.log("⌨️ Keyboard shortcut: Show all dates (Escape)");
            }
            break;

          case "r":
          case "R":
            // Reset view
            event.preventDefault();
            if (this.viewer) {
              this.viewer.viewport.goHome();
              console.log("⌨️ Keyboard shortcut: Reset view");
            }
            break;

          case "f":
          case "F":
            // Toggle fullscreen
            event.preventDefault();
            if (this.viewer) {
              this.viewer.setFullScreen(!this.viewer.isFullPage());
              console.log("⌨️ Keyboard shortcut: Toggle fullscreen");
            }
            break;
        }
      });
    },

    // Work log management
    openWorkLogModal(x, y) {
      console.log(
        `📝 OPENING CREATE MODAL at position (${(x * 100).toFixed(1)}%, ${(
          y * 100
        ).toFixed(1)}%)`
      );
      this.clickCoordinates = { x, y };
      this.newLog = {
        floor_id: this.selectedFloor.id,
        x_coord: x,
        y_coord: y,
        work_date: new Date().toISOString().split("T")[0],
        worker_name: "",
        work_type: "",
        description: "",
      };
      this.showModal = true;
      console.log(`✅ Create modal opened - showModal = ${this.showModal}`);
    },

    async submitWorkLog() {
      try {
        let response;
        let successMessage;

        if (this.editMode && this.editingLog) {
          // UPDATE existing log
          response = await fetchWithAuth(
            `${API_BASE}/work-logs/${this.editingLog.id}`,
            {
              method: "PUT",
              headers: {
                "Content-Type": "application/json",
              },
              body: JSON.stringify(this.newLog),
            }
          );
          successMessage = "Work log updated";
        } else {
          // CREATE new log
          response = await fetchWithAuth(`${API_BASE}/work-logs`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify(this.newLog),
          });
          successMessage = "Work log created";
        }

        if (response.ok) {
          const result = await response.json();
          console.log(`✅ ${successMessage}:`, result);

          // Refresh data
          await this.fetchFloorLogs(this.selectedFloor.id);
          await this.fetchStats();

          // Close modal and reset edit mode
          this.closeModal();
        } else {
          const errorData = await response.json();
          alert(
            `Failed to save work log: ${errorData.error || "Unknown error"}`
          );
        }
      } catch (error) {
        console.error("Error saving work log:", error);
        alert("Error saving work log");
      }
    },

    closeModal() {
      this.showModal = false;
      this.clickCoordinates = null;
      this.editMode = false;
      this.editingLog = null;
    },

    // Edit existing work log
    editWorkLog(log) {
      console.log("📝 Editing work log:", log);

      this.editMode = true;
      this.editingLog = log;

      // Pre-populate form with existing data
      this.newLog = {
        floor_id: log.floor_id,
        x_coord: log.x_coord,
        y_coord: log.y_coord,
        work_date: log.work_date,
        worker_name: log.worker_name,
        work_type: log.work_type,
        description: log.description || "",
      };

      // Close details modal and open edit modal
      this.closeDetailsModal();
      this.showModal = true;
    },

    // Delete work log with confirmation
    async deleteWorkLog(log) {
      const confirmed = confirm(
        `Are you sure you want to delete this work log?\n\nWorker: ${log.worker_name}\nType: ${log.work_type}\nDate: ${log.work_date}\n\nThis action cannot be undone.`
      );

      if (!confirmed) return;

      try {
        console.log("🗑️ Deleting work log:", log);

        const response = await fetchWithAuth(
          `${API_BASE}/work-logs/${log.id}`,
          {
            method: "DELETE",
          }
        );

        if (response.ok) {
          const result = await response.json();
          console.log("✅ Work log deleted:", result);

          // Refresh data
          await this.fetchFloorLogs(this.selectedFloor.id);
          await this.fetchStats();

          // Close details modal
          this.closeDetailsModal();

          alert("Work log deleted successfully");
        } else {
          const errorData = await response.json();
          alert(
            `Failed to delete work log: ${errorData.error || "Unknown error"}`
          );
        }
      } catch (error) {
        console.error("Error deleting work log:", error);
        alert("Error deleting work log");
      }
    },

    showLogDetails(log) {
      console.log(`📋 SHOWING DETAILS MODAL for log:`, {
        id: log.id,
        worker: log.worker_name,
        workType: log.work_type,
        currentShowModal: this.showModal,
        currentShowDetailsModal: this.showDetailsModal,
      });

      this.selectedLogDetails = log;
      this.showDetailsModal = true;

      console.log(`📋 Details modal state after setting:`, {
        showDetailsModal: this.showDetailsModal,
        selectedLogDetails: this.selectedLogDetails
          ? this.selectedLogDetails.id
          : null,
      });
    },

    closeDetailsModal() {
      this.showDetailsModal = false;
      this.selectedLogDetails = null;
    },

    // Utility methods
    getWorkTypeColor(workType) {
      const colors = {
        Electrical: "#ef4444",
        Lighting: "#3b82f6",
        Maintenance: "#10b981",
        Installation: "#eab308",
        Inspection: "#8b5cf6",
        Repair: "#f97316",
        Other: "#8b5cf6",
      };
      return colors[workType] || "#6b7280";
    },

    getWorkTypeBadgeClass(workType) {
      const classes = {
        Electrical: "bg-red-100 text-red-800",
        Lighting: "bg-blue-100 text-blue-800",
        Maintenance: "bg-green-100 text-green-800",
        Installation: "bg-yellow-100 text-yellow-800",
        Inspection: "bg-purple-100 text-purple-800",
        Repair: "bg-orange-100 text-orange-800",
        Other: "bg-purple-100 text-purple-800",
      };
      return classes[workType] || "bg-gray-100 text-gray-800";
    },

    formatDate(dateString) {
      const date = new Date(dateString);
      return date.toLocaleDateString("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
      });
    },

    // Dashboard helper methods
    getFloorLogsCount(floorId) {
      return this.allLogs.filter((log) => log.floor_id === floorId).length;
    },

    // Chart initialization methods
    initializeCharts() {
      // Wait for DOM to be ready
      this.$nextTick(() => {
        this.createWorkTypeChart();
        this.createTimelineChart();
      });
    },

    createWorkTypeChart() {
      const canvas = document.getElementById("workTypeChart");
      if (!canvas) {
        console.warn("⚠️ workTypeChart canvas not found");
        return;
      }

      // Destroy existing chart instance to prevent memory leaks
      if (this.chartInstances.workType) {
        console.log("🗑️ Destroying existing workType chart");
        this.chartInstances.workType.destroy();
        this.chartInstances.workType = null;
      }

      const ctx = canvas.getContext("2d");

      // Prepare data - count logs by work type
      const workTypeCounts = {};
      this.allLogs.forEach((log) => {
        workTypeCounts[log.work_type] =
          (workTypeCounts[log.work_type] || 0) + 1;
      });

      const labels = Object.keys(workTypeCounts);
      const data = Object.values(workTypeCounts);
      const colors = labels.map((type) => this.getWorkTypeColor(type));

      // Store chart instance for proper cleanup
      this.chartInstances.workType = new Chart(ctx, {
        type: "doughnut",
        data: {
          labels: labels,
          datasets: [
            {
              data: data,
              backgroundColor: colors,
              borderColor: "#0a0a0f",
              borderWidth: 2,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              position: "bottom",
              labels: {
                color: "#ffd700",
                font: {
                  size: 12,
                },
                padding: 15,
              },
            },
            tooltip: {
              backgroundColor: "rgba(0, 0, 0, 0.8)",
              titleColor: "#ffd700",
              bodyColor: "#ffffff",
              borderColor: "#ffd700",
              borderWidth: 1,
            },
          },
        },
      });
    },

    createTimelineChart() {
      const canvas = document.getElementById("timelineChart");
      if (!canvas) {
        console.warn("⚠️ timelineChart canvas not found");
        return;
      }

      // Destroy existing chart instance to prevent memory leaks
      if (this.chartInstances.timeline) {
        console.log("🗑️ Destroying existing timeline chart");
        this.chartInstances.timeline.destroy();
        this.chartInstances.timeline = null;
      }

      const ctx = canvas.getContext("2d");

      // Get last 30 days of activity
      const today = new Date();
      const thirtyDaysAgo = new Date(today);
      thirtyDaysAgo.setDate(today.getDate() - 30);

      // Create date labels
      const labels = [];
      const dateCounts = {};

      for (let i = 0; i < 30; i++) {
        const date = new Date(thirtyDaysAgo);
        date.setDate(thirtyDaysAgo.getDate() + i);
        const dateStr = date.toISOString().split("T")[0];
        labels.push(dateStr);
        dateCounts[dateStr] = 0;
      }

      // Count logs per day
      this.allLogs.forEach((log) => {
        if (dateCounts.hasOwnProperty(log.work_date)) {
          dateCounts[log.work_date]++;
        }
      });

      const data = labels.map((date) => dateCounts[date]);

      // Store chart instance for proper cleanup
      this.chartInstances.timeline = new Chart(ctx, {
        type: "line",
        data: {
          labels: labels.map((date) => {
            const d = new Date(date);
            return d.toLocaleDateString("en-US", {
              month: "short",
              day: "numeric",
            });
          }),
          datasets: [
            {
              label: "Work Logs",
              data: data,
              borderColor: "#ffd700",
              backgroundColor: "rgba(255, 215, 0, 0.1)",
              tension: 0.4,
              fill: true,
              pointBackgroundColor: "#ffd700",
              pointBorderColor: "#0a0a0f",
              pointBorderWidth: 2,
              pointRadius: 3,
              pointHoverRadius: 5,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              display: false,
            },
            tooltip: {
              backgroundColor: "rgba(0, 0, 0, 0.8)",
              titleColor: "#ffd700",
              bodyColor: "#ffffff",
              borderColor: "#ffd700",
              borderWidth: 1,
            },
          },
          scales: {
            y: {
              beginAtZero: true,
              ticks: {
                color: "#9ca3af",
                stepSize: 1,
              },
              grid: {
                color: "rgba(255, 215, 0, 0.1)",
              },
            },
            x: {
              ticks: {
                color: "#9ca3af",
                maxRotation: 45,
                minRotation: 45,
              },
              grid: {
                color: "rgba(255, 215, 0, 0.05)",
              },
            },
          },
        },
      });
    },

    // Toggle section visibility
    toggleSection(sectionName) {
      this.sectionsExpanded[sectionName] = !this.sectionsExpanded[sectionName];
      console.log(
        `📂 Section ${sectionName}: ${
          this.sectionsExpanded[sectionName] ? "expanded" : "collapsed"
        }`
      );
    },

    // Sidebar navigation methods
    toggleSidebar() {
      this.sidebarOpen = !this.sidebarOpen;
      console.log(`☰ Sidebar ${this.sidebarOpen ? "opened" : "closed"}`);
    },

    closeSidebar() {
      this.sidebarOpen = false;
      console.log("☰ Sidebar closed via overlay");
    },

    setView(view) {
      console.log(`🔄 Switching to ${view} view`);

      // Role-based dashboard routing
      if (view === "admin") {
        // Check user role and redirect to appropriate dashboard
        if (this.currentUser && this.currentUser.role === "worker") {
          console.log(
            "🔄 Worker detected - redirecting to worker_dashboard.html"
          );
          window.location.href = "worker_dashboard.html";
          return;
        } else if (this.currentUser && this.currentUser.role === "supervisor") {
          console.log(
            "🔄 Supervisor detected - redirecting to supervisor_dashboard.html"
          );
          window.location.href = "supervisor_dashboard.html";
          return;
        }
        // Admin users continue to admin view
      }

      this.currentView = view;
      this.closeSidebar();

      // Toggle body class to control scrolling
      if (view === "map") {
        document.body.classList.add("map-view");
        // Reset scroll position when switching to map view
        window.scrollTo(0, 0);
      } else {
        document.body.classList.remove("map-view");
      }
    },

    // Setup fullscreen change listener
    setupFullscreenListener() {
      const fullscreenChangeHandler = () => {
        this.isCustomFullscreen = !!document.fullscreenElement;
        console.log(
          `⛶ Fullscreen state changed: ${
            this.isCustomFullscreen ? "ON" : "OFF"
          }`
        );
      };

      document.addEventListener("fullscreenchange", fullscreenChangeHandler);
      document.addEventListener(
        "webkitfullscreenchange",
        fullscreenChangeHandler
      );
      document.addEventListener("mozfullscreenchange", fullscreenChangeHandler);
      document.addEventListener("msfullscreenchange", fullscreenChangeHandler);
    },

    // Custom fullscreen toggle using native Fullscreen API
    async toggleCustomFullscreen() {
      const mapLayout = document.querySelector(".map-view-layout");

      if (!document.fullscreenElement) {
        // Enter native fullscreen
        try {
          if (mapLayout.requestFullscreen) {
            await mapLayout.requestFullscreen();
          } else if (mapLayout.webkitRequestFullscreen) {
            await mapLayout.webkitRequestFullscreen();
          } else if (mapLayout.msRequestFullscreen) {
            await mapLayout.msRequestFullscreen();
          }
          console.log("⛶ Requested native fullscreen mode");
        } catch (error) {
          console.error("Fullscreen request failed:", error);
        }
      } else {
        // Exit native fullscreen
        try {
          if (document.exitFullscreen) {
            await document.exitFullscreen();
          } else if (document.webkitExitFullscreen) {
            await document.webkitExitFullscreen();
          } else if (document.msExitFullscreen) {
            await document.msExitFullscreen();
          }
          console.log("⛶ Requested exit from fullscreen mode");
        } catch (error) {
          console.error("Exit fullscreen failed:", error);
        }
      }
    },

    // Critical Sector Management Methods
    async fetchCriticalSectors() {
      try {
        const response = await fetchWithAuth(`${API_BASE}/critical-sectors`);
        this.allSectors = await response.json();

        if (this.selectedFloor) {
          this.currentFloorSectors = this.allSectors.filter(
            (s) => s.floor_id === this.selectedFloor.id
          );
        }

        if (this.sectorDrawer && this.sectorsVisible) {
          this.updateSectorOverlays();
        }
      } catch (error) {
        console.error("Error fetching critical sectors:", error);
      }
    },

    startSectorDrawing(mode) {
      if (!this.sectorDrawer || !this.viewer) {
        console.warn("Cannot start drawing: viewer or drawer not ready");
        return;
      }
      console.log(`🎨 Starting sector drawing: ${mode}`);

      // Switch to drawing mode
      this.interactionMode = "drawing-sector";

      // Lock map interactions
      this.lockMapInteractions();

      // Start drawing
      const success = this.sectorDrawer.startDrawing(mode);
      if (!success) {
        // Reset mode if drawing failed to start
        this.interactionMode = "normal";
        this.unlockMapInteractions();
      }
    },

    cancelSectorDrawing() {
      if (this.sectorDrawer) {
        this.sectorDrawer.stopDrawing();
        console.log("Drawing cancelled");
      }

      // Unlock map interactions
      this.unlockMapInteractions();

      // Return to normal mode
      this.interactionMode = "normal";
    },

    lockMapInteractions() {
      if (!this.viewer) return;

      console.log("🔒 Locking map interactions for drawing mode");

      // Store original settings but DON'T disable mouse navigation
      // (we need it for canvas-click events)
      this._originalPanSettings = {
        panHorizontal: this.viewer.panHorizontal,
        panVertical: this.viewer.panVertical,
      };

      this._originalGestureSettings = {
        scrollToZoom: this.viewer.gestureSettingsMouse.scrollToZoom,
        clickToZoom: this.viewer.gestureSettingsMouse.clickToZoom,
        dblClickToZoom: this.viewer.gestureSettingsMouse.dblClickToZoom,
        pinchToZoom: this.viewer.gestureSettingsMouse.pinchToZoom,
      };

      // Disable panning
      this.viewer.panHorizontal = false;
      this.viewer.panVertical = false;

      // Disable all zoom gestures
      this.viewer.gestureSettingsMouse.scrollToZoom = false;
      this.viewer.gestureSettingsMouse.clickToZoom = false;
      this.viewer.gestureSettingsMouse.dblClickToZoom = false;
      this.viewer.gestureSettingsMouse.pinchToZoom = false;

      // Visual indication - change cursor
      if (this.viewer.element) {
        this.viewer.element.style.cursor = "crosshair";
      }

      console.log("✅ Map locked - drawing mode active (clicks still work)");
    },

    unlockMapInteractions() {
      if (!this.viewer) {
        console.warn("⚠️ Cannot unlock - viewer not available");
        return;
      }

      console.log("🔓 Unlocking map interactions");

      try {
        // Restore pan settings with validation
        if (this._originalPanSettings) {
          if (typeof this._originalPanSettings.panHorizontal !== "undefined") {
            this.viewer.panHorizontal = this._originalPanSettings.panHorizontal;
          }
          if (typeof this._originalPanSettings.panVertical !== "undefined") {
            this.viewer.panVertical = this._originalPanSettings.panVertical;
          }
          this._originalPanSettings = null;
        } else {
          // Fallback to default values if no stored settings
          this.viewer.panHorizontal = true;
          this.viewer.panVertical = true;
        }

        // Restore gesture settings with validation
        if (this._originalGestureSettings && this.viewer.gestureSettingsMouse) {
          if (
            typeof this._originalGestureSettings.scrollToZoom !== "undefined"
          ) {
            this.viewer.gestureSettingsMouse.scrollToZoom =
              this._originalGestureSettings.scrollToZoom;
          }
          if (
            typeof this._originalGestureSettings.clickToZoom !== "undefined"
          ) {
            this.viewer.gestureSettingsMouse.clickToZoom =
              this._originalGestureSettings.clickToZoom;
          }
          if (
            typeof this._originalGestureSettings.dblClickToZoom !== "undefined"
          ) {
            this.viewer.gestureSettingsMouse.dblClickToZoom =
              this._originalGestureSettings.dblClickToZoom;
          }
          if (
            typeof this._originalGestureSettings.pinchToZoom !== "undefined"
          ) {
            this.viewer.gestureSettingsMouse.pinchToZoom =
              this._originalGestureSettings.pinchToZoom;
          }
          this._originalGestureSettings = null;
        } else {
          // Fallback to enabled
          if (this.viewer.gestureSettingsMouse) {
            this.viewer.gestureSettingsMouse.scrollToZoom = true;
            this.viewer.gestureSettingsMouse.clickToZoom = false;
            this.viewer.gestureSettingsMouse.dblClickToZoom = false;
            this.viewer.gestureSettingsMouse.pinchToZoom = true;
          }
        }

        // Reset cursor safely
        if (this.viewer.element) {
          this.viewer.element.style.cursor = "default";
        }

        console.log("✅ Map unlocked - normal mode restored");
      } catch (error) {
        console.error("❌ Error unlocking map:", error);
        // Don't crash - just log the error
      }
    },

    toggleInteractionMode() {
      if (this.interactionMode === "normal") {
        // Can't toggle if no floor selected
        if (!this.selectedFloor) {
          alert("Please select a floor first");
          return;
        }
        alert(
          "Click a drawing button (Rectangle or Polygon) to start drawing critical sectors"
        );
      } else {
        // Cancel any active drawing
        this.cancelSectorDrawing();
      }
    },

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

    openSectorSaveModal(sectorData) {
      console.log("Opening sector save modal:", sectorData);

      // Build the newSector object with all necessary data
      this.newSector = {
        sector_name: "",
        floor_id: this.selectedFloor.id,
        priority: "standard",
        type: sectorData.type,
        x_coord: sectorData.x_coord,
        y_coord: sectorData.y_coord,
        radius: sectorData.radius,
      };

      // For rectangles, extract and include width and height from bounds
      if (sectorData.type === "rectangle" && sectorData.bounds) {
        this.newSector.width = sectorData.bounds.width;
        this.newSector.height = sectorData.bounds.height;
        console.log(
          `📐 Rectangle dimensions: ${sectorData.bounds.width.toFixed(
            3
          )} × ${sectorData.bounds.height.toFixed(3)}`
        );
      }

      // For polygons, include the points array
      if (sectorData.type === "polygon" && sectorData.points) {
        this.newSector.points = JSON.stringify(sectorData.points);
        console.log(`🔺 Polygon with ${sectorData.points.length} points`);
      }

      this.showSectorModal = true;

      // DON'T unlock yet - wait until modal is closed
      // Unlock will happen in submitCriticalSector or closeSectorModal
      this.interactionMode = "normal";
    },

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

      // Unlock map when modal closes (if still locked)
      if (
        this.interactionMode === "drawing-sector" ||
        this._originalPanSettings
      ) {
        this.unlockMapInteractions();
      }

      // Refresh viewer after modal DOM is removed (prevents map disappearing)
      this.$nextTick(() => {
        setTimeout(() => {
          if (this.viewer && this.viewer.element) {
            try {
              this.viewer.viewport.applyConstraints();
              if (typeof this.viewer.forceRedraw === "function") {
                this.viewer.forceRedraw();
              }
              if (typeof this.viewer.forceResize === "function") {
                this.viewer.forceResize();
              }
            } catch (e) {
              console.warn("Viewer refresh on modal close:", e);
            }
          }
        }, 100);
      });
    },

    async submitCriticalSector() {
      try {
        console.log("💾 Saving critical sector...");

        const response = await fetchWithAuth(`${API_BASE}/critical-sectors`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(this.newSector),
        });

        if (response.ok) {
          const result = await response.json();
          console.log("✅ Critical sector created:", result);

          // Close modal (this will unlock map)
          this.closeSectorModal();

          // Wait for Vue DOM update and let layout settle after modal closes
          await this.$nextTick();
          await new Promise((resolve) => setTimeout(resolve, 150));

          // Restore viewer visibility and notify OpenSeadragon of layout changes
          // (modal overlay can affect container dimensions; OSD needs to recalculate)
          if (this.viewer && this.viewer.element) {
            try {
              this.viewer.element.style.display = "";
              this.viewer.element.style.visibility = "visible";
              this.viewer.element.style.opacity = "1";
              this.viewer.viewport.applyConstraints();
              if (typeof this.viewer.forceRedraw === "function") {
                this.viewer.forceRedraw();
              }
              if (typeof this.viewer.forceResize === "function") {
                this.viewer.forceResize();
              }
            } catch (viewerError) {
              console.warn("⚠️ Viewer refresh:", viewerError);
            }
          }

          // Refresh sectors
          try {
            await this.fetchCriticalSectors();
            alert("Critical sector created successfully!");
          } catch (refreshError) {
            console.error("Error refreshing sectors:", refreshError);
            alert(
              "Sector created but failed to refresh. Please reload the page."
            );
          }
        } else {
          const errorData = await response.json();
          alert(
            `Failed to create sector: ${errorData.error || "Unknown error"}`
          );
        }
      } catch (error) {
        console.error("Error creating sector:", error);
        alert("Error creating critical sector");
      }
    },

    viewSectorDetails(sector) {
      console.log("View sector details:", sector);
      this.selectedSectorDetails = sector;
      this.showSectorDetailsModal = true;
    },

    closeSectorDetailsModal() {
      this.showSectorDetailsModal = false;
      this.selectedSectorDetails = null;
    },

    async deleteCriticalSector(sector) {
      const confirmed = confirm(
        `Are you sure you want to delete this critical sector?\n\nSector: ${sector.sector_name}\nPriority: ${sector.priority}\n\nThis action cannot be undone.`
      );

      if (!confirmed) return;

      try {
        console.log("🗑️ Deleting critical sector:", sector);

        const response = await fetchWithAuth(
          `${API_BASE}/critical-sectors/${sector.id}`,
          {
            method: "DELETE",
          }
        );

        if (response.ok) {
          console.log("✅ Critical sector deleted");

          // Refresh sectors
          await this.fetchCriticalSectors();

          // Close details modal
          this.closeSectorDetailsModal();

          alert("Critical sector deleted successfully");
        } else {
          const errorData = await response.json();
          alert(
            `Failed to delete sector: ${errorData.error || "Unknown error"}`
          );
        }
      } catch (error) {
        console.error("Error deleting critical sector:", error);
        alert("Error deleting critical sector");
      }
    },

    async clearAllSectorsOnFloor() {
      if (!this.selectedFloor || this.currentFloorSectors.length === 0) {
        return;
      }

      const confirmed = confirm(
        `⚠️ DELETE ALL SECTORS?\n\nThis will permanently delete ALL ${this.currentFloorSectors.length} critical sector(s) on ${this.selectedFloor.name}.\n\nThis action CANNOT be undone!\n\nAre you absolutely sure?`
      );

      if (!confirmed) return;

      // Double confirmation for safety
      const doubleConfirm = confirm(
        `Final confirmation:\n\nYou are about to delete ${this.currentFloorSectors.length} sector(s).\n\nClick OK to proceed or Cancel to abort.`
      );

      if (!doubleConfirm) return;

      try {
        console.log(
          `🗑️ Clearing all sectors on floor ${this.selectedFloor.id}`
        );

        let successCount = 0;
        let failCount = 0;

        // Delete each sector
        for (const sector of this.currentFloorSectors) {
          try {
            const response = await fetchWithAuth(
              `${API_BASE}/critical-sectors/${sector.id}`,
              { method: "DELETE" }
            );

            if (response.ok) {
              successCount++;
              console.log(
                `✅ Deleted sector ${sector.id}: ${sector.sector_name}`
              );
            } else {
              failCount++;
              // Handle 401/403 without triggering logout
              if (response.status === 401 || response.status === 403) {
                console.error(`❌ Permission denied for sector ${sector.id}`);
              } else {
                console.error(
                  `❌ Failed to delete sector ${sector.id}: ${response.status}`
                );
              }
            }
          } catch (error) {
            // Catch authentication errors without propagating to avoid logout
            if (
              error.message &&
              error.message.includes("Authentication expired")
            ) {
              console.error(`❌ Authentication error - stopping deletion`);
              break; // Stop deletion loop if auth actually expired
            }
            failCount++;
            console.error(`❌ Error deleting sector ${sector.id}:`, error);
          }
        }

        // Refresh sectors list
        await this.fetchCriticalSectors();

        // Show results
        if (failCount === 0) {
          alert(`✅ Successfully deleted all ${successCount} sector(s)!`);
        } else {
          alert(
            `Completed with mixed results:\n\n✅ Deleted: ${successCount}\n❌ Failed: ${failCount}\n\nPlease refresh the page if sectors still appear.`
          );
        }

        console.log(
          `✅ Clear operation complete: ${successCount} deleted, ${failCount} failed`
        );
      } catch (error) {
        console.error("❌ Error clearing sectors:", error);
        alert("Error clearing sectors. Please try again.");
      }
    },

    async loadSectorsOnMap() {
      if (!this.selectedFloor || !this.sectorDrawer) {
        return;
      }
      await this.fetchCriticalSectors();
      if (this.sectorsVisible) {
        this.updateSectorOverlays();
      }
    },

    updateSectorOverlays() {
      if (!this.sectorDrawer || !this.sectorsVisible) {
        return;
      }

      // Safety check - ensure viewer still exists
      if (
        !this.viewer ||
        !this.viewer.world ||
        !this.viewer.world.getItemCount()
      ) {
        console.warn("⚠️ Cannot update sectors - viewer not ready");
        return;
      }

      try {
        console.log(
          `🎨 Updating sector overlays: ${this.currentFloorSectors.length} sectors`
        );
        this.sectorDrawer.clearAllSectors();
        this.currentFloorSectors.forEach((sector) => {
          try {
            this.sectorDrawer.displaySector(sector);
          } catch (err) {
            console.error(`❌ Error displaying sector ${sector.id}:`, err);
          }
        });
        console.log(`✅ Displayed ${this.sectorDrawer.sectors.size} sectors`);
      } catch (error) {
        console.error("❌ Error updating sector overlays:", error);
      }
    },

    // Authentication methods
    async logout() {
      console.log("🚪 Logging out user:", this.currentUser.username);
      await authManager.logout();
    },
  },

  beforeUnmount() {
    // Cleanup viewer when component is destroyed
    if (this.viewer) {
      this.viewer.destroy();
    }
  },
}).mount("#app");

console.log("🚀 OpenSeadragon Electrician Work Log App initialized");
