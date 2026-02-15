/**
 * Critical Sector Drawer - OpenSeadragon Integration
 * Handles drawing, displaying, and managing critical sectors on floor plans
 */

class CriticalSectorDrawer {
  constructor(viewer, vueInstance) {
    this.viewer = viewer;
    this.vue = vueInstance;
    this.sectors = new Map(); // id -> {overlay, element, data}
    this.isDrawing = false;
    this.drawingMode = null; // 'circle', 'rectangle', 'polygon'
    this.currentDrawing = null;
    this.polygonPoints = [];
    this.tempOverlays = [];

    console.log("🎨 CriticalSectorDrawer initialized");
  }

  /**
   * Start drawing mode
   */
  startDrawing(mode) {
    if (!this.viewer || !this.viewer.world.getItemCount()) {
      console.warn("🚫 Cannot start drawing: viewer not ready");
      return false;
    }

    // Validate mode
    if (mode !== "rectangle" && mode !== "polygon") {
      console.error(`🚫 Invalid drawing mode: ${mode}`);
      return false;
    }

    this.drawingMode = mode;
    this.isDrawing = true;
    this.polygonPoints = [];
    this.currentDrawing = null;

    console.log(`🎨 Started drawing mode: ${mode}`);

    try {
      // Set up drawing handlers based on mode
      if (mode === "rectangle") {
        this.setupRectangleDrawing();
      } else if (mode === "polygon") {
        this.setupPolygonDrawing();
      }

      // Change cursor
      this.viewer.element.style.cursor = "crosshair";

      return true;
    } catch (error) {
      console.error("❌ Error starting drawing mode:", error);
      this.stopDrawing();
      return false;
    }
  }

  /**
   * Stop drawing mode
   */
  stopDrawing() {
    console.log("🛑 Stopping drawing mode");

    this.isDrawing = false;
    this.drawingMode = null;
    this.currentDrawing = null;
    this.polygonPoints = [];

    // Clear temporary overlays
    this.clearTempOverlays();

    // Reset cursor
    this.viewer.element.style.cursor = "default";

    // Remove drawing handlers
    this.removeDrawingHandlers();
  }

  /**
   * Setup rectangle drawing
   */
  setupRectangleDrawing() {
    let startPoint = null;

    this.drawingClickHandler = (event) => {
      try {
        if (!this.isDrawing || this.drawingMode !== "rectangle") return;

        const webPoint = event.position;
        const viewportPoint = this.viewer.viewport.pointFromPixel(webPoint);

        if (!startPoint) {
          // First click - set first corner
          startPoint = viewportPoint;
          console.log("🎯 Rectangle first corner set");

          const dotElement = this.createDotElement();
          this.viewer.addOverlay({
            element: dotElement,
            location: startPoint,
            placement: OpenSeadragon.Placement.CENTER,
          });
          this.tempOverlays.push({
            element: dotElement,
            isOSDOverlay: true,
          });
        } else {
          // Second click - set opposite corner and complete
          console.log("🎯 Rectangle second corner set");

          // Calculate rectangle bounds
          const imageStart = this.viewportToImageCoords(startPoint);
          const imageEnd = this.viewportToImageCoords(viewportPoint);

          const x = Math.min(imageStart.x, imageEnd.x);
          const y = Math.min(imageStart.y, imageEnd.y);
          const width = Math.abs(imageEnd.x - imageStart.x);
          const height = Math.abs(imageEnd.y - imageStart.y);

          // Calculate center and radius for storage
          const centerX = x + width / 2;
          const centerY = y + height / 2;
          const radius = Math.max(width, height) / 2;

          this.completeSectorDrawing({
            type: "rectangle",
            x_coord: centerX,
            y_coord: centerY,
            radius: radius,
            bounds: { x, y, width, height },
          });

          startPoint = null;
        }
      } catch (error) {
        console.error("❌ Error in rectangle drawing:", error);
        this.stopDrawing();
        alert("Error while drawing rectangle. Please try again.");
      }
    };

    this.viewer.addHandler("canvas-click", this.drawingClickHandler);
  }

  /**
   * Setup polygon drawing
   */
  setupPolygonDrawing() {
    this.drawingClickHandler = (event) => {
      try {
        if (!this.isDrawing || this.drawingMode !== "polygon") return;

        // Prevent event propagation to avoid conflicts
        event.preventDefaultAction = true;

        const webPoint = event.position;
        const viewportPoint = this.viewer.viewport.pointFromPixel(webPoint);

        // Check if we have 3+ points and clicked near the first point to close
        if (this.polygonPoints.length >= 3 && this.isNearFirstPoint(webPoint)) {
          console.log("🎯 Polygon closed by clicking first point");

          // Draw closing line
          this.drawPolygonLine(
            this.polygonPoints[this.polygonPoints.length - 1],
            this.polygonPoints[0]
          );

          // Complete the polygon
          this.completePolygon();
          return;
        }

        // Add point to polygon
        this.polygonPoints.push(viewportPoint);
        console.log(`🎯 Polygon point ${this.polygonPoints.length} added`);

        // Add visual dot (make first dot distinctive)
        const dotElement =
          this.polygonPoints.length === 1
            ? this.createStartDotElement()
            : this.createDotElement();

        this.viewer.addOverlay({
          element: dotElement,
          location: viewportPoint,
          placement: OpenSeadragon.Placement.CENTER,
        });
        this.tempOverlays.push({
          element: dotElement,
          isOSDOverlay: true,
        });

        // Draw connecting lines
        if (this.polygonPoints.length > 1) {
          this.drawPolygonLine(
            this.polygonPoints[this.polygonPoints.length - 2],
            this.polygonPoints[this.polygonPoints.length - 1]
          );
        }
      } catch (error) {
        console.error("❌ Error in polygon drawing:", error);
        this.stopDrawing();
        alert("Error while drawing polygon. Please try again.");
      }
    };

    this.viewer.addHandler("canvas-click", this.drawingClickHandler);
  }

  /**
   * Complete sector drawing and show save modal
   */
  completeSectorDrawing(sectorData) {
    try {
      console.log("✅ Sector drawing complete:", sectorData);

      // Clear temporary overlays
      this.clearTempOverlays();

      // Stop drawing mode
      this.stopDrawing();

      // Pass data to Vue component for saving
      this.vue.openSectorSaveModal(sectorData);
    } catch (error) {
      console.error("❌ Error completing sector drawing:", error);
      this.stopDrawing();
      alert("Error completing sector. Please try again.");
    }
  }

  /**
   * Display existing critical sector on map
   */
  displaySector(sector) {
    if (!this.viewer || !this.viewer.world.getItemCount()) {
      console.warn("🚫 Cannot display sector: viewer not ready");
      return false;
    }

    console.log(
      `🎨 Displaying sector ${sector.id}: ${sector.sector_name} (type: ${sector.type})`
    );

    let overlay;
    let viewportPoint;
    let element;

    // Calculate size and position based on sector type
    if (sector.type === "rectangle" && sector.width && sector.height) {
      // For rectangles: Use OpenSeadragon's native width/height scaling
      const viewportWidth = this.imageToViewportDistance(sector.width);
      const viewportHeight = this.imageToViewportDistanceY(sector.height);

      // Calculate top-left corner from center position
      const centerPoint = this.imageCoordsToViewport({
        x: sector.x_coord,
        y: sector.y_coord,
      });

      const topLeftPoint = new OpenSeadragon.Point(
        centerPoint.x - viewportWidth / 2,
        centerPoint.y - viewportHeight / 2
      );

      viewportPoint = topLeftPoint;

      // Create element without polygon points
      element = this.createSectorElement(sector, null);

      // Add overlay with viewport-based dimensions (auto-scales with zoom)
      overlay = this.viewer.addOverlay({
        element: element,
        location: topLeftPoint,
        width: viewportWidth,
        height: viewportHeight,
        placement: OpenSeadragon.Placement.TOP_LEFT,
        checkResize: false,
      });

      console.log(
        `📐 Rectangle: viewport size (${viewportWidth.toFixed(
          4
        )} × ${viewportHeight.toFixed(4)}) - auto-scales with zoom`
      );
    } else if (sector.type === "polygon" && sector.points) {
      // For polygons: Use actual polygon points with clip-path
      const imagePoints = JSON.parse(sector.points);

      // Calculate bounding box from polygon points
      const xs = imagePoints.map((p) => p.x);
      const ys = imagePoints.map((p) => p.y);
      const minX = Math.min(...xs);
      const minY = Math.min(...ys);
      const maxX = Math.max(...xs);
      const maxY = Math.max(...ys);

      const width = maxX - minX;
      const height = maxY - minY;

      // Convert to viewport coordinates
      const viewportWidth = this.imageToViewportDistance(width);
      const viewportHeight = this.imageToViewportDistanceY(height);

      const topLeft = this.imageCoordsToViewport({ x: minX, y: minY });
      viewportPoint = topLeft;

      // Convert polygon points to percentage coordinates within bounding box
      const polygonPercentages = imagePoints.map((p) => ({
        x: ((p.x - minX) / width) * 100,
        y: ((p.y - minY) / height) * 100,
      }));

      // Create element with polygon clip-path
      element = this.createSectorElement(sector, polygonPercentages);

      // Add overlay with viewport-based dimensions
      overlay = this.viewer.addOverlay({
        element: element,
        location: topLeft,
        width: viewportWidth,
        height: viewportHeight,
        placement: OpenSeadragon.Placement.TOP_LEFT,
        checkResize: false,
      });

      console.log(
        `📐 Polygon: ${
          imagePoints.length
        } points, viewport size (${viewportWidth.toFixed(
          4
        )} × ${viewportHeight.toFixed(4)})`
      );
    } else {
      // Fallback for circles or other types
      const centerPoint = this.imageCoordsToViewport({
        x: sector.x_coord,
        y: sector.y_coord,
      });

      const viewportRadius = this.imageToViewportDistance(sector.radius);
      const pixelRadius =
        this.viewer.viewport.pixelFromPoint(
          new OpenSeadragon.Point(centerPoint.x + viewportRadius, centerPoint.y)
        ).x - this.viewer.viewport.pixelFromPoint(centerPoint).x;

      element = this.createSectorElement(sector, null);
      element.style.width = `${pixelRadius * 2}px`;
      element.style.height = `${pixelRadius * 2}px`;

      viewportPoint = centerPoint;

      overlay = this.viewer.addOverlay({
        element: element,
        location: centerPoint,
        placement: OpenSeadragon.Placement.CENTER,
        checkResize: false,
      });

      console.log(`⭕ Circle size: ${pixelRadius * 2}px diameter`);
    }

    // Store sector data
    this.sectors.set(sector.id, {
      overlay: overlay,
      element: element,
      data: sector,
      viewportPoint: viewportPoint,
    });

    console.log(`✅ Sector ${sector.id} displayed`);
    return true;
  }

  /**
   * Remove sector from map
   */
  removeSector(sectorId) {
    const sector = this.sectors.get(sectorId);
    if (!sector) {
      console.warn(`🚫 Sector ${sectorId} not found for removal`);
      return false;
    }

    console.log(`🗑️ Removing sector ${sectorId}`);

    // Remove overlay
    if (this.viewer && sector.element) {
      this.viewer.removeOverlay(sector.element);
    }

    this.sectors.delete(sectorId);
    console.log(`✅ Sector ${sectorId} removed`);
    return true;
  }

  /**
   * Clear all sectors
   */
  clearAllSectors() {
    console.log(`🧹 Clearing ${this.sectors.size} sectors`);

    for (const [sectorId, sector] of this.sectors) {
      if (this.viewer && sector.element) {
        this.viewer.removeOverlay(sector.element);
      }
    }

    this.sectors.clear();
    console.log("✅ All sectors cleared");
  }

  /**
   * Create sector overlay element
   */
  createSectorElement(sector, polygonPercentages = null) {
    const element = document.createElement("div");
    element.className = "critical-sector-overlay";

    const priorityColors = {
      high: "rgba(239, 68, 68, 0.3)",
      medium: "rgba(245, 158, 11, 0.3)",
      standard: "rgba(16, 185, 129, 0.3)",
    };

    const borderColors = {
      high: "#ef4444",
      medium: "#f59e0b",
      standard: "#10b981",
    };

    // Different styling for different types
    let borderRadius = "8px";
    let clipPath = "";

    if (sector.type === "polygon" && polygonPercentages) {
      // For polygons: use clip-path to create the exact shape
      const polygonPoints = polygonPercentages
        .map((p) => `${p.x}% ${p.y}%`)
        .join(", ");
      clipPath = `polygon(${polygonPoints})`;
      borderRadius = "0"; // No border radius for polygons
    } else if (sector.type !== "rectangle") {
      borderRadius = "50%"; // Circle for other types
    }

    element.style.cssText = `
            background: ${
              priorityColors[sector.priority] || priorityColors.standard
            };
            border: 3px solid ${
              borderColors[sector.priority] || borderColors.standard
            };
            border-radius: ${borderRadius};
            ${clipPath ? `clip-path: ${clipPath};` : ""}
            cursor: pointer;
            transition: all 0.2s ease;
            pointer-events: auto;
            animation: pulse 2s infinite;
            position: relative;
        `;

    element.title = `${sector.sector_name} (${sector.priority}) - ${sector.type}`;
    element.setAttribute("data-sector-id", sector.id);

    // Add click handler for details (all users can view)
    element.addEventListener("click", (e) => {
      e.stopPropagation();
      this.vue.viewSectorDetails(sector);
    });

    // Create delete button only for supervisors/admins (hidden by default)
    if (this.vue.canManageSectors) {
      const deleteBtn = document.createElement("button");
      deleteBtn.innerHTML = "🗑️";
      deleteBtn.className = "sector-delete-btn";
      deleteBtn.style.cssText = `
            position: absolute;
            top: -12px;
            right: -12px;
            width: 28px;
            height: 28px;
            background: #ef4444;
            color: white;
            border: 2px solid white;
            border-radius: 50%;
            cursor: pointer;
            display: none;
            align-items: center;
            justify-content: center;
            font-size: 14px;
            z-index: 1000;
            box-shadow: 0 2px 4px rgba(0,0,0,0.3);
            transition: transform 0.2s ease;
        `;
      deleteBtn.title = "Delete sector";

      deleteBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        this.deleteSector(sector);
      });

      element.addEventListener("mouseenter", () => {
        deleteBtn.style.display = "flex";
      });

      element.addEventListener("mouseleave", () => {
        deleteBtn.style.display = "none";
      });

      deleteBtn.addEventListener("mouseenter", () => {
        deleteBtn.style.transform = "scale(1.2)";
      });

      deleteBtn.addEventListener("mouseleave", () => {
        deleteBtn.style.transform = "scale(1)";
      });

      element.appendChild(deleteBtn);
    }

    return element;
  }

  /**
   * Delete sector with confirmation
   */
  async deleteSector(sector) {
    const confirmed = confirm(
      `Delete this critical sector?\n\nName: ${sector.sector_name}\nPriority: ${sector.priority}\n\nThis cannot be undone.`
    );

    if (!confirmed) return;

    try {
      console.log("🗑️ Deleting sector:", sector.id);

      // Call Vue method to delete via API
      await this.vue.deleteCriticalSector(sector);
    } catch (error) {
      console.error("❌ Error deleting sector:", error);
      alert("Failed to delete sector. Please try again.");
    }
  }

  /**
   * Create dot element for drawing
   */
  createDotElement() {
    const element = document.createElement("div");
    element.style.cssText = `
            background: #ffd700;
            border: 2px solid white;
            border-radius: 50%;
            width: 10px;
            height: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.3);
            pointer-events: none;
        `;
    return element;
  }

  /**
   * Create distinctive start dot element for polygon first point
   */
  createStartDotElement() {
    const element = document.createElement("div");
    element.style.cssText = `
            background: #10b981;
            border: 3px solid white;
            border-radius: 50%;
            width: 16px;
            height: 16px;
            box-shadow: 0 3px 6px rgba(0,0,0,0.4);
            pointer-events: none;
            position: relative;
        `;
    element.title = "Click here to close polygon (after adding 3+ points)";
    return element;
  }

  /**
   * Check if click is near the first polygon point
   */
  isNearFirstPoint(webPoint) {
    if (this.polygonPoints.length === 0) return false;

    const firstPoint = this.polygonPoints[0];
    const firstPixel = this.viewer.viewport.pixelFromPoint(firstPoint);

    const distance = Math.sqrt(
      Math.pow(webPoint.x - firstPixel.x, 2) +
        Math.pow(webPoint.y - firstPixel.y, 2)
    );

    // 20 pixel threshold for "close enough"
    return distance <= 20;
  }

  /**
   * Complete polygon drawing
   */
  completePolygon() {
    try {
      if (this.polygonPoints.length < 3) {
        alert("A polygon must have at least 3 points");
        return;
      }

      console.log(
        `🎯 Polygon complete with ${this.polygonPoints.length} points`
      );

      // Convert points to image coordinates
      const imagePoints = this.polygonPoints.map((p) =>
        this.viewportToImageCoords(p)
      );

      // Calculate center and bounding circle
      const center = this.calculatePolygonCenter(imagePoints);
      const radius = this.calculatePolygonRadius(imagePoints, center);

      this.completeSectorDrawing({
        type: "polygon",
        x_coord: center.x,
        y_coord: center.y,
        radius: radius,
        points: imagePoints,
      });
    } catch (error) {
      console.error("❌ Error completing polygon:", error);
      this.stopDrawing();
      alert("Error completing polygon. Please try again.");
    }
  }

  /**
   * Draw line between polygon points
   */
  drawPolygonLine(start, end) {
    const element = document.createElement("div");

    const startPixel = this.viewer.viewport.pixelFromPoint(start);
    const endPixel = this.viewer.viewport.pixelFromPoint(end);

    const length = Math.sqrt(
      Math.pow(endPixel.x - startPixel.x, 2) +
        Math.pow(endPixel.y - startPixel.y, 2)
    );

    const angle =
      (Math.atan2(endPixel.y - startPixel.y, endPixel.x - startPixel.x) * 180) /
      Math.PI;

    element.style.cssText = `
            position: absolute;
            background: #ffd700;
            height: 2px;
            width: ${length}px;
            left: ${startPixel.x}px;
            top: ${startPixel.y}px;
            transform-origin: 0 0;
            transform: rotate(${angle}deg);
            pointer-events: none;
        `;

    this.viewer.element.appendChild(element);
    this.tempOverlays.push({ element: element, isOSDOverlay: false });
  }

  /**
   * Clear temporary drawing overlays
   */
  clearTempOverlays() {
    try {
      this.tempOverlays.forEach((item) => {
        try {
          const el = item.element;
          if (!el) return;

          // Only call removeOverlay for elements added via addOverlay.
          // Line elements are appended directly to viewer.element - calling
          // removeOverlay on them can corrupt OpenSeadragon's internal state.
          if (item.isOSDOverlay && this.viewer) {
            this.viewer.removeOverlay(el);
          } else if (el.parentNode) {
            el.parentNode.removeChild(el);
          }
        } catch (err) {
          console.warn("⚠️ Error clearing temp overlay:", err);
        }
      });
      this.tempOverlays = [];
    } catch (error) {
      console.error("❌ Error clearing temp overlays:", error);
      this.tempOverlays = [];
    }
  }

  /**
   * Remove drawing event handlers
   */
  removeDrawingHandlers() {
    if (this.drawingClickHandler) {
      this.viewer.removeHandler("canvas-click", this.drawingClickHandler);
      this.drawingClickHandler = null;
    }
    if (this.drawingDblClickHandler) {
      this.viewer.removeHandler(
        "canvas-double-click",
        this.drawingDblClickHandler
      );
      this.drawingDblClickHandler = null;
    }
  }

  /**
   * Coordinate conversion helpers
   */
  viewportToImageCoords(viewportPoint) {
    if (!this.viewer.world.getItemCount()) {
      return { x: 0, y: 0 };
    }

    const tiledImage = this.viewer.world.getItemAt(0);
    const imagePoint = tiledImage.viewportToImageCoordinates(viewportPoint);
    const imageSize = tiledImage.getContentSize();

    // Return as percentage (0-1)
    return {
      x: imagePoint.x / imageSize.x,
      y: imagePoint.y / imageSize.y,
    };
  }

  imageCoordsToViewport(imageCoords) {
    if (!this.viewer.world.getItemCount()) {
      return new OpenSeadragon.Point(0, 0);
    }

    const tiledImage = this.viewer.world.getItemAt(0);
    const imageSize = tiledImage.getContentSize();

    const imagePoint = new OpenSeadragon.Point(
      imageCoords.x * imageSize.x,
      imageCoords.y * imageSize.y
    );

    return tiledImage.imageToViewportCoordinates(imagePoint);
  }

  viewportToImageDistance(viewportDistance) {
    if (!this.viewer.world.getItemCount()) {
      return 0;
    }

    const tiledImage = this.viewer.world.getItemAt(0);
    const imageSize = tiledImage.getContentSize();

    // Convert viewport distance to image distance as percentage
    return (
      (viewportDistance * this.viewer.viewport.getContainerSize().x) /
      imageSize.x
    );
  }

  imageToViewportDistance(imageDistance) {
    if (!this.viewer.world.getItemCount()) {
      return 0;
    }

    const tiledImage = this.viewer.world.getItemAt(0);
    const imageSize = tiledImage.getContentSize();

    // Convert image distance (as percentage 0-1) to actual image pixels (X-axis)
    const imagePixels = imageDistance * imageSize.x;

    // Create two points in image space separated by the distance horizontally
    const point1 = new OpenSeadragon.Point(0, 0);
    const point2 = new OpenSeadragon.Point(imagePixels, 0);

    // Convert to viewport coordinates
    const viewportPoint1 = tiledImage.imageToViewportCoordinates(point1);
    const viewportPoint2 = tiledImage.imageToViewportCoordinates(point2);

    // Return the viewport distance (horizontal)
    return viewportPoint2.x - viewportPoint1.x;
  }

  imageToViewportDistanceY(imageDistance) {
    if (!this.viewer.world.getItemCount()) {
      return 0;
    }

    const tiledImage = this.viewer.world.getItemAt(0);
    const imageSize = tiledImage.getContentSize();

    // Convert image distance (as percentage 0-1) to actual image pixels (Y-axis)
    const imagePixels = imageDistance * imageSize.y;

    // Create two points in image space separated by the distance vertically
    const point1 = new OpenSeadragon.Point(0, 0);
    const point2 = new OpenSeadragon.Point(0, imagePixels);

    // Convert to viewport coordinates
    const viewportPoint1 = tiledImage.imageToViewportCoordinates(point1);
    const viewportPoint2 = tiledImage.imageToViewportCoordinates(point2);

    // Return the viewport distance (vertical)
    return viewportPoint2.y - viewportPoint1.y;
  }

  calculateDistance(point1, point2) {
    return Math.sqrt(
      Math.pow(point2.x - point1.x, 2) + Math.pow(point2.y - point1.y, 2)
    );
  }

  calculatePolygonCenter(points) {
    const sum = points.reduce(
      (acc, p) => ({
        x: acc.x + p.x,
        y: acc.y + p.y,
      }),
      { x: 0, y: 0 }
    );

    return {
      x: sum.x / points.length,
      y: sum.y / points.length,
    };
  }

  calculatePolygonRadius(points, center) {
    const distances = points.map((p) =>
      Math.sqrt(Math.pow(p.x - center.x, 2) + Math.pow(p.y - center.y, 2))
    );
    return Math.max(...distances);
  }
}

// Export for use in other modules
if (typeof module !== "undefined" && module.exports) {
  module.exports = CriticalSectorDrawer;
}
