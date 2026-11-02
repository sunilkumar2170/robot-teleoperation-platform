/**
 * Robot Canvas renderer module for Teleop-Sim.
 */
class RobotRenderer {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
    }
}
window.RobotRenderer = RobotRenderer;
