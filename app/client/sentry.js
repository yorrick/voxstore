// Sentry Browser SDK initialization
// Fetches DSN from /api/config and loads the SDK from CDN.

(function () {
    var SDK_VERSION = "10.38.0";
    var SDK_URL = "https://browser.sentry-cdn.com/" + SDK_VERSION + "/bundle.min.js";

    function loadScript(src, onload) {
        var script = document.createElement("script");
        script.src = src;
        script.crossOrigin = "anonymous";
        script.onload = onload;
        script.onerror = function () {
            console.warn("[Sentry] Failed to load SDK from CDN");
        };
        document.head.appendChild(script);
    }

    function initSentry(dsn) {
        if (!window.Sentry) return;
        window.Sentry.init({ dsn: dsn });
        console.log("[Sentry] Initialized");
    }

    fetch("/api/config")
        .then(function (res) {
            return res.json();
        })
        .then(function (config) {
            if (!config.sentry_dsn) {
                console.log("[Sentry] No DSN configured, error tracking disabled");
                return;
            }
            loadScript(SDK_URL, function () {
                initSentry(config.sentry_dsn);
            });
        })
        .catch(function () {
            console.warn("[Sentry] Failed to fetch config");
        });
})();
