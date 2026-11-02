/**
 * WebSocket manager module for Teleop-Sim.
 */
class TeleopWebSocket {
    constructor(url) {
        this.url = url;
        this.socket = null;
    }
}
window.TeleopWebSocket = TeleopWebSocket;
