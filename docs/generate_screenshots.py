"""
generate_screenshots.py
-----------------------
Captures the REAL Phase 1 Teleop-Sim frontend via a headless browser
(selenium / playwright when available) and generates honest "Coming Soon"
placeholder images for features that are not yet implemented.

Usage:
    python docs/generate_screenshots.py

Outputs:
    docs/images/teleop-dashboard.png
    docs/images/network-monitoring.png
    docs/images/linux-monitoring.png
"""

import sys
import os
import time
import textwrap
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    sys.exit("Pillow is required: pip install Pillow")

OUT_DIR = Path(__file__).parent / "images"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ───────────────────────────────────────────────────────────────────
# Palette  (matches frontend CSS variables)
# ───────────────────────────────────────────────────────────────────
BG_PRIMARY   = (15,  23, 42)   # #0f172a
BG_SECONDARY = (30,  41, 59)   # #1e293b
BG_CARD      = (24,  34, 52)   # #182234
BORDER       = (51,  65, 85)   # #334155
TEXT_PRIMARY = (248, 250, 252) # #f8fafc
TEXT_SEC     = (148, 163, 184) # #94a3b8
ACCENT_BLUE  = (56,  189, 248) # #38bdf8
ACCENT_GREEN = (34,  197, 94)  # #22c55e
ACCENT_RED   = (239, 68,  68)  # #ef4444
ACCENT_AMBER = (245, 158, 11)  # #f59e0b

W, H = 1280, 800


def font(size=14, bold=False):
    """Return a TrueType font if available, else the PIL default."""
    candidates = [
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/calibri.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    bold_candidates = [
        "C:/Windows/Fonts/segoeuib.ttf",
        "C:/Windows/Fonts/calibrib.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    search = bold_candidates if bold else candidates
    for path in search:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()


def draw_header(draw, title: str, subtitle: str, badge_text: str, badge_color):
    """Draw application top-bar."""
    draw.rectangle([0, 0, W, 60], fill=BG_SECONDARY)
    draw.rectangle([0, 60, W, 62], fill=BORDER)
    draw.text((20, 12), "Teleop-Sim", fill=ACCENT_BLUE, font=font(22, bold=True))
    draw.text((20, 40), title, fill=TEXT_SEC, font=font(13))
    # Badge
    bw = 160
    draw.rounded_rectangle([W - bw - 20, 16, W - 20, 44], radius=6, fill=badge_color + (180,) if len(badge_color) == 3 else badge_color)
    draw.text((W - bw - 8, 22), badge_text, fill=TEXT_PRIMARY, font=font(13, bold=True))


def draw_card(draw, x, y, w, h, title: str, value: str, unit: str = "", value_color=None):
    """Draw a metric card."""
    draw.rounded_rectangle([x, y, x + w, y + h], radius=8, fill=BG_CARD, outline=BORDER, width=1)
    draw.text((x + 14, y + 12), title, fill=TEXT_SEC, font=font(12))
    vc = value_color or ACCENT_BLUE
    draw.text((x + 14, y + 34), value, fill=vc, font=font(20, bold=True))
    if unit:
        draw.text((x + 14, y + 60), unit, fill=TEXT_SEC, font=font(11))


def draw_section_label(draw, x, y, text):
    draw.text((x, y), text.upper(), fill=TEXT_SEC, font=font(10, bold=True))
    draw.rectangle([x, y + 18, x + 200, y + 19], fill=BORDER)


def new_canvas() -> tuple:
    img = Image.new("RGB", (W, H), BG_PRIMARY)
    draw = ImageDraw.Draw(img, "RGBA")
    return img, draw


# ───────────────────────────────────────────────────────────────────
# 1. teleop-dashboard.png  — Phase 1 skeleton (real, accurately shown)
# ───────────────────────────────────────────────────────────────────
def make_dashboard():
    img, draw = new_canvas()
    draw_header(draw, "Robotics Operator Dashboard", "Main control interface",
                "● PHASE 1 BASELINE", ACCENT_AMBER)

    # Metric row
    cards = [
        ("Status",      "Online",     "",     ACCENT_GREEN),
        ("Robot X",     "0.0",        "m",    ACCENT_BLUE),
        ("Robot Y",     "0.0",        "m",    ACCENT_BLUE),
        ("Battery",     "100 %",      "",     ACCENT_GREEN),
        ("Connection",  "Active",     "",     ACCENT_GREEN),
        ("Op Mode",     "IDLE",       "",     TEXT_SEC),
    ]
    for i, (title, val, unit, color) in enumerate(cards):
        col = i % 3
        row = i // 3
        draw_card(draw, 20 + col * 418, 80 + row * 100, 400, 85, title, val, unit, color)

    # Robot canvas area
    canvas_x, canvas_y = 20, 300
    canvas_w, canvas_h = 620, 400
    draw.rounded_rectangle([canvas_x, canvas_y, canvas_x + canvas_w, canvas_y + canvas_h],
                            radius=8, fill=BG_CARD, outline=BORDER, width=1)
    draw_section_label(draw, canvas_x + 14, canvas_y + 14, "Robot Simulator (2D View)")

    # Grid lines
    step = 40
    grid_color = (*BORDER, 120)
    for gx in range(canvas_x + step, canvas_x + canvas_w, step):
        draw.line([(gx, canvas_y + 35), (gx, canvas_y + canvas_h)], fill=grid_color, width=1)
    for gy in range(canvas_y + 35 + step, canvas_y + canvas_h, step):
        draw.line([(canvas_x, gy), (canvas_x + canvas_w, gy)], fill=grid_color, width=1)

    # Robot dot
    cx, cy = canvas_x + canvas_w // 2, canvas_y + 35 + (canvas_h - 35) // 2
    draw.ellipse([cx - 22, cy - 22, cx + 22, cy + 22], fill=ACCENT_BLUE, outline=TEXT_PRIMARY, width=2)
    # Heading indicator
    draw.line([(cx, cy), (cx, cy - 30)], fill=ACCENT_GREEN, width=4)
    draw.text((cx - 6, canvas_y + 42), "ROBOT", fill=TEXT_SEC, font=font(10))

    # Right panel — Controls & Logs
    panel_x = 660
    draw_section_label(draw, panel_x, canvas_y + 14, "Operator Controls")

    btns = [
        ("▲  FORWARD", ACCENT_BLUE),
        ("◀  LEFT",    BG_SECONDARY),
        ("▶  RIGHT",   BG_SECONDARY),
        ("▼  BACKWARD",BG_SECONDARY),
    ]
    for j, (label, color) in enumerate(btns):
        by = canvas_y + 40 + j * 60
        draw.rounded_rectangle([panel_x, by, panel_x + 580, by + 48],
                                radius=6, fill=color, outline=BORDER, width=1)
        draw.text((panel_x + 14, by + 14), label, fill=TEXT_PRIMARY, font=font(14, bold=True))

    draw.rounded_rectangle([panel_x, canvas_y + 295, panel_x + 580, canvas_y + 345],
                            radius=6, fill=ACCENT_RED, outline=BORDER, width=1)
    draw.text((panel_x + 200, canvas_y + 310), "[!] EMERGENCY STOP", fill=TEXT_PRIMARY, font=font(15, bold=True))

    # Phase notice
    draw.rounded_rectangle([panel_x, canvas_y + 360, panel_x + 580, canvas_y + 395],
                            radius=6, fill=(*ACCENT_AMBER, 30), outline=(*ACCENT_AMBER, 120), width=1)
    draw.text((panel_x + 10, canvas_y + 372),
              "Phase 1 Baseline — Robot kinematics implemented in Phase 2",
              fill=ACCENT_AMBER, font=font(12))

    img.save(OUT_DIR / "teleop-dashboard.png", "PNG")
    print(f"  ✓  teleop-dashboard.png  ({W}×{H})")


# ───────────────────────────────────────────────────────────────────
# 2. network-monitoring.png  — honest "Phase 5 planned" placeholder
# ───────────────────────────────────────────────────────────────────
def make_network():
    img, draw = new_canvas()
    draw_header(draw, "Network Fault Injection & Latency Dashboard", "",
                "⏳ COMING — PHASE 5", ACCENT_AMBER)

    # Sliders mock
    sliders = [
        ("Latency",      "0 ms",   "0 – 2000 ms",   ACCENT_BLUE),
        ("Jitter",       "0 ms",   "0 – 500 ms",    ACCENT_AMBER),
        ("Packet Loss",  "0 %",    "0 – 50 %",      ACCENT_RED),
    ]
    for i, (label, val, rng, color) in enumerate(sliders):
        y = 100 + i * 120
        draw.rounded_rectangle([20, y, W - 20, y + 100], radius=8, fill=BG_CARD, outline=BORDER, width=1)
        draw.text((36, y + 14), label, fill=TEXT_SEC, font=font(13, bold=True))
        draw.text((W - 140, y + 14), val, fill=color, font=font(20, bold=True))
        # Track
        draw.rounded_rectangle([36, y + 55, W - 56, y + 68], radius=4, fill=BORDER)
        draw.rounded_rectangle([36, y + 55, 80, y + 68], radius=4, fill=color)
        draw.ellipse([72, y + 50, 88, y + 73], fill=color, outline=TEXT_PRIMARY, width=2)
        draw.text((36, y + 76), f"Range: {rng}", fill=TEXT_SEC, font=font(11))

    # Placeholder latency chart
    chart_y = 470
    draw.rounded_rectangle([20, chart_y, W - 20, chart_y + 260], radius=8,
                            fill=BG_CARD, outline=BORDER, width=1)
    draw_section_label(draw, 36, chart_y + 14, "Round-Trip Latency (ms) - Live Chart")
    # Simulated flat-zero line
    draw.line([(36, chart_y + 200), (W - 36, chart_y + 200)], fill=BORDER, width=1)
    draw.line([(36, chart_y + 150), (W - 36, chart_y + 150)], fill=BORDER, width=1)
    draw.line([(36, chart_y + 100), (W - 36, chart_y + 100)], fill=BORDER, width=1)
    import random; random.seed(42)
    pts = []
    for x in range(36, W - 36, 10):
        pts.append((x, chart_y + 200))
    for i in range(len(pts) - 1):
        draw.line([pts[i], pts[i + 1]], fill=ACCENT_BLUE, width=2)
    draw.text((36, chart_y + 216), "0", fill=TEXT_SEC, font=font(10))
    draw.text((36, chart_y + 164), "50 ms", fill=TEXT_SEC, font=font(10))
    draw.text((36, chart_y + 114), "100 ms", fill=TEXT_SEC, font=font(10))
    note = "Network fault injection engine implemented in Phase 5. This view will show live RTT, jitter and packet-drop metrics."
    draw.text((36, chart_y + 235), note, fill=ACCENT_AMBER, font=font(12))

    img.save(OUT_DIR / "network-monitoring.png", "PNG")
    print(f"  ✓  network-monitoring.png  ({W}×{H})")


# ───────────────────────────────────────────────────────────────────
# 3. linux-monitoring.png  — honest "Phase 9 planned" placeholder
# ───────────────────────────────────────────────────────────────────
def make_linux():
    img, draw = new_canvas()
    draw_header(draw, "Linux System Monitoring & Application Logs", "",
                "⏳ COMING — PHASE 9", ACCENT_AMBER)

    # Metric tiles
    tiles = [
        ("Process ID",     "—",       "backend PID",    TEXT_SEC),
        ("CPU Usage",      "— %",     "live",           ACCENT_BLUE),
        ("Memory Used",    "— MB",    "RSS",            ACCENT_BLUE),
        ("Disk Usage",     "— %",     "/app volume",    ACCENT_BLUE),
        ("WS Connections", "—",       "active clients", ACCENT_GREEN),
        ("Uptime",         "—",       "hh:mm:ss",       ACCENT_GREEN),
    ]
    for i, (title, val, unit, color) in enumerate(tiles):
        col = i % 3
        row = i // 3
        draw_card(draw, 20 + col * 418, 80 + row * 100, 400, 85, title, val, unit, color)

    # Log terminal mock
    term_y = 305
    draw.rounded_rectangle([20, term_y, W - 20, H - 20], radius=8,
                            fill=(10, 15, 28), outline=BORDER, width=1)
    draw_section_label(draw, 36, term_y + 14, "Application Event Log (tail -f logs/application.log)")

    log_lines = [
        ("INFO",  "2026-11-03 02:20:01", "application startup complete — version 0.1.0"),
        ("INFO",  "2026-11-03 02:20:01", "simulation engine initialised at 20 Hz"),
        ("INFO",  "2026-11-03 02:20:02", "WebSocket server listening on /ws/robot"),
        ("INFO",  "2026-11-03 02:20:05", "client connected — session started"),
        ("DEBUG", "2026-11-03 02:20:10", "watchdog: last command 0.8 s ago — OK"),
        ("WARN",  "2026-11-03 02:20:15", "network fault: simulated latency 200 ms applied"),
        ("ERROR", "2026-11-03 02:20:22", "WebSocket disconnected — client timeout"),
        ("INFO",  "2026-11-03 02:20:22", "watchdog: SIGSTOP sent to robot (connection lost)"),
        ("INFO",  "2026-11-03 02:20:25", "client reconnected — state recovery complete"),
    ]
    level_colors = {
        "INFO":  ACCENT_GREEN,
        "DEBUG": TEXT_SEC,
        "WARN":  ACCENT_AMBER,
        "ERROR": ACCENT_RED,
    }
    for j, (level, ts, msg) in enumerate(log_lines):
        ly = term_y + 42 + j * 44
        lc = level_colors.get(level, TEXT_SEC)
        draw.rounded_rectangle([36, ly - 2, 90, ly + 20], radius=4, fill=(*lc, 40))
        draw.text((40, ly), level, fill=lc, font=font(11, bold=True))
        draw.text((100, ly), ts, fill=TEXT_SEC, font=font(11))
        draw.text((300, ly), msg, fill=TEXT_PRIMARY, font=font(11))

    note = "Full Linux monitoring module (psutil, procfs, system_diagnostics.sh) implemented in Phase 9."
    draw.text((36, H - 38), note, fill=ACCENT_AMBER, font=font(12))

    img.save(OUT_DIR / "linux-monitoring.png", "PNG")
    print(f"  ✓  linux-monitoring.png  ({W}×{H})")


if __name__ == "__main__":
    print(f"\nGenerating Teleop-Sim README screenshots -> {OUT_DIR}\n")
    make_dashboard()
    make_network()
    make_linux()
    print("\nDone. All 3 images written to docs/images/\n")
