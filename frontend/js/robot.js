/**
 * 2D Robot Canvas Renderer
 * ------------------------
 * Renders the authoritative robot state on HTML5 Canvas:
 *  - Arena boundary box (-50m to +50m)
 *  - Metric grid with origin axes
 *  - Smooth differential-drive body with heading arrow
 *  - Fading motion trajectory trail
 *  - Emergency-stop visual lockout indicator
 */
class RobotRenderer {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas ? this.canvas.getContext("2d") : null;
        this.bounds = 50.0; // ±50 metres
        this.trail = [];
        this.maxTrailLength = 150;
        this.lastState = null;
    }

    worldToScreen(x, y) {
        if (!this.canvas) return { px: 0, py: 0 };
        const w = this.canvas.width;
        const h = this.canvas.height;
        const px = ((x + this.bounds) / (2 * this.bounds)) * w;
        const py = h - ((y + this.bounds) / (2 * this.bounds)) * h;
        return { px, py };
    }

    render(state) {
        if (!this.ctx || !state) return;
        this.lastState = state;
        const ctx = this.ctx;
        const w = this.canvas.width;
        const h = this.canvas.height;

        // Add to motion trail
        this.trail.push({ x: state.x, y: state.y });
        if (this.trail.length > this.maxTrailLength) {
            this.trail.shift();
        }

        // 1. Clear background
        ctx.fillStyle = "#030712";
        ctx.fillRect(0, 0, w, h);

        // 2. Draw Grid (every 10 m)
        ctx.strokeStyle = "#1f2937";
        ctx.lineWidth = 1;
        for (let gx = -40; gx <= 40; gx += 10) {
            const { px } = this.worldToScreen(gx, 0);
            ctx.beginPath();
            ctx.moveTo(px, 0);
            ctx.lineTo(px, h);
            ctx.stroke();
        }
        for (let gy = -40; gy <= 40; gy += 10) {
            const { py } = this.worldToScreen(0, gy);
            ctx.beginPath();
            ctx.moveTo(0, py);
            ctx.lineTo(w, py);
            ctx.stroke();
        }

        // 3. Coordinate Axes & Origin Cross
        const origin = this.worldToScreen(0, 0);
        ctx.strokeStyle = "#374151";
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(origin.px - 8, origin.py);
        ctx.lineTo(origin.px + 8, origin.py);
        ctx.moveTo(origin.px, origin.py - 8);
        ctx.lineTo(origin.px, origin.py + 8);
        ctx.stroke();

        // 4. Boundary Box
        ctx.strokeStyle = state.emergency_stop ? "#ef4444" : "#4b5563";
        ctx.lineWidth = 2;
        ctx.strokeRect(1, 1, w - 2, h - 2);

        // 5. Draw Motion Trail
        if (this.trail.length > 1) {
            ctx.lineWidth = 2;
            for (let i = 1; i < this.trail.length; i++) {
                const p0 = this.worldToScreen(this.trail[i - 1].x, this.trail[i - 1].y);
                const p1 = this.worldToScreen(this.trail[i].x, this.trail[i].y);
                const alpha = (i / this.trail.length) * 0.7;
                ctx.strokeStyle = `rgba(56, 189, 248, ${alpha})`;
                ctx.beginPath();
                ctx.moveTo(p0.px, p0.py);
                ctx.lineTo(p1.px, p1.py);
                ctx.stroke();
            }
        }

        // 6. Draw Robot Body
        const robotPos = this.worldToScreen(state.x, state.y);
        const radius = 14;

        ctx.save();
        ctx.translate(robotPos.px, robotPos.py);

        // Body circle
        ctx.beginPath();
        ctx.arc(0, 0, radius, 0, Math.PI * 2);
        if (state.emergency_stop) {
            ctx.fillStyle = "#ef4444";
            ctx.shadowColor = "#ef4444";
            ctx.shadowBlur = 15;
        } else if (state.operating_mode === "MOVING") {
            ctx.fillStyle = "#38bdf8";
            ctx.shadowColor = "#38bdf8";
            ctx.shadowBlur = 10;
        } else {
            ctx.fillStyle = "#0284c7";
            ctx.shadowBlur = 0;
        }
        ctx.fill();
        ctx.lineWidth = 2;
        ctx.strokeStyle = "#ffffff";
        ctx.stroke();
        ctx.shadowBlur = 0;

        // Heading arrow (screen Y is inverted: angle in radians)
        const angle = -state.orientation;
        const arrowLength = radius + 10;
        const tipX = Math.cos(angle) * arrowLength;
        const tipY = Math.sin(angle) * arrowLength;

        ctx.strokeStyle = "#10b981";
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.moveTo(0, 0);
        ctx.lineTo(tipX, tipY);
        ctx.stroke();

        // Arrow head
        const headLen = 6;
        ctx.fillStyle = "#10b981";
        ctx.beginPath();
        ctx.moveTo(tipX, tipY);
        ctx.lineTo(
            tipX - headLen * Math.cos(angle - Math.PI / 6),
            tipY - headLen * Math.sin(angle - Math.PI / 6)
        );
        ctx.lineTo(
            tipX - headLen * Math.cos(angle + Math.PI / 6),
            tipY - headLen * Math.sin(angle + Math.PI / 6)
        );
        ctx.closePath();
        ctx.fill();

        ctx.restore();

        // 7. Emergency Stop Watermark
        if (state.emergency_stop) {
            ctx.fillStyle = "rgba(239, 68, 68, 0.85)";
            ctx.font = "bold 18px monospace";
            ctx.textAlign = "center";
            ctx.fillText("EMERGENCY STOP ENGAGED", w / 2, 35);
        }
    }

    clearTrail() {
        this.trail = [];
    }
}

window.RobotRenderer = RobotRenderer;
