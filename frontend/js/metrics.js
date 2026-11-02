/**
 * Latency Chart & Telemetry Metrics Module
 * ----------------------------------------
 * Plots real-time Round-Trip Time (RTT) on HTML5 Canvas and
 * formats telemetry counters.
 */
class TeleopMetrics {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas ? this.canvas.getContext("2d") : null;
        this.rttHistory = [];
        this.maxPoints = 50;
    }

    addSample(rttMs) {
        this.rttHistory.push(rttMs);
        if (this.rttHistory.length > this.maxPoints) {
            this.rttHistory.shift();
        }
        this.renderChart();
    }

    renderChart() {
        if (!this.ctx || this.rttHistory.length < 2) return;
        const ctx = this.ctx;
        const w = this.canvas.width;
        const h = this.canvas.height;

        // Background
        ctx.fillStyle = "#030712";
        ctx.fillRect(0, 0, w, h);

        // Calculate dynamic scale
        const maxVal = Math.max(100, ...this.rttHistory) * 1.2;

        // Grid lines
        ctx.strokeStyle = "#1f2937";
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(0, h * 0.5);
        ctx.lineTo(w, h * 0.5);
        ctx.stroke();

        // Line plot
        ctx.strokeStyle = "#38bdf8";
        ctx.lineWidth = 2;
        ctx.beginPath();

        const stepX = w / (this.maxPoints - 1);
        const startIndex = this.maxPoints - this.rttHistory.length;

        for (let i = 0; i < this.rttHistory.length; i++) {
            const x = (startIndex + i) * stepX;
            const y = h - (this.rttHistory[i] / maxVal) * h;
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        }
        ctx.stroke();

        // Fill area under curve
        ctx.lineTo((startIndex + this.rttHistory.length - 1) * stepX, h);
        ctx.lineTo(startIndex * stepX, h);
        ctx.fillStyle = "rgba(56, 189, 248, 0.15)";
        ctx.fill();

        // Value text
        const latest = this.rttHistory[this.rttHistory.length - 1];
        ctx.fillStyle = "#9ca3af";
        ctx.font = "10px monospace";
        ctx.textAlign = "right";
        ctx.fillText(`${latest.toFixed(1)} ms`, w - 5, 12);
    }
}

window.TeleopMetrics = TeleopMetrics;
