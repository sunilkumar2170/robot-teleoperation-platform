"""
generate_demo_gif.py
--------------------
Generates a genuine robot-movement demo GIF by running the real
RobotSimulator engine (app/robot/simulator.py) and rendering each
physics tick as a frame.

No browser, no fake recording — the simulation data driving the GIF
is identical to what the REST API and WebSocket stream in production.

Usage (from teleop-sim/):
    PYTHONPATH=backend python docs/generate_demo_gif.py

Output:
    docs/images/robot-demo.gif   (~5-8 s loop, 640×480)
"""
from __future__ import annotations

import math
import os
import sys
import time
from pathlib import Path

# ── Make sure app/ is importable ─────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.robot.simulator import RobotSimulator
from app.robot.state import RobotState
from app.schemas.command import CommandType, RobotCommandSchema

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    sys.exit("Pillow required: pip install Pillow")

OUT_DIR = Path(__file__).parent / "images"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Canvas & palette ─────────────────────────────────────────────────────────
W, H = 640, 480
BOUNDS = 50.0              # sim boundary ±50 m

BG        = (15, 23, 42)
GRID      = (30, 42, 65)
BOUND_CLR = (51, 65, 85)
ROBOT_CLR = (56, 189, 248)    # accent blue
HEAD_CLR  = (34, 197, 94)     # accent green
TRAIL_CLR = (56, 189, 248, 60)
TEXT_PRI  = (248, 250, 252)
TEXT_SEC  = (148, 163, 184)
ESTOP_CLR = (239, 68, 68)
AMBER     = (245, 158, 11)


def font(size=12, bold=False):
    candidates = [
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf"  if bold else "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
            else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


# ── Coordinate helpers ────────────────────────────────────────────────────────
CANVAS_X, CANVAS_Y = 20, 60
CANVAS_W = W - 40
CANVAS_H = H - 130

def world_to_screen(wx: float, wy: float):
    """Convert world coordinates (m) to screen pixels."""
    px = CANVAS_X + int((wx + BOUNDS) / (2 * BOUNDS) * CANVAS_W)
    py = CANVAS_Y + CANVAS_H - int((wy + BOUNDS) / (2 * BOUNDS) * CANVAS_H)
    return px, py


# ── Frame renderer ────────────────────────────────────────────────────────────
def render_frame(
    state: dict,
    trail: list,
    phase_label: str,
    cmd_label: str,
    seq: int,
) -> Image.Image:
    img = Image.new("RGBA", (W, H), (*BG, 255))
    draw = ImageDraw.Draw(img, "RGBA")

    # ── Header bar ────────────────────────────────────────────────────────────
    draw.rectangle([0, 0, W, 52], fill=(30, 41, 59, 255))
    draw.rectangle([0, 52, W, 54], fill=(*BOUND_CLR, 255))
    draw.text((14, 8), "Teleop-Sim", fill=ROBOT_CLR, font=font(20, bold=True))
    draw.text((14, 34), "2D Robot Simulation — Live Kinematics", fill=TEXT_SEC, font=font(12))

    # Status badge
    estop = state.get("emergency_stop", False)
    mode  = state.get("operating_mode", "IDLE")
    badge_color = ESTOP_CLR if estop else (HEAD_CLR if mode == "MOVING" else (51, 65, 85))
    badge_text  = "E-STOP" if estop else mode
    draw.rounded_rectangle([W - 115, 12, W - 10, 40], radius=6, fill=(*badge_color, 200))
    draw.text((W - 108, 19), badge_text, fill=TEXT_PRI, font=font(13, bold=True))

    # ── Canvas border ────────────────────────────────────────────────────────
    draw.rounded_rectangle(
        [CANVAS_X - 1, CANVAS_Y - 1, CANVAS_X + CANVAS_W + 1, CANVAS_Y + CANVAS_H + 1],
        radius=6, outline=(*BOUND_CLR, 255), width=1,
    )

    # ── Grid ─────────────────────────────────────────────────────────────────
    grid_step_world = 10  # every 10 m
    for gx_w in range(-50, 51, grid_step_world):
        gx, _ = world_to_screen(gx_w, 0)
        draw.line([(gx, CANVAS_Y), (gx, CANVAS_Y + CANVAS_H)], fill=(*GRID, 255), width=1)
    for gy_w in range(-50, 51, grid_step_world):
        _, gy = world_to_screen(0, gy_w)
        draw.line([(CANVAS_X, gy), (CANVAS_X + CANVAS_W, gy)], fill=(*GRID, 255), width=1)

    # Origin cross
    ox, oy = world_to_screen(0, 0)
    draw.line([(ox - 6, oy), (ox + 6, oy)], fill=(*BOUND_CLR, 255), width=2)
    draw.line([(ox, oy - 6), (ox, oy + 6)], fill=(*BOUND_CLR, 255), width=2)

    # ── Trail ────────────────────────────────────────────────────────────────
    if len(trail) >= 2:
        trail_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        td = ImageDraw.Draw(trail_layer, "RGBA")
        for i in range(1, len(trail)):
            alpha = int(40 + 160 * (i / len(trail)))
            sx, sy = world_to_screen(trail[i - 1][0], trail[i - 1][1])
            ex, ey = world_to_screen(trail[i][0], trail[i][1])
            td.line([(sx, sy), (ex, ey)], fill=(*ROBOT_CLR, alpha), width=2)
        img = Image.alpha_composite(img, trail_layer)
        draw = ImageDraw.Draw(img, "RGBA")

    # ── Robot body ────────────────────────────────────────────────────────────
    rx, ry = world_to_screen(state["x"], state["y"])
    r = 14
    robot_fill = ESTOP_CLR if estop else ROBOT_CLR
    draw.ellipse([rx - r, ry - r, rx + r, ry + r], fill=(*robot_fill, 230), outline=TEXT_PRI, width=2)

    # Heading arrow
    ori = state["orientation"]
    hx = rx + int((r + 8) * math.cos(ori))
    hy = ry - int((r + 8) * math.sin(ori))
    draw.line([(rx, ry), (hx, hy)], fill=(*HEAD_CLR, 255), width=3)
    # Arrow head
    arrow_len = 5
    for offset in (-0.4, 0.4):
        ax = hx - int(arrow_len * math.cos(ori - offset))
        ay = hy + int(arrow_len * math.sin(ori - offset))
        draw.line([(hx, hy), (ax, ay)], fill=(*HEAD_CLR, 255), width=2)

    # ── Telemetry bar ────────────────────────────────────────────────────────
    bar_y = CANVAS_Y + CANVAS_H + 10
    bar_h = 55
    draw.rectangle([0, bar_y, W, bar_y + bar_h], fill=(24, 34, 52, 255))
    draw.rectangle([0, bar_y, W, bar_y + 1], fill=(*BOUND_CLR, 255))

    fields = [
        ("X", f"{state['x']:+.2f} m"),
        ("Y", f"{state['y']:+.2f} m"),
        ("HDG", f"{math.degrees(state['orientation']):.1f} deg"),
        ("SPD", f"{abs(state['linear_velocity']):.2f} m/s"),
        ("BAT", f"{state['battery_percentage']:.1f} %"),
        ("SEQ", str(seq)),
    ]
    col_w = W // len(fields)
    for i, (label, val) in enumerate(fields):
        fx = 10 + i * col_w
        draw.text((fx, bar_y + 6), label, fill=TEXT_SEC, font=font(10, bold=True))
        draw.text((fx, bar_y + 24), val, fill=TEXT_PRI, font=font(13, bold=True))

    # ── Command label ─────────────────────────────────────────────────────────
    fy = bar_y + bar_h + 4
    draw.rectangle([0, fy, W, H], fill=(*BG, 255))
    draw.text((14, fy + 4), f"CMD: {cmd_label}", fill=AMBER, font=font(11, bold=True))
    draw.text((14, fy + 22), phase_label, fill=TEXT_SEC, font=font(10))

    return img.convert("RGB")


# ── Simulation script ─────────────────────────────────────────────────────────
def run_simulation() -> list:
    """
    Run the real RobotSimulator engine synchronously tick by tick.
    Returns a list of (state_dict, cmd_label, seq_num) tuples.
    """
    sim = RobotSimulator(robot_id="demo", tick_hz=20.0, watchdog_timeout=999.0)
    sim.state.connection_status = "CONNECTED"
    sim.state.last_command_timestamp = time.time()

    def cmd(seq, ctype, speed=1.0):
        return RobotCommandSchema(
            sequence_number=seq,
            command_type=ctype,
            speed=speed,
        )

    script = [
        # (ticks, command, label)
        (15, None,                            "Idle — robot at origin"),
        (30, cmd(1, CommandType.MOVE_FORWARD),  "MOVE_FORWARD  speed=1.0"),
        (30, cmd(2, CommandType.MOVE_FORWARD, 1.5), "MOVE_FORWARD  speed=1.5"),
        (25, cmd(3, CommandType.TURN_LEFT),     "TURN_LEFT     speed=1.0"),
        (30, cmd(4, CommandType.MOVE_FORWARD),  "MOVE_FORWARD  speed=1.0"),
        (25, cmd(5, CommandType.TURN_LEFT),     "TURN_LEFT     speed=1.0"),
        (30, cmd(6, CommandType.MOVE_FORWARD),  "MOVE_FORWARD  speed=1.0"),
        (20, cmd(7, CommandType.STOP),          "STOP"),
        (15, cmd(8, CommandType.EMERGENCY_STOP),"EMERGENCY_STOP"),
        (20, None,                              "Emergency stop latched"),
        (15, "reset",                           "RESET — return to origin"),
        (20, None,                              "Reset complete"),
        (30, cmd(9, CommandType.MOVE_FORWARD),  "MOVE_FORWARD  speed=1.0"),
        (30, cmd(10, CommandType.TURN_RIGHT),   "TURN_RIGHT    speed=1.0"),
        (25, cmd(11, CommandType.MOVE_FORWARD), "MOVE_FORWARD  speed=1.0"),
        (15, cmd(12, CommandType.STOP),         "STOP — demo complete"),
        (20, None,                              ""),
    ]

    frames = []
    trail = []
    seq_counter = 0

    for (ticks, action, label) in script:
        if action == "reset":
            sim.reset()
            trail.clear()
        elif action is not None:
            sim.process_command(action)
            seq_counter = action.sequence_number

        for _ in range(ticks):
            sim._tick()
            state = sim.get_state()
            trail.append((state["x"], state["y"]))
            if len(trail) > 300:
                trail.pop(0)
            frames.append((dict(state), list(trail), label, seq_counter))

    return frames


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Running real RobotSimulator engine to capture demo frames...")
    frames_data = run_simulation()
    print(f"  Simulation produced {len(frames_data)} frames")

    phase_label = "Phase 2: Python kinematics engine — genuine simulation data"
    images = []
    for i, (state, trail, cmd_label, seq) in enumerate(frames_data):
        img = render_frame(state, trail, phase_label, cmd_label, seq)
        images.append(img)
        if i % 50 == 0:
            print(f"  Rendered frame {i}/{len(frames_data)}", end="\r")

    print(f"  Rendered {len(images)} frames")

    out_path = OUT_DIR / "robot-demo.gif"
    print(f"  Saving animated GIF -> {out_path}")
    images[0].save(
        out_path,
        format="GIF",
        save_all=True,
        append_images=images[1:],
        duration=50,      # 50 ms per frame = 20 fps
        loop=0,           # loop forever
        optimize=True,
    )
    size_kb = out_path.stat().st_size // 1024
    print(f"\nDone. robot-demo.gif saved ({size_kb} KB, {len(images)} frames, ~{len(images)*50//1000} s loop)\n")
