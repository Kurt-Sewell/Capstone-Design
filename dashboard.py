# dashboard.py
# UI: force gauge, BNO pitch label, 8× ToF plot, Start/Stop/Zero, XML logging.

import os, csv, xml.etree.ElementTree as ET
import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np

from xml_logger import XMLLogger
from sensors import SensorReader, ARM_LENGTH_M

# ===== CONFIG =====
MAX_FORCE_LBS = 2000
WARNING_FORCE = 1700
UPDATE_MS = 200
WINDOW_POINTS = 120
APPLY_ZERO_DISPLAY = True
# ==================

# ----- XML → CSV -----
def export_xml_to_csv(xml_path: str) -> str:
    tree = ET.parse(xml_path); root = tree.getroot()
    samples = root.findall(".//Sample")
    fields, rows = set(), []
    for s in samples:
        row = {}
        def add(prefix, elem):
            for c in elem:
                tag = f"{prefix}.{c.tag}" if prefix else c.tag
                if len(c):
                    add(tag, c)
                else:
                    row[tag] = (c.text or "").strip(); fields.add(tag)
        add("", s)
        row["timestamp"] = s.attrib.get("t", "")
        rows.append(row)
    fieldnames = ["timestamp"] + sorted(fields)
    base, _ = os.path.splitext(xml_path)
    csv_path = f"{base}.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames); w.writeheader(); w.writerows(rows)
    return csv_path


# ===== MAIN UI =====
class FSAE_Dashboard:
    def __init__(self, root):
        # state
        self.root = root
        self.root.title("FSAE Telemetry Dashboard — Pi")
        self.sample_count = 0
        self.running = True
        self.force_zero = 0.0
        self.angle_zero = 0.0
        self.torque_zero = 0.0
        self.last_raw = (0.0, 0.0, 0.0)

        # logger (auto-saves under 'xml files/')
        self.logger = XMLLogger(
            path="torsion_session.xml",
            session_meta={"rig": "FSAE Torsion Rig", "mode": "8x ToF + BNO055"},
            rotate_daily=True
        )
        self.logger.flush_every = 1

        # sensors
        self.sensors = SensorReader(target_hz=20.0)

        # top bar
        frame_top = ttk.Frame(root); frame_top.pack(fill="x", padx=10, pady=(10,6))
        self.force_label = tk.Label(frame_top, text="0 lbs", font=("Consolas", 36, "bold"), fg="white", bg="black")
        self.force_label.pack(side="left", padx=20)
        self.bno_label = tk.Label(frame_top, text="BNO Pitch: --.-°", font=("Consolas", 14), fg="white", bg="black")
        self.bno_label.pack(side="left", padx=10)
        self.state_var = tk.StringVar(value="RUNNING")
        self.state_lbl = tk.Label(frame_top, textvariable=self.state_var, font=("Segoe UI", 12, "bold"), fg="white", bg="#2e7d32", padx=10, pady=4)
        self.state_lbl.pack(side="left", padx=10)
        btns = ttk.Frame(frame_top); btns.pack(side="right", padx=10)
        self.btn_start = ttk.Button(btns, text="Start", command=self.on_start)
        self.btn_stop  = ttk.Button(btns, text="Stop",  command=self.on_stop)
        self.btn_zero  = ttk.Button(btns, text="Zero",  command=self.on_zero)
        self.btn_start.grid(row=0, column=0, padx=5)
        self.btn_stop.grid(row=0, column=1, padx=5)
        self.btn_zero.grid(row=0, column=2, padx=5)

        # gauge
        self.gauge_fig = Figure(figsize=(4, 3), dpi=100, facecolor="#1e1e1e")
        self.gauge_ax = self.gauge_fig.add_subplot(111, projection="polar")
        self._setup_gauge()
        self.gauge_canvas = FigureCanvasTkAgg(self.gauge_fig, master=root)
        self.gauge_canvas.get_tk_widget().pack(fill="x", padx=10, pady=(0,10))

        # plot: torque vs 8x angle
        frame_bottom = ttk.LabelFrame(root, text="Torque vs Angle — All ToF Sensors (S1…S8)")
        frame_bottom.pack(fill="both", expand=True, padx=10, pady=(0,10))
        self.fig = Figure(figsize=(7.6, 4.6), dpi=100, facecolor="#1e1e1e")
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor("#111")
        self.ax.set_xlabel("Torque (Nm)", color="white")
        self.ax.set_ylabel("Angle (deg)", color="white")
        self.ax.tick_params(colors="white")
        self.ax.grid(True, color="#333", linestyle="--")
        self.canvas = FigureCanvasTkAgg(self.fig, master=frame_bottom)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        self.num_sensors = len(self.sensors.angles_tof_deg)
        self.ang_bufs = [[] for _ in range(self.num_sensors)]
        self.tor_bufs = [[] for _ in range(self.num_sensors)]
        self.lines = []
        for _ in range(self.num_sensors):
            (line_i,) = self.ax.plot([], [], lw=2, ms=4, marker="o")
            self.lines.append(line_i)
        self.ax.legend([f"S{i+1}" for i in range(self.num_sensors)],
                       loc="upper left", ncol=4, facecolor="#222", edgecolor="#333", labelcolor="white")

        # status/loop
        bar = ttk.Frame(root); bar.pack(fill="x", padx=10, pady=(0,10))
        self.status = tk.StringVar(value="Samples: 0")
        ttk.Label(bar, textvariable=self.status).pack(side="left")
        ttk.Label(bar, text=f"XML: {self.logger.path}").pack(side="right")
        self.root.bind("<space>", lambda e: self.on_start() if not self.running else self.on_stop())
        self.root.bind("<z>", lambda e: self.on_zero())
        self.root.after(UPDATE_MS, self.tick)
        self.root.protocol("WM_DELETE_WINDOW", self.on_quit)
        self._refresh_buttons()

    # UI helpers
    def _refresh_buttons(self):
        if self.running:
            self.btn_start.state(["disabled"]); self.btn_stop.state(["!disabled"])
            self.state_var.set("RUNNING"); self.state_lbl.configure(bg="#2e7d32")
        else:
            self.btn_start.state(["!disabled"]); self.btn_stop.state(["disabled"])
            self.state_var.set("PAUSED"); self.state_lbl.configure(bg="#9e9e9e")

    def on_start(self): self.running = True;  self._refresh_buttons()
    def on_stop(self):  self.running = False; self._refresh_buttons()
    def on_zero(self):
        f, a, t = self.last_raw
        self.force_zero, self.angle_zero, self.torque_zero = f, a, t
        self.logger.add_event("Zero")

    # gauge
    def _setup_gauge(self):
        ax = self.gauge_ax
        ax.set_theta_zero_location("S"); ax.set_theta_direction(-1)
        ax.set_ylim(0, 10); ax.set_yticklabels([]); ax.set_xticklabels([])
        ax.grid(False); ax.set_facecolor("#1e1e1e")
        ax.bar(np.linspace(0, np.pi*0.7, 50), 10, width=np.pi/50, color="#00ffcc", alpha=0.6)
        ax.bar(np.linspace(np.pi*0.7, np.pi*0.85, 20), 10, width=np.pi/50, color="#ffff00", alpha=0.7)
        ax.bar(np.linspace(np.pi*0.85, np.pi*0.95, 15), 10, width=np.pi/50, color="#ff9900", alpha=0.7)
        ax.bar(np.linspace(np.pi*0.95, np.pi, 10), width=np.pi/50, height=10, color="#ff0000", alpha=0.8)
        self.needle_line, = ax.plot([], [], color="white", lw=3)
        self.needle_dot,  = ax.plot([], [], "o", color="red", markersize=12)

    # main loop
    def tick(self):
        try:
            if self.running:
                rf = float(self.sensors.force_lbs)
                ra = float(self.sensors.angle_deg)                 # selected angle (BNO or avg ToF)
                rt = rf * 4.448 * float(ARM_LENGTH_M)              # torque
                self.last_raw = (rf, ra, rt)

                if APPLY_ZERO_DISPLAY:
                    df = max(0.0, rf - self.force_zero)
                    da = ra - self.angle_zero
                    dt = rt - self.torque_zero
                else:
                    df, da, dt = rf, ra, rt

                theta = (min(df, MAX_FORCE_LBS) / MAX_FORCE_LBS) * np.pi
                self.needle_line.set_data([theta, theta], [0, 10])
                self.needle_dot.set_data([theta], [10])
                if df < 900: color = "#00ffcc"
                elif df < 1350: color = "#ffff00"
                elif df < WARNING_FORCE: color = "#ff9900"
                else:
                    self._blink = not getattr(self, "_blink", False)
                    color = "#ff0000" if self._blink else "#000000"
                self.force_label.config(text=f"{df:4.0f} lbs", fg=color)
                self.gauge_canvas.draw_idle()

                bno = getattr(self.sensors, "bno_euler_deg", {"pitch": 0.0})
                self.bno_label.config(text=f"BNO Pitch: {float(bno.get('pitch', 0.0)):.2f}°")

                tof_angles = list(self.sensors.angles_tof_deg)
                for i in range(self.num_sensors):
                    self.ang_bufs[i].append(tof_angles[i]); self.tor_bufs[i].append(rt)
                    if len(self.ang_bufs[i]) > WINDOW_POINTS:
                        self.ang_bufs[i].pop(0); self.tor_bufs[i].pop(0)
                    self.lines[i].set_data(self.tor_bufs[i], self.ang_bufs[i])
                self.ax.relim(); self.ax.autoscale_view()
                self.canvas.draw_idle()

                self.logger.add_sample({
                    "Raw": {
                        "Force_lbs": round(rf, 2),
                        "Angle_deg_selected": round(ra, 3),
                        "Torque_Nm": round(rt, 3)
                    },
                    "Angles": {
                        "ToF_deg": {f"S{i+1}": round(val, 3) for i, val in enumerate(tof_angles)},
                        "BNO055": {
                            "roll_deg":  round(float(bno.get("roll",  0.0)), 3),
                            "pitch_deg": round(float(bno.get("pitch", 0.0)), 3),
                            "yaw_deg":   round(float(bno.get("yaw",   0.0)), 3),
                        }
                    },
                    "Display": {
                        "Force_lbs": round(df, 2),
                        "Angle_deg": round(da, 3),
                        "Torque_Nm": round(dt, 3)
                    }
                })
                self.logger.flush()

                self.sample_count += 1
                self.status.set(f"Samples: {self.sample_count}")

        finally:
            self.root.after(UPDATE_MS, self.tick)

    # closing
    def on_quit(self):
        try: self.sensors.stop()
        except: pass
        try: self.logger.close()
        except: pass
        try:
            csv_file = export_xml_to_csv(self.logger.path)
            messagebox.showinfo("Saved", f"CSV saved:\n{csv_file}")
        except:
            pass
        self.root.destroy()


# run
if __name__ == "__main__":
    root = tk.Tk()
    try: ttk.Style().theme_use("clam")
    except: pass
    app = FSAE_Dashboard(root)
    root.mainloop()



