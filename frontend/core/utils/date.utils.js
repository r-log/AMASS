/**
 * Date Utilities
 * Helper functions for date formatting and manipulation
 */

const DateUtils = {
  /**
   * Format date to display format (e.g., "Jan 15, 2024")
   */
  formatDate(dateString) {
    if (!dateString) return "-";

    const date = new Date(dateString);
    return date.toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  },

  /**
   * Format date to full display (e.g., "Monday, January 15, 2024")
   */
  formatDateFull(dateString) {
    if (!dateString) return "-";

    const date = new Date(dateString);
    return date.toLocaleDateString("en-US", {
      weekday: "long",
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  },

  /**
   * Format date to input format (YYYY-MM-DD)
   */
  formatDateInput(date = new Date()) {
    return date.toISOString().split("T")[0];
  },

  /**
   * Get today's date in input format
   */
  getToday() {
    return this.formatDateInput(new Date());
  },

  /**
   * Parse date string to Date object
   */
  parseDate(dateString) {
    return new Date(dateString);
  },

  /**
   * Check if date is today
   */
  isToday(dateString) {
    const date = this.parseDate(dateString);
    const today = new Date();

    return (
      date.getDate() === today.getDate() &&
      date.getMonth() === today.getMonth() &&
      date.getFullYear() === today.getFullYear()
    );
  },

  /**
   * Check if date is in the past
   */
  isPast(dateString) {
    const date = this.parseDate(dateString);
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    return date < today;
  },

  /**
   * Check if date is in the future
   */
  isFuture(dateString) {
    const date = this.parseDate(dateString);
    const today = new Date();
    today.setHours(23, 59, 59, 999);

    return date > today;
  },

  /**
   * Get relative time string (e.g., "2 days ago", "in 3 days")
   */
  getRelativeTime(dateString) {
    const date = this.parseDate(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return "Today";
    if (diffDays === 1) return "Yesterday";
    if (diffDays === -1) return "Tomorrow";
    if (diffDays > 1) return `${diffDays} days ago`;
    if (diffDays < -1) return `in ${Math.abs(diffDays)} days`;

    return this.formatDate(dateString);
  },

  /**
   * Add days to a date
   */
  addDays(dateString, days) {
    const date = this.parseDate(dateString);
    date.setDate(date.getDate() + days);
    return this.formatDateInput(date);
  },

  /**
   * Subtract days from a date
   */
  subtractDays(dateString, days) {
    return this.addDays(dateString, -days);
  },

  /**
   * Get date range (start and end dates)
   */
  getDateRange(startDate, endDate) {
    const start = this.parseDate(startDate);
    const end = this.parseDate(endDate);
    const dates = [];

    const currentDate = new Date(start);
    while (currentDate <= end) {
      dates.push(this.formatDateInput(currentDate));
      currentDate.setDate(currentDate.getDate() + 1);
    }

    return dates;
  },

  /**
   * Get start of week
   */
  getStartOfWeek(date = new Date()) {
    const d = new Date(date);
    const day = d.getDay();
    const diff = d.getDate() - day;
    d.setDate(diff);
    return this.formatDateInput(d);
  },

  /**
   * Get end of week
   */
  getEndOfWeek(date = new Date()) {
    const d = new Date(date);
    const day = d.getDay();
    const diff = d.getDate() + (6 - day);
    d.setDate(diff);
    return this.formatDateInput(d);
  },

  /**
   * Get start of month
   */
  getStartOfMonth(date = new Date()) {
    const d = new Date(date);
    d.setDate(1);
    return this.formatDateInput(d);
  },

  /**
   * Get end of month
   */
  getEndOfMonth(date = new Date()) {
    const d = new Date(date);
    d.setMonth(d.getMonth() + 1);
    d.setDate(0);
    return this.formatDateInput(d);
  },

  /**
   * Compare two dates
   * Returns: -1 if date1 < date2, 0 if equal, 1 if date1 > date2
   */
  compareDates(date1, date2) {
    const d1 = this.parseDate(date1);
    const d2 = this.parseDate(date2);

    if (d1 < d2) return -1;
    if (d1 > d2) return 1;
    return 0;
  },

  /**
   * Sort array of dates
   */
  sortDates(dates, ascending = true) {
    return dates.sort((a, b) => {
      const comparison = this.compareDates(a, b);
      return ascending ? comparison : -comparison;
    });
  },

  /**
   * Get unique dates from array
   */
  getUniqueDates(dates) {
    return [...new Set(dates)];
  },

  /**
   * Validate date string
   */
  isValidDate(dateString) {
    const date = this.parseDate(dateString);
    return date instanceof Date && !isNaN(date);
  },
};

// Export for use in other modules
if (typeof module !== "undefined" && module.exports) {
  module.exports = DateUtils;
}

if (typeof window !== "undefined") {
  window.DateUtils = DateUtils;
}

console.log("📅 Date utilities loaded");
