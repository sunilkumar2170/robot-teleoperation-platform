/**
 * Telemetry and latency charting module for Teleop-Sim.
 */
class TeleopMetrics {
    constructor() {
        this.rttHistory = [];
    }
}
window.TeleopMetrics = TeleopMetrics;
