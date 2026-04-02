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
