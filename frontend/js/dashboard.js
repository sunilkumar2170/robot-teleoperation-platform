/**
 * Dashboard UI Event Handling & Interaction Controller
 * ----------------------------------------------------
 * Connects DOM controls, keyboard teleoperation shortcuts,
 * fault injection sliders, and Linux telemetry streams.
 */
class TeleopDashboard {
    constructor(wsClient, robotRenderer, metricsTracker) {
        this.ws = wsClient;
        this.renderer = robotRenderer;
        this.metrics = metricsTracker;
        this.currentSpeed = 1.0;
        this.isReplaying = false;

        this._bindControls();
        this._bindKeyboard();
        this._bindSliders();
        this._bindSessions();
        this._startPolling();
    }

    _bindControls() {
        // D-Pad buttons
        document.getElementById("btn-fwd")?.addEventListener("click", () => this._send("MOVE_FORWARD"));
        document.getElementById("btn-bwd")?.addEventListener("click", () => this._send("MOVE_BACKWARD"));
        document.getElementById("btn-left")?.addEventListener("click", () => this._send("TURN_LEFT"));
        document.getElementById("btn-right")?.addEventListener("click", () => this._send("TURN_RIGHT"));
        document.getElementById("btn-stop")?.addEventListener("click", () => this._send("STOP"));

        // Emergency Stop & Reset
        const triggerEStop = async () => {
            try {
                await fetch("/api/robot/emergency-stop", { method: "POST" });
            } catch (e) {
                console.error(e);
            }
        };
        const triggerReset = async () => {
            try {
                await fetch("/api/robot/reset", { method: "POST" });
                this.renderer.clearTrail();
            } catch (e) {
                console.error(e);
            }
        };

        document.getElementById("btn-e-stop-top")?.addEventListener("click", triggerEStop);
        document.getElementById("btn-reset-top")?.addEventListener("click", triggerReset);

        // Clear logs
        document.getElementById("btn-clear-logs")?.addEventListener("click", () => {
            const term = document.getElementById("log-terminal");
            if (term) term.innerHTML = "";
        });
    }

    _send(commandType) {
        if (this.isReplaying) return;
        this.ws.sendCommand(commandType, this.currentSpeed);
    }

    _bindKeyboard() {
        window.addEventListener("keydown", (e) => {
            if (["INPUT", "SELECT", "TEXTAREA"].includes(e.target.tagName)) return;

            let handled = true;
            switch (e.code) {
                case "KeyW":
                case "ArrowUp":
                    this._send("MOVE_FORWARD");
                    break;
                case "KeyS":
                case "ArrowDown":
                    this._send("MOVE_BACKWARD");
                    break;
                case "KeyA":
                case "ArrowLeft":
                    this._send("TURN_LEFT");
                    break;
                case "KeyD":
                case "ArrowRight":
                    this._send("TURN_RIGHT");
                    break;
                case "Escape":
                    this._send("STOP");
                    break;
                case "Space":
                    fetch("/api/robot/emergency-stop", { method: "POST" });
                    break;
                default:
                    handled = false;
            }
            if (handled) e.preventDefault();
        });
    }

    _bindSliders() {
        // Speed slider
        const sSpeed = document.getElementById("slider-speed");
        const lSpeed = document.getElementById("lbl-speed-val");
        sSpeed?.addEventListener("input", (e) => {
            this.currentSpeed = parseFloat(e.target.value);
            if (lSpeed) lSpeed.textContent = `${this.currentSpeed.toFixed(1)}x`;
        });

        // Network Sliders
        const sLat = document.getElementById("slider-latency");
        const sJit = document.getElementById("slider-jitter");
        const sLoss = document.getElementById("slider-loss");

        const updateNetworkConditions = async () => {
            const payload = {
                latency_ms: parseFloat(sLat.value),
                jitter_ms: parseFloat(sJit.value),
                packet_loss_pct: parseFloat(sLoss.value),
            };

            document.getElementById("lbl-latency-val").textContent = `${payload.latency_ms} ms`;
            document.getElementById("lbl-jitter-val").textContent = `${payload.jitter_ms} ms`;
            document.getElementById("lbl-loss-val").textContent = `${payload.packet_loss_pct} %`;

            try {
                await fetch("/api/network/conditions", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload),
                });
            } catch (err) {
                console.error("Failed to update network faults:", err);
            }
        };

        sLat?.addEventListener("change", updateNetworkConditions);
        sJit?.addEventListener("change", updateNetworkConditions);
        sLoss?.addEventListener("change", updateNetworkConditions);

        sLat?.addEventListener("input", (e) => {
            document.getElementById("lbl-latency-val").textContent = `${e.target.value} ms`;
        });
        sJit?.addEventListener("input", (e) => {
            document.getElementById("lbl-jitter-val").textContent = `${e.target.value} ms`;
        });
        sLoss?.addEventListener("input", (e) => {
            document.getElementById("lbl-loss-val").textContent = `${e.target.value} %`;
        });
    }

    _bindSessions() {
        const btnStart = document.getElementById("btn-session-start");
        const btnStop = document.getElementById("btn-session-stop");
        const btnList = document.getElementById("btn-session-list");
        const box = document.getElementById("session-replay-container");
        const listUl = document.getElementById("session-items-list");
        const badge = document.getElementById("badge-rec-status");

        btnStart?.addEventListener("click", async () => {
            const name = prompt("Enter session name:", `Run-${new Date().toISOString().substr(11, 8)}`);
            if (!name) return;
            try {
                const res = await fetch("/api/sessions/start", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ session_name: name }),
                });
                if (res.ok) {
                    btnStart.disabled = true;
                    btnStop.disabled = false;
                    badge.textContent = "RECORDING";
                    badge.className = "badge badge-danger";
                }
            } catch (e) {
                console.error(e);
            }
        });

        btnStop?.addEventListener("click", async () => {
            try {
                const res = await fetch("/api/sessions/stop", { method: "POST" });
                if (res.ok) {
                    btnStart.disabled = false;
                    btnStop.disabled = true;
                    badge.textContent = "SAVED";
                    badge.className = "badge badge-success";
                }
            } catch (e) {
                console.error(e);
            }
        });

        btnList?.addEventListener("click", async () => {
            box.classList.toggle("hidden");
            if (!box.classList.contains("hidden")) {
                try {
                    const res = await fetch("/api/sessions");
                    const sessions = await res.json();
                    listUl.innerHTML = "";
                    sessions.forEach((s) => {
                        const li = document.createElement("li");
                        li.innerHTML = `
                            <span>${s.session_name} (${s.event_count} evts)</span>
                            <button class="btn btn-primary" onclick="window.dashboard.replaySession('${s.session_id}')">Replay</button>
                        `;
                        listUl.appendChild(li);
                    });
                } catch (e) {
                    console.error(e);
                }
            }
        });
    }

    async replaySession(sessionId) {
        try {
            const res = await fetch(`/api/sessions/${sessionId}/replay`);
            const events = await res.json();
            if (!events || events.length === 0) {
                alert("No events recorded for this session.");
                return;
            }

            this.isReplaying = true;
            this.renderer.clearTrail();
            const badge = document.getElementById("badge-op-mode");
            if (badge) {
                badge.textContent = "REPLAYING";
                badge.className = "badge badge-warning";
            }

            for (const ev of events) {
                if (ev.event_type === "STATE" && ev.data) {
                    this.updateStateView(ev.data);
                }
                await new Promise((r) => setTimeout(r, 60)); // smooth playback pacing
            }

            this.isReplaying = false;
            if (badge) {
                badge.textContent = "IDLE";
                badge.className = "badge";
            }
            alert("Session replay complete.");
        } catch (e) {
            console.error("Replay error:", e);
            this.isReplaying = false;
        }
    }

    updateStateView(state) {
        this.renderer.render(state);

        // Update top badges
        const badgeMode = document.getElementById("badge-op-mode");
        if (badgeMode) {
            badgeMode.textContent = state.operating_mode;
            badgeMode.className = state.emergency_stop
                ? "badge badge-danger"
                : state.operating_mode === "MOVING"
                ? "badge badge-success"
                : "badge";
        }

        const arenaCoords = document.getElementById("arena-coords");
        const deg = (state.orientation * 180 / Math.PI).toFixed(1);
        if (arenaCoords) {
            arenaCoords.textContent = `X: ${state.x.toFixed(2)}m | Y: ${state.y.toFixed(2)}m | HDG: ${deg}°`;
        }

        // Telemetry cards
        document.getElementById("val-pos").textContent = `${state.x.toFixed(2)}, ${state.y.toFixed(2)} m`;
        document.getElementById("val-heading").textContent = `${deg}° (${state.orientation.toFixed(2)} rad)`;
        document.getElementById("val-linear").textContent = `${state.linear_velocity.toFixed(2)} m/s`;
        document.getElementById("val-angular").textContent = `${state.angular_velocity.toFixed(2)} rad/s`;
        document.getElementById("val-battery").textContent = `${state.battery_percentage.toFixed(1)} %`;
        document.getElementById("val-seq").textContent = `${state.last_sequence_number}`;
    }

    _startPolling() {
        // Poll Linux diagnostics and application logs every 2 seconds
        setInterval(() => this._fetchDiagnostics(), 2000);
        setInterval(() => this._fetchLogs(), 2000);
    }

    async _fetchDiagnostics() {
        try {
            const res = await fetch("/api/system/diagnostics");
            if (!res.ok) return;
            const diag = await res.json();

            // Header indicators
            document.getElementById("hdr-cpu").textContent = `${diag.resources.cpu_percent.toFixed(0)} %`;
            document.getElementById("hdr-ram").textContent = `${diag.process.memory_rss_mb.toFixed(0)} MB`;

            // System tiles
            document.getElementById("sys-pid").textContent = diag.process.pid;
            const uptimeMins = (diag.process.uptime_seconds / 60).toFixed(1);
            document.getElementById("sys-uptime").textContent = `${uptimeMins}m`;
            document.getElementById("sys-proc-cpu").textContent = `${diag.process.cpu_percent.toFixed(1)} %`;
            document.getElementById("sys-rss").textContent = `${diag.process.memory_rss_mb.toFixed(1)} MB`;
            document.getElementById("sys-mem-used").textContent = `${diag.resources.memory_used_percent.toFixed(0)} %`;
            document.getElementById("sys-port").textContent = diag.network.port_listening ? "ACTIVE (8000)" : "LISTENING";
        } catch (e) {
            // Handled silently
        }
    }

    async _fetchLogs() {
        const filter = document.getElementById("log-filter-level")?.value || "";
        const url = filter ? `/api/logs?limit=30&level=${filter}` : `/api/logs?limit=30`;
        try {
            const res = await fetch(url);
            if (!res.ok) return;
            const logs = await res.json();
            const term = document.getElementById("log-terminal");
            if (!term) return;

            term.innerHTML = "";
            logs.forEach((item) => {
                const row = document.createElement("div");
                row.className = "log-row";
                row.innerHTML = `
                    <span class="log-ts">${item.time_str.split(" ")[1]}</span>
                    <span class="log-lvl lvl-${item.level}">[${item.level}]</span>
                    <span>${item.message}</span>
                `;
                term.appendChild(row);
            });
            term.scrollTop = term.scrollHeight;
        } catch (e) {
            // Handled silently
        }
    }
}

window.TeleopDashboard = TeleopDashboard;
