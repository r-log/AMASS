/**
 * Shared dashboard Vue components for worker, supervisor, and admin dashboards.
 * Usage: app.component('StatCard', window.DashboardComponents.StatCard);
 */

(function () {
    const StatCard = {
        props: {
            value: { type: [Number, String], default: 0 },
            label: { type: String, required: true },
            variant: { type: String, default: '' } // '', 'success', 'warning', 'critical'
        },
        template: `
            <div :class="['stat-card', variant ? variant : '']">
                <div class="stat-value">{{ value }}</div>
                <div class="stat-label">{{ label }}</div>
            </div>
        `
    };

    window.DashboardComponents = {
        StatCard,
        register(app) {
            // Register both PascalCase and kebab-case so it works in
            // in-DOM templates (HTML lowercases tag names to "statcard").
            app.component('StatCard', StatCard);
            app.component('stat-card', StatCard);
        }
    };
})();
