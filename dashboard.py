# dashboard.py
import os
os.environ["MPLBACKEND"] = "TkAgg"

import tkinter as tk
from tkinter import ttk, messagebox
import time, csv, math
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import xml.etree.ElementTree as ET

from xml_logger import XMLLogger
from sensors import SensorReader, ARM_LENGTH_M   # <-- comes from sensors.py

# ===================== CONFIG =====================
MAX_FORCE_LBS = 2000
WARNING_FORCE = 1700
UPDATE_MS = 200      # ms
WINDOW_POINTS = 80
APPLY_ZERO_DISPLAY = True  # Zero affects DISPLAY only (raw always logged)
# ==================================================

def export_xml_to_csv(xml_path: str) -> str:
    import os
    if not os.path.exists(xml_path):
        raise FileNotFoundError(f"XML log not found: {xml_path}")
    tree = ET.parse(xml_path); root = tree.getroot()
    samples = root.findall(".//Sample")
    if not samples: raise ValueError("No <Sample> elements found in XML")
    fields, rows = set(), []
    for s in samples:
        row = {}
        def walk(prefix, elem):
            for c in elem:
                tag = f"{prefix}.{c.tag}" if prefix else c.tag
                if len(c): walk(tag, c)
                else:
                    row[tag] = (c.text or "").strip(); fields.add(tag)
        walk("", s)
        row["timestamp"] = s.attrib.get("t", ""); rows.append(row)
    fieldnames = ["timestamp"] + sorted(fields)
    base, _ = os.path.splitext(xml_path); csv_path = f"{base}.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames); w.writeheader(); w.writerows(rows)
    return csv_path


class FSAE_Dashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("FSAE Telemetry Dashboard")

        # ---------- Logger ----------
        self.logger = XMLLogger(
            path="torsion_session.xml",
            session_meta={"operator": "User", "rig": "FSAE Torsion Rig", "mode": "Hardware/Random via sensors.py"},
            rotate_daily=True
        )
        self.logger.flush_every = 1
        print(f"Logging to: {self.logger.path}")

        # ---------- State ----------
        self.sample_count = 0
        self.running = True
        self.force_zero = 0.0    # display offsets only
        self.angle_zero = 0.0
        self.torque_zero = 0.0
        self.last_raw = (0.0, 0.0, 0.0)  # (force_lbs, angle_deg, torque_Nm)

        # ---------- Sensors (hardware on Pi / random on laptop) ----------
        self.sensors = SensorReader(target_hz=20.0)

        # ---- Top: readout + status + buttons ----
        frame_top = ttk.Frame(root); frame_top.pack(fill="x", padx=10, pady=(10,6))
        self.force_label = tk.Label(frame_top, text="0 lbs",
                                    font=("Consolas", 36, "bold"),
                                    fg="white", bg="black")
        self.force_label.pack(side="left", padx=20)

        self.state_var = tk.StringVar(value="RUNNING")
        self.state_lbl = tk.Label(frame_top, textvariable=self.state_var,
                                  font=("Segoe UI", 12, "bold"),
                                  fg="white", bg="#2e7d32", padx=10, pady=4)
        self.state_lbl.pack(side="left", padx=10)

        btns = ttk.Frame(frame_top); btns.pack(side="right", padx=10)
        self.btn_start = ttk.Button(btns, text="Start", command=self.on_start)
        self.btn_stop  = ttk.Button(btns, text="Stop",  command=self.on_stop)
        self.btn_zero  = ttk.Button(btns, text="Zero",  command=self.on_zero)
        self.btn_start.grid(row=0, column=0, padx=5)
        self.btn_stop.grid(row=0, column=1, padx=5)
        self.btn_zero.grid(row=0, column=2, padx=5)

        # ---- Gauge ----
        self.gauge_fig = Figure(figsize=(4, 3), dpi=100, facecolor="#1e1e1e")
        self.gauge_ax = self.gauge_fig.add_subplot(111, projection="polar")
        self._setup_gauge()
        self.gauge_canvas = FigureCanvasTkAgg(self.gauge_fig, master=root)
        self.gauge_canvas.get_tk_widget().pack(fill="x", padx=10, pady=(0,10))

        # ---- Plot: Torque vs Angle (DISPLAY values) ----
        frame_bottom = ttk.LabelFrame(root, text="Torque vs Angle")
        frame_bottom.pack(fill="both", expand=True, padx=10, pady=(0,10))
        self.fig = Figure(figsize=(6, 4), dpi=100, facecolor="#1e1e1e")
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor("#111")
        self.ax.set_xlabel("Torque (Nm)", color="white")
        self.ax.set_ylabel("Angle (deg)", color="white")
        self.ax.tick_params(colors="white")
        self.ax.grid(True, color="#333", linestyle="--")
        self.canvas = FigureCanvasTkAgg(self.fig, master=frame_bottom)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        self.angle_data, self.torque_data = [], []
        (self.line,) = self.ax.plot([], [], marker="o", color="#00aaff", lw=2, ms=6, mec="white")

        # ---- Status bar ----
        bar = ttk.Frame(root); bar.pack(fill="x", padx=10, pady=(0,10))
        self.status = tk.StringVar(value="Samples: 0")
        ttk.Label(bar, textvariable=self.status).pack(side="left")
        ttk.Label(bar, text=f"XML: {self.logger.path}").pack(side="right")

        self.blink_state = True

        # Shortcuts
        self.root.bind("<space>", lambda e: self.on_start() if not self.running else self.on_stop())
        self.root.bind("<z>",      lambda e: self.on_zero())

        # Loop + close hook
        self.root.after(UPDATE_MS, self.tick)
        self.root.protocol("WM_DELETE_WINDOW", self.on_quit)
        self._refresh_buttons()

    # ---------- UI helpers ----------
    def _refresh_buttons(self):
        if self.running:
            self.btn_start.state(["disabled"])
            self.btn_stop.state(["!disabled"])
            self.state_var.set("RUNNING")
            self.state_lbl.configure(bg="#2e7d32")  # green
        else:
            self.btn_start.state(["!disabled"])
            self.btn_stop.state(["disabled"])
            self.state_var.set("PAUSED")
            self.state_lbl.configure(bg="#9e9e9e")  # gray

    def on_start(self):
        self.running = True
        self._refresh_buttons()

    def on_stop(self):
        self.running = False
        self._refresh_buttons()

    def on_zero(self):
        """Zero (tare) affects DISPLAY only; raw values continue unchanged in the log."""
        f, a, t = self.last_raw
        self.force_zero, self.angle_zero, self.torque_zero = f, a, t
        self.status.set(f"Samples: {self.sample_count}  (Zeroed display)")

    # ---------- Rendering ----------
    def _setup_gauge(self):
        self.gauge_ax.set_theta_zero_location("S")
        self.gauge_ax.set_theta_direction(-1)
        self.gauge_ax.set_ylim(0, 10)
        self.gauge_ax.set_yticklabels([]); self.gauge_ax.set_xticklabels([])
        self.gauge_ax.grid(False); self.gauge_ax.set_facecolor("#1e1e1e")
        self.gauge_ax.bar(np.linspace(0, np.pi*0.7, 50), 10, width=np.pi/50, color="#00ffcc", alpha=0.6)
        self.gauge_ax.bar(np.linspace(np.pi*0.7, np.pi*0.85, 20), 10, width=np.pi/50, color="#ffff00", alpha=0.7)
        self.gauge_ax.bar(np.linspace(np.pi*0.85, np.pi*0.95, 15), 10, width=np.pi/50, color="#ff9900", alpha=0.7)
        self.gauge_ax.bar(np.linspace(np.pi*0.95, np.pi, 10), 10, width=np.pi/50, color="#ff0000", alpha=0.8)
        self.needle_line, = self.gauge_ax.plot([], [], color="white", lw=3)
        self.needle_dot,  = self.gauge_ax.plot([], [], "o", color="red", markersize=12)

    # ---------- Main loop ----------
    def tick(self):
        try:
            if self.running:
                # 1) RAW sample from sensors.py (hardware on Pi / random on laptop)
                rf = float(self.sensors.force_lbs)              # lbs
                ra = float(self.sensors.angle_deg)              # deg
                rt = rf * 4.448 * float(ARM_LENGTH_M)           # torque = F(N) * arm(m)

                self.last_raw = (rf, ra, rt)

                # 2) DISPLAY values (optionally zeroed)
                if APPLY_ZERO_DISPLAY:
                    df = max(0.0, rf - self.force_zero)
                    da = ra - self.angle_zero
                    dt = rt - self.torque_zero
                else:
                    df, da, dt = rf, ra, rt

                # 3) Update UI with DISPLAY values
                theta = (min(df, MAX_FORCE_LBS) / MAX_FORCE_LBS) * np.pi
                self.needle_line.set_data([theta, theta], [0, 10])
                self.needle_dot.set_data([theta], [10])  # NOTE: sequences for a single point

                if df < 900: color = "#00ffcc"
                elif df < 1350: color = "#ffff00"
                elif df < WARNING_FORCE: color = "#ff9900"
                else:
                    self.blink_state = not self.blink_state
                    color = "#ff0000" if self.blink_state else "#000000"
                self.force_label.config(text=f"{df:4.0f} lbs", fg=color)
                self.gauge_canvas.draw_idle()

                self.angle_data.append(da); self.torque_data.append(dt)
                if len(self.angle_data) > WINDOW_POINTS:
                    self.angle_data.pop(0); self.torque_data.pop(0)
                self.line.set_data(self.torque_data, self.angle_data)
                self.ax.relim(); self.ax.autoscale_view()
                self.canvas.draw_idle()

                # 4) Log RAW and DISPLAY and flush
                self.logger.add_sample({
                    "Raw":    {"Force_lbs": round(rf,2), "Angle_deg": round(ra,3), "Torque_Nm": round(rt,3)},
                    "Display":{"Force_lbs": round(df,2), "Angle_deg": round(da,3), "Torque_Nm": round(dt,3)},
                    "UI": {"warning_active": df >= WARNING_FORCE, "running": True, "apply_zero_display": APPLY_ZERO_DISPLAY}
                })
                self.logger.flush()

                # 5) Status
                self.sample_count += 1
                self.status.set(f"Samples: {self.sample_count}")

        except Exception as e:
            import traceback; traceback.print_exc()

        finally:
            self.root.after(UPDATE_MS, self.tick)

    def on_quit(self):
        try:
            self.sensors.stop()
        except Exception:
            pass
        try:
            self.logger.close()
        except Exception as e:
            messagebox.showwarning("Logger", f"Close error: {e}")
        try:
            csv_path = export_xml_to_csv(self.logger.path)
            messagebox.showinfo("Export Complete", f"Saved:\n• XML: {self.logger.path}\n• CSV:  {csv_path}")
        except Exception as e:
            messagebox.showwarning("CSV Export", f"Export failed: {e}")
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    try:
        s = ttk.Style(); s.theme_use("clam")
    except Exception:
        pass
    app = FSAE_Dashboard(root)
    print("UI started — Space toggles run/pause; 'z' zeros (display only).")
    root.mainloop()
