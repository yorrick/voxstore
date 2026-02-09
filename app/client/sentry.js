// Sentry Browser SDK initialization
// In production, load the Sentry SDK from CDN and configure here.
// For now, this is a placeholder that will be replaced with the real SDK.

(function () {
    // Replace with your actual Sentry DSN
    var SENTRY_DSN = "";

    if (!SENTRY_DSN) {
        console.log("[Sentry] No DSN configured, error tracking disabled");
        return;
    }

    // Load Sentry SDK dynamically
    var script = document.createElement("script");
    script.src = "https://browser.sentry-cdn.com/8.49.0/bundle.min.js";
    script.crossOrigin = "anonymous";
    script.onload = function () {
        if (window.Sentry) {
            window.Sentry.init({
                dsn: SENTRY_DSN,
                tracesSampleRate: 1.0,
                replaysSessionSampleRate: 0.1,
                replaysOnErrorSampleRate: 1.0,
            });
            console.log("[Sentry] Initialized");
        }
    };
    document.head.appendChild(script);
})();
