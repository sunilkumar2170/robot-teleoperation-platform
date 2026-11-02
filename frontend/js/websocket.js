/**
 * Resilient WebSocket Client for Teleop-Sim
 * -----------------------------------------
 * Handles:
 *  - Auto-reconnection with exponential backoff
 *  - Connection loss notification banner
 *  - State recovery on reconnect (GET_STATE)
 *  - Bi-directional command dispatch with monotonic sequence numbers
 *  - Ping/Pong round-trip time (RTT) heartbeats
 */
class TeleopWebSocket {
    constructor() {
        this.socket = null;
        this.isConnected = false;
        this.sequenceNumber = 0;
        this.reconnectAttempts = 0;
        this.maxReconnectIntervalMs = 8000;
        this.pingInterval = null;
        this.callbacks = {
            onState: () => {},
            onAck: () => {},
            onDrop: () => {},
            onStatusChange: () => {},
            onPong: () => {},
        };
    }

    connect() {
        const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        const wsUrl = `${protocol}//${window.location.host}/ws/robot`;

        try {
            this.socket = new WebSocket(wsUrl);
        } catch (e) {
            this._handleDisconnect();
            return;
        }

        this.socket.onopen = () => {
            this.isConnected = true;
            this.reconnectAttempts = 0;
            this.callbacks.onStatusChange(true);
            this._startHeartbeat();
            // Request latest authoritative state on reconnection
            this.sendMessage("GET_STATE", {});
        };

        this.socket.onclose = () => {
            this._handleDisconnect();
        };

        this.socket.onerror = () => {
            if (this.socket) {
                this.socket.close();
            }
        };

        this.socket.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                this._handleMessage(msg);
            } catch (err) {
                console.error("Malformed WS message:", err);
            }
        };
    }

    _handleDisconnect() {
        this.isConnected = false;
        this._stopHeartbeat();
        this.callbacks.onStatusChange(false);

        // Exponential backoff: 1s, 2s, 4s, 8s
        const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), this.maxReconnectIntervalMs);
        this.reconnectAttempts++;

        const banner = document.getElementById("connection-banner");
        const countdown = document.getElementById("reconnect-countdown");
        if (banner) banner.classList.remove("hidden");
        if (countdown) countdown.textContent = (delay / 1000).toFixed(0);

        setTimeout(() => {
            this.connect();
        }, delay);
    }

    _startHeartbeat() {
        this._stopHeartbeat();
        this.pingInterval = setInterval(() => {
            if (this.isConnected) {
                this.sendMessage("PING", { timestamp: Date.now() / 1000 });
            }
        }, 1000);
    }

    _stopHeartbeat() {
        if (this.pingInterval) {
            clearInterval(this.pingInterval);
            this.pingInterval = null;
        }
    }

    _handleMessage(msg) {
        switch (msg.type) {
            case "ROBOT_STATE":
                if (msg.data && msg.data.last_sequence_number !== undefined) {
                    this.sequenceNumber = Math.max(this.sequenceNumber, msg.data.last_sequence_number);
                }
                this.callbacks.onState(msg.data);
                break;

            case "COMMAND_ACK":
                this.callbacks.onAck(msg.data, msg.simulated_delay_ms);
                break;

            case "PACKET_DROPPED":
                this.callbacks.onDrop(msg);
                break;

            case "PONG":
                this.callbacks.onPong(msg);
                break;

            default:
                break;
        }
    }

    sendMessage(type, data) {
        if (!this.isConnected || !this.socket) return false;
        try {
            this.socket.send(JSON.stringify({ type, ...data }));
            return true;
        } catch (e) {
            return false;
        }
    }

    sendCommand(commandType, speed = 1.0) {
        this.sequenceNumber += 1;
        const cmd = {
            command_id: `cmd-${Date.now().toString(36)}-${Math.random().toString(36).substr(2, 4)}`,
            sequence_number: this.sequenceNumber,
            timestamp: Date.now() / 1000,
            command_type: commandType,
            speed: parseFloat(speed),
        };
        return this.sendMessage("COMMAND", { data: cmd });
    }
}

window.TeleopWebSocket = TeleopWebSocket;
