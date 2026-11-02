/**
 * Main Application Bootstrap for Teleop-Sim
 * -----------------------------------------
 * Initializes the renderer, WebSocket connection, metrics tracker,
 * and attaches callbacks.
 */
document.addEventListener("DOMContentLoaded", () => {
    // 1. Initialize components
    const renderer = new RobotRenderer("robot-canvas");
    const metrics = new TeleopMetrics("rtt-chart");
    const ws = new TeleopWebSocket();
    const dashboard = new TeleopDashboard(ws, renderer, metrics);

    window.dashboard = dashboard;

    // 2. Wire WebSocket callbacks
    ws.callbacks.onState = (state) => {
        dashboard.updateStateView(state);
    };

    ws.callbacks.onAck = (ack, delayMs) => {
        const statusVal = document.getElementById("val-seq");
        if (statusVal) statusVal.textContent = ack.sequence_number;
    };

    ws.callbacks.onDrop = (dropInfo) => {
        console.warn("Command dropped due to simulated packet loss:", dropInfo);
    };

    ws.callbacks.onPong = (pongData) => {
        metrics.addSample(pongData.rtt_ms);
        const hdrRtt = document.getElementById("hdr-rtt");
        if (hdrRtt) hdrRtt.textContent = `${pongData.rtt_ms.toFixed(0)} ms`;
    };

    ws.callbacks.onStatusChange = (connected) => {
        const badge = document.getElementById("badge-connection");
        const banner = document.getElementById("connection-banner");
        if (connected) {
            if (badge) {
                badge.textContent = "WS CONNECTED";
                badge.className = "badge badge-success";
            }
            if (banner) banner.classList.add("hidden");
        } else {
            if (badge) {
                badge.textContent = "WS DISCONNECTED";
                badge.className = "badge badge-danger";
            }
            if (banner) banner.classList.remove("hidden");
        }
    };

    // 3. Connect WebSocket
    ws.connect();
});
