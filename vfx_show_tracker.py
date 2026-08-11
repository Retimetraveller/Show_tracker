import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import os
import csv
from datetime import datetime

try:
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

BG = "#0a0b0f"
SURFACE = "#13151c"
ELEVATED = "#1a1d27"
BORDER = "#252a38"
TEXT = "#f0f1f5"
TEXT2 = "#9ca3af"
TEXT3 = "#6b7280"
ACCENT = "#60a5fa"
SUCCESS = "#4ade80"
WARNING = "#fbbf24"
DANGER = "#f87171"
PURPLE = "#a78bfa"
ORANGE = "#fb923c"

STATUS_COLORS = {
    "Not Started": TEXT3, "WIP": WARNING, "Review": ACCENT,
    "Approved": SUCCESS, "On Hold": DANGER, "Omit": "#888888"
}
SHOT_TYPES = ["VFX", "CG", "Cleanup", "Roto", "Matchmove", "Paint", "Compositing", "Full CG", "Element"]
DEPARTMENTS = ["Compositing", "Lighting", "FX", "Animation", "Roto", "Prep", "Matchmove", "Concept"]
PRIORITIES = ["Low", "Normal", "High", "Critical"]
STATUSES = ["Not Started", "WIP", "Review", "Approved", "On Hold", "Omit"]

class ShowData:
    def __init__(self):
        self.show_info = {
            "name": "", "client": "", "producer": "", "vfx_supervisor": "",
            "comp_supervisor": "", "start_date": "", "delivery_date": "",
            "budget": "", "fps": "24", "resolution": "1920x1080",
            "colorspace": "ACES", "notes": "", "status": "Active"
        }
        self.sequences = []
        self.shots = []
        self.artists = []
        self.history = []

    def get_shot_count(self): return len(self.shots)
    def get_seq_count(self): return len(self.sequences)
    def get_artist_count(self): return len(self.artists)

    def get_status_counts(self):
        counts = {s: 0 for s in STATUSES}
        for shot in self.shots:
            if shot.get("status") in counts: counts[shot["status"]] += 1
        return counts

    def get_completion_pct(self):
        if not self.shots: return 0
        approved = sum(1 for s in self.shots if s.get("status") == "Approved")
        return round((approved / len(self.shots)) * 100, 1)

    def get_type_counts(self):
        counts = {}
        for s in self.shots:
            t = s.get("type", "Unknown")
            counts[t] = counts.get(t, 0) + 1
        return counts

    def get_artist_workload(self):
        workload = {}
        for s in self.shots:
            artist = s.get("artist", "Unassigned")
            if artist not in workload:
                workload[artist] = {"total": 0, "wip": 0, "approved": 0}
            workload[artist]["total"] += 1
            if s.get("status") == "WIP": workload[artist]["wip"] += 1
            elif s.get("status") == "Approved": workload[artist]["approved"] += 1
        return workload

    def get_retake_count(self):
        return sum(s.get("retakes", 0) for s in self.shots)

    def get_sequence_progress(self):
        progress = {}
        for seq in self.sequences:
            seq_shots = [s for s in self.shots if s.get("seq") == seq.get("name")]
            if seq_shots:
                approved = sum(1 for s in seq_shots if s.get("status") == "Approved")
                progress[seq["name"]] = round((approved / len(seq_shots)) * 100, 1)
            else:
                progress[seq["name"]] = 0
        return progress

    def get_priority_counts(self):
        counts = {}
        for s in self.shots:
            p = s.get("priority", "Normal")
            counts[p] = counts.get(p, 0) + 1
        return counts

    def get_retake_by_shot(self):
        return {s["shot_name"]: s.get("retakes", 0) for s in self.shots if s.get("retakes", 0) > 0}

class ShowTrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("VFX Show Tracker")
        self.root.geometry("1400x900")
        self.root.configure(bg=BG)
        self.root.minsize(1200, 700)
        self.data = ShowData()
        self.current_file = None
        self.current_page = None
        self.build_sidebar()
        self.build_main_container()
        self.show_dashboard()

    def build_sidebar(self):
        sidebar = tk.Frame(self.root, bg=SURFACE, width=220)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        tk.Label(sidebar, text="SHOW TRACKER", font=("Segoe UI", 14, "bold"), 
                bg=SURFACE, fg=TEXT).pack(pady=(20, 5))
        tk.Label(sidebar, text="VFX Production", font=("Segoe UI", 9), 
                bg=SURFACE, fg=TEXT3).pack()
        tk.Frame(sidebar, bg=BORDER, height=1).pack(fill="x", padx=20, pady=15)

        nav_items = [
            ("Dashboard", self.show_dashboard),
            ("Show Setup", self.show_setup),
            ("Sequences", self.show_sequences),
            ("Shots", self.show_shots),
            ("Artists", self.show_artists),
            ("Reports", self.show_reports),
        ]
        self.nav_buttons = {}
        for label, cmd in nav_items:
            btn = tk.Button(sidebar, text=label, font=("Segoe UI", 11, "bold"),
                          bg=SURFACE, fg=TEXT2, activebackground=ELEVATED, activeforeground=TEXT,
                          bd=0, cursor="hand2", anchor="w", padx=25, pady=10,
                          command=lambda l=label, c=cmd: self.nav_click(l, c))
            btn.pack(fill="x")
            self.nav_buttons[label] = btn

        tk.Frame(sidebar, bg=BORDER, height=1).pack(fill="x", padx=20, pady=15)

        for text, cmd in [("New Show", self.new_show), ("Save Show", self.save_show), ("Load Show", self.load_show)]:
            tk.Button(sidebar, text=text, font=("Segoe UI", 10, "bold"),
                     bg=ELEVATED, fg=TEXT, bd=0, cursor="hand2", padx=25, pady=8,
                     command=cmd).pack(fill="x", padx=20, pady=2)

        tk.Frame(sidebar, bg=BORDER, height=1).pack(fill="x", padx=20, pady=15)
        self.sidebar_show_name = tk.Label(sidebar, text="No Show Loaded", font=("Segoe UI", 10, "bold"),
                                          bg=SURFACE, fg=ACCENT, wraplength=180)
        self.sidebar_show_name.pack(padx=20, pady=5)
        self.sidebar_show_status = tk.Label(sidebar, text="", font=("Segoe UI", 9),
                                            bg=SURFACE, fg=TEXT3)
        self.sidebar_show_status.pack(padx=20)

    def nav_click(self, label, cmd):
        for btn in self.nav_buttons.values(): btn.config(bg=SURFACE, fg=TEXT2)
        self.nav_buttons[label].config(bg=ELEVATED, fg=ACCENT)
        self.current_page = label
        cmd()

    def build_main_container(self):
        self.main = tk.Frame(self.root, bg=BG)
        self.main.pack(side="left", fill="both", expand=True, padx=20, pady=20)

    def clear_main(self):
        for widget in self.main.winfo_children(): widget.destroy()

    def update_sidebar_info(self):
        name = self.data.show_info.get("name", "")
        if name:
            self.sidebar_show_name.config(text=name)
            self.sidebar_show_status.config(
                text=f"{self.data.get_shot_count()} shots | {self.data.get_completion_pct()}% done")
        else:
            self.sidebar_show_name.config(text="No Show Loaded")
            self.sidebar_show_status.config(text="")

    def new_show(self):
        if messagebox.askyesno("New Show", "Create a new show? Unsaved data will be lost."):
            self.data = ShowData()
            self.current_file = None
            self.update_sidebar_info()
            self.show_dashboard()

    def save_show(self):
        if self.current_file:
            path = self.current_file
        else:
            path = filedialog.asksaveasfilename(defaultextension=".json",
                                               filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
        if path:
            with open(path, "w") as f:
                json.dump({
                    "show_info": self.data.show_info,
                    "sequences": self.data.sequences,
                    "shots": self.data.shots,
                    "artists": self.data.artists,
                    "history": self.data.history
                }, f, indent=2)
            self.current_file = path
            messagebox.showinfo("Saved", f"Show saved to {os.path.basename(path)}")

    def load_show(self):
        path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
        if path:
            with open(path, "r") as f:
                data = json.load(f)
            self.data.show_info = data.get("show_info", self.data.show_info)
            self.data.sequences = data.get("sequences", [])
            self.data.shots = data.get("shots", [])
            self.data.artists = data.get("artists", [])
            self.data.history = data.get("history", [])
            self.current_file = path
            self.update_sidebar_info()
            self.show_dashboard()
            messagebox.showinfo("Loaded", f"Show loaded: {self.data.show_info.get('name', 'Untitled')}")

    # ===== DASHBOARD =====
    def show_dashboard(self):
        self.clear_main()
        header = tk.Frame(self.main, bg=BG)
        header.pack(fill="x", pady=(0, 20))
        tk.Label(header, text="Dashboard", font=("Segoe UI", 24, "bold"), bg=BG, fg=TEXT).pack(side="left")
        show_name = self.data.show_info.get("name", "Untitled Show")
        tk.Label(header, text=show_name, font=("Segoe UI", 14), bg=BG, fg=TEXT2).pack(side="right", pady=8)

        kpi_frame = tk.Frame(self.main, bg=BG)
        kpi_frame.pack(fill="x", pady=(0, 20))

        kpis = [
            ("Total Shots", str(self.data.get_shot_count()), ACCENT),
            ("Sequences", str(self.data.get_seq_count()), PURPLE),
            ("Artists", str(self.data.get_artist_count()), SUCCESS),
            ("Completion", f"{self.data.get_completion_pct()}%", SUCCESS if self.data.get_completion_pct() > 80 else WARNING),
            ("Retakes", str(self.data.get_retake_count()), DANGER if self.data.get_retake_count() > 5 else TEXT2),
            ("In Review", str(self.data.get_status_counts().get("Review", 0)), ORANGE),
        ]

        for title, value, color in kpis:
            card = tk.Frame(kpi_frame, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1)
            card.pack(side="left", expand=True, fill="both", padx=5, pady=5)
            tk.Label(card, text=value, font=("Segoe UI", 28, "bold"), bg=SURFACE, fg=color).pack(pady=(15, 5))
            tk.Label(card, text=title, font=("Segoe UI", 10), bg=SURFACE, fg=TEXT2).pack(pady=(0, 15))

        charts_frame = tk.Frame(self.main, bg=BG)
        charts_frame.pack(fill="both", expand=True)

        left_chart = tk.Frame(charts_frame, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1)
        left_chart.pack(side="left", expand=True, fill="both", padx=(0, 10), pady=10)
        tk.Label(left_chart, text="Shot Status Breakdown", font=("Segoe UI", 12, "bold"), 
                bg=SURFACE, fg=TEXT).pack(pady=10)

        if MATPLOTLIB_AVAILABLE:
            self.draw_pie_chart(left_chart, self.data.get_status_counts(), "Status")
        else:
            tk.Label(left_chart, text="Install matplotlib for charts\npip install matplotlib", 
                    bg=SURFACE, fg=TEXT2).pack(expand=True)

        right_chart = tk.Frame(charts_frame, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1)
        right_chart.pack(side="right", expand=True, fill="both", padx=(10, 0), pady=10)
        tk.Label(right_chart, text="Sequence Progress", font=("Segoe UI", 12, "bold"), 
                bg=SURFACE, fg=TEXT).pack(pady=10)

        if MATPLOTLIB_AVAILABLE:
            self.draw_hbar_chart(right_chart, self.data.get_sequence_progress(), ACCENT, "%")
        else:
            tk.Label(right_chart, text="Install matplotlib for charts\npip install matplotlib", 
                    bg=SURFACE, fg=TEXT2).pack(expand=True)

        activity = tk.Frame(self.main, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1)
        activity.pack(fill="x", pady=(10, 0))
        tk.Label(activity, text="Recent Activity", font=("Segoe UI", 12, "bold"), 
                bg=SURFACE, fg=TEXT).pack(anchor="w", padx=15, pady=10)

        if self.data.history:
            for item in self.data.history[-5:]:
                tk.Label(activity, text=f"  {item}", font=("Segoe UI", 10), 
                        bg=SURFACE, fg=TEXT2).pack(anchor="w", padx=25, pady=2)
        else:
            tk.Label(activity, text="  No activity yet. Start by setting up your show!", 
                    font=("Segoe UI", 10), bg=SURFACE, fg=TEXT3).pack(anchor="w", padx=25, pady=10)

    def draw_pie_chart(self, parent, data, title):
        fig = Figure(figsize=(5, 3.5), dpi=100, facecolor=SURFACE)
        ax = fig.add_subplot(111)
        ax.set_facecolor(SURFACE)
        labels = list(data.keys())
        values = list(data.values())
        colors_list = [STATUS_COLORS.get(l, TEXT3) for l in labels]

        if sum(values) > 0:
            wedges, texts, autotexts = ax.pie(values, labels=labels, colors=colors_list, 
                                              autopct='%1.0f%%', startangle=90,
                                              textprops={'color': TEXT, 'fontsize': 9})
            for autotext in autotexts:
                autotext.set_color(BG)
                autotext.set_fontweight('bold')
        else:
            ax.text(0.5, 0.5, "No data yet", ha='center', va='center', 
                   transform=ax.transAxes, color=TEXT2, fontsize=12)
        ax.axis('equal')
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

    def draw_hbar_chart(self, parent, data, color, unit=""):
        fig = Figure(figsize=(5, 3.5), dpi=100, facecolor=SURFACE)
        ax = fig.add_subplot(111)
        ax.set_facecolor(SURFACE)

        if data:
            labels = list(data.keys())
            values = list(data.values())
            bars = ax.barh(labels, values, color=color, height=0.5)
            ax.set_xlim(0, 100 if unit == "%" else max(values) * 1.2)
            ax.tick_params(colors=TEXT2, labelsize=9)
            ax.spines['bottom'].set_color(BORDER)
            ax.spines['left'].set_color(BORDER)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            for bar, val in zip(bars, values):
                ax.text(val + 1, bar.get_y() + bar.get_height()/2, f"{val}{unit}", 
                       va='center', color=TEXT, fontsize=9, fontweight='bold')
        else:
            ax.text(0.5, 0.5, "No data yet", ha='center', va='center',
                   transform=ax.transAxes, color=TEXT2, fontsize=12)

        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

    def draw_vbar_chart(self, parent, data, color):
        fig = Figure(figsize=(5, 3), dpi=100, facecolor=SURFACE)
        ax = fig.add_subplot(111)
        ax.set_facecolor(SURFACE)

        if data:
            labels = list(data.keys())[:10]
            values = [data[k] for k in labels]
            bars = ax.bar(labels, values, color=color, width=0.6)
            ax.tick_params(colors=TEXT2, labelsize=9)
            ax.spines['bottom'].set_color(BORDER)
            ax.spines['left'].set_color(BORDER)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            for bar, val in zip(bars, values):
                ax.text(bar.get_x() + bar.get_width()/2, val + 0.1, str(val),
                       ha='center', color=TEXT, fontsize=9, fontweight='bold')
        else:
            ax.text(0.5, 0.5, "No data yet", ha='center', va='center',
                   transform=ax.transAxes, color=TEXT2, fontsize=12)

        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

    # ===== SHOW SETUP =====
    def show_setup(self):
        self.clear_main()
        header = tk.Frame(self.main, bg=BG)
        header.pack(fill="x", pady=(0, 20))
        tk.Label(header, text="Show Setup", font=("Segoe UI", 24, "bold"), bg=BG, fg=TEXT).pack(side="left")

        self.setup_mode = tk.StringVar(value="view" if self.data.show_info.get("name") else "edit")
        toggle_frame = tk.Frame(header, bg=BG)
        toggle_frame.pack(side="right")
        tk.Radiobutton(toggle_frame, text="View", variable=self.setup_mode, value="view",
                      bg=BG, fg=TEXT, selectcolor=ACCENT, font=("Segoe UI", 10, "bold"),
                      command=self.refresh_setup).pack(side="left", padx=5)
        tk.Radiobutton(toggle_frame, text="Edit", variable=self.setup_mode, value="edit",
                      bg=BG, fg=TEXT, selectcolor=ACCENT, font=("Segoe UI", 10, "bold"),
                      command=self.refresh_setup).pack(side="left", padx=5)

        self.setup_content = tk.Frame(self.main, bg=BG)
        self.setup_content.pack(fill="both", expand=True)
        self.refresh_setup()

    def refresh_setup(self):
        for w in self.setup_content.winfo_children(): w.destroy()
        if self.setup_mode.get() == "view":
            self.build_setup_view()
        else:
            self.build_setup_edit()

    def build_setup_view(self):
        info = self.data.show_info
        if not info.get("name"):
            tk.Label(self.setup_content, text="No show configured yet. Switch to Edit mode to set up.",
                    font=("Segoe UI", 14), bg=BG, fg=TEXT2).pack(expand=True)
            return

        left = tk.Frame(self.setup_content, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1)
        left.pack(side="left", expand=True, fill="both", padx=(0, 10))

        right = tk.Frame(self.setup_content, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1)
        right.pack(side="right", expand=True, fill="both", padx=(10, 0))

        tk.Label(left, text="Show Information", font=("Segoe UI", 14, "bold"), 
                bg=SURFACE, fg=ACCENT).pack(anchor="w", padx=20, pady=15)

        fields = [
            ("Show Name", info.get("name")), ("Client", info.get("client")),
            ("Producer", info.get("producer")), ("VFX Supervisor", info.get("vfx_supervisor")),
            ("Comp Supervisor", info.get("comp_supervisor")), ("Status", info.get("status")),
        ]
        for label, value in fields:
            if value:
                row = tk.Frame(left, bg=SURFACE)
                row.pack(fill="x", padx=20, pady=5)
                tk.Label(row, text=label + ":", font=("Segoe UI", 10, "bold"), 
                        bg=SURFACE, fg=TEXT2, width=18, anchor="w").pack(side="left")
                tk.Label(row, text=value, font=("Segoe UI", 10), 
                        bg=SURFACE, fg=TEXT).pack(side="left", padx=(10, 0))

        tk.Label(right, text="Technical Specifications", font=("Segoe UI", 14, "bold"), 
                bg=SURFACE, fg=ACCENT).pack(anchor="w", padx=20, pady=15)

        tech_fields = [
            ("Start Date", info.get("start_date")), ("Delivery Date", info.get("delivery_date")),
            ("Budget", info.get("budget")), ("Frame Rate", info.get("fps")),
            ("Resolution", info.get("resolution")), ("Colorspace", info.get("colorspace")),
        ]
        for label, value in tech_fields:
            if value:
                row = tk.Frame(right, bg=SURFACE)
                row.pack(fill="x", padx=20, pady=5)
                tk.Label(row, text=label + ":", font=("Segoe UI", 10, "bold"), 
                        bg=SURFACE, fg=TEXT2, width=18, anchor="w").pack(side="left")
                tk.Label(row, text=value, font=("Segoe UI", 10), 
                        bg=SURFACE, fg=TEXT).pack(side="left", padx=(10, 0))

        if info.get("notes"):
            tk.Frame(left, bg=BORDER, height=1).pack(fill="x", padx=20, pady=15)
            tk.Label(left, text="Notes", font=("Segoe UI", 12, "bold"), 
                    bg=SURFACE, fg=TEXT2).pack(anchor="w", padx=20)
            tk.Label(left, text=info["notes"], font=("Segoe UI", 10), 
                    bg=SURFACE, fg=TEXT, wraplength=400, justify="left").pack(anchor="w", padx=20, pady=5)

    def build_setup_edit(self):
        canvas = tk.Canvas(self.setup_content, bg=BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.setup_content, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=BG)
        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw", width=1360)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.setup_entries = {}
        self.build_form_section(scroll_frame, "Basic Information", [
            ("name", "Show Name *", "entry"),
            ("client", "Client", "entry"),
            ("producer", "Producer", "entry"),
            ("vfx_supervisor", "VFX Supervisor", "entry"),
            ("comp_supervisor", "Comp Supervisor", "entry"),
        ])
        self.build_form_section(scroll_frame, "Technical Specifications", [
            ("start_date", "Start Date", "entry"),
            ("delivery_date", "Delivery Date", "entry"),
            ("budget", "Budget", "entry"),
            ("fps", "Frame Rate", "dropdown", ["24", "25", "30", "48", "60"]),
            ("resolution", "Resolution", "dropdown", ["1920x1080", "2048x1080", "3840x2160", "4096x2160", "Custom"]),
            ("colorspace", "Colorspace", "dropdown", ["ACES", "sRGB", "Rec.709", "Alexa", "LogC", "Custom"]),
            ("status", "Show Status", "dropdown", ["Active", "Bidding", "On Hold", "Wrapped", "Delivered"]),
        ])
        self.build_form_section(scroll_frame, "Notes", [
            ("notes", "Additional Notes", "text"),
        ])

        tk.Button(scroll_frame, text="Save Show Details", font=("Segoe UI", 12, "bold"),
                 bg=ACCENT, fg="#000", bd=0, cursor="hand2", padx=30, pady=12,
                 command=self.save_setup).pack(pady=20)

    def build_form_section(self, parent, title, fields):
        section = tk.Frame(parent, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1)
        section.pack(fill="x", pady=10, padx=5)
        tk.Label(section, text=title, font=("Segoe UI", 13, "bold"), 
                bg=SURFACE, fg=ACCENT).pack(anchor="w", padx=20, pady=12)

        for field in fields:
            key = field[0]
            label = field[1]
            ftype = field[2]
            row = tk.Frame(section, bg=SURFACE)
            row.pack(fill="x", padx=20, pady=6)
            tk.Label(row, text=label, font=("Segoe UI", 10), 
                    bg=SURFACE, fg=TEXT2, width=20, anchor="w").pack(side="left")

            if ftype == "entry":
                entry = tk.Entry(row, font=("Segoe UI", 11), bg=ELEVATED, fg=TEXT,
                               insertbackground=TEXT, bd=1, relief="flat", width=50)
                entry.insert(0, self.data.show_info.get(key, ""))
                entry.pack(side="left", padx=(10, 0), ipady=5)
                self.setup_entries[key] = entry
            elif ftype == "dropdown":
                var = tk.StringVar(value=self.data.show_info.get(key, field[3][0]))
                dd = ttk.Combobox(row, textvariable=var, values=field[3], 
                                state="readonly", font=("Segoe UI", 11), width=48)
                dd.pack(side="left", padx=(10, 0), ipady=3)
                self.setup_entries[key] = var
            elif ftype == "text":
                text = tk.Text(row, font=("Segoe UI", 11), bg=ELEVATED, fg=TEXT,
                             insertbackground=TEXT, bd=1, relief="flat", 
                             width=50, height=4, wrap="word")
                text.insert("1.0", self.data.show_info.get(key, ""))
                text.pack(side="left", padx=(10, 0))
                self.setup_entries[key] = text

    def save_setup(self):
        for key, widget in self.setup_entries.items():
            if isinstance(widget, tk.Text):
                self.data.show_info[key] = widget.get("1.0", "end-1c").strip()
            else:
                self.data.show_info[key] = widget.get().strip()

        if not self.data.show_info.get("name"):
            messagebox.showwarning("Required", "Show Name is required")
            return

        self.data.history.append(f"Show details updated: {self.data.show_info['name']}")
        self.update_sidebar_info()
        self.setup_mode.set("view")
        self.refresh_setup()
        messagebox.showinfo("Saved", "Show details saved successfully!")

    # ===== SEQUENCES =====
    def show_sequences(self):
        self.clear_main()
        header = tk.Frame(self.main, bg=BG)
        header.pack(fill="x", pady=(0, 20))
        tk.Label(header, text="Sequences", font=("Segoe UI", 24, "bold"), bg=BG, fg=TEXT).pack(side="left")
        tk.Button(header, text="+ Add Sequence", font=("Segoe UI", 11, "bold"),
                 bg=ACCENT, fg="#000", bd=0, cursor="hand2", padx=20, pady=8,
                 command=self.add_sequence_dialog).pack(side="right")

        self.seq_container = tk.Frame(self.main, bg=BG)
        self.seq_container.pack(fill="both", expand=True)
        self.refresh_sequences()

    def refresh_sequences(self):
        for w in self.seq_container.winfo_children(): w.destroy()

        if not self.data.sequences:
            tk.Label(self.seq_container, text="No sequences yet. Click '+ Add Sequence' to create one.",
                    font=("Segoe UI", 14), bg=BG, fg=TEXT2).pack(expand=True)
            return

        for seq in self.data.sequences:
            card = tk.Frame(self.seq_container, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1)
            card.pack(fill="x", pady=5, padx=2)

            top = tk.Frame(card, bg=SURFACE)
            top.pack(fill="x", padx=20, pady=10)

            tk.Label(top, text=seq.get("name", "Unnamed"), font=("Segoe UI", 16, "bold"),
                    bg=SURFACE, fg=TEXT).pack(side="left")

            seq_shots = [s for s in self.data.shots if s.get("seq") == seq.get("name")]
            approved = sum(1 for s in seq_shots if s.get("status") == "Approved")
            total = len(seq_shots)
            pct = round((approved/total)*100, 1) if total else 0

            status_color = SUCCESS if pct == 100 else (WARNING if pct > 50 else TEXT2)
            tk.Label(top, text=f"{approved}/{total} shots | {pct}%", font=("Segoe UI", 11, "bold"),
                    bg=SURFACE, fg=status_color).pack(side="right")

            if seq.get("description"):
                tk.Label(card, text=seq["description"], font=("Segoe UI", 10),
                        bg=SURFACE, fg=TEXT2, wraplength=1200).pack(anchor="w", padx=20, pady=(0, 5))

            if total > 0:
                bar_bg = tk.Frame(card, bg=ELEVATED, height=6)
                bar_bg.pack(fill="x", padx=20, pady=(5, 15))
                bar_fg = tk.Frame(bar_bg, bg=ACCENT, height=6)
                bar_fg.place(x=0, y=0, relwidth=pct/100)

    def add_sequence_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Sequence")
        dialog.geometry("500x300")
        dialog.configure(bg=BG)
        dialog.transient(self.root)
        dialog.grab_set()

        tk.Label(dialog, text="Add New Sequence", font=("Segoe UI", 16, "bold"), bg=BG, fg=TEXT).pack(pady=15)

        form = tk.Frame(dialog, bg=BG)
        form.pack(padx=30, fill="x")

        tk.Label(form, text="Sequence Name *", font=("Segoe UI", 10), bg=BG, fg=TEXT2).pack(anchor="w")
        name_entry = tk.Entry(form, font=("Segoe UI", 12), bg=ELEVATED, fg=TEXT, insertbackground=TEXT, bd=1)
        name_entry.pack(fill="x", pady=(4, 12), ipady=6)

        tk.Label(form, text="Description", font=("Segoe UI", 10), bg=BG, fg=TEXT2).pack(anchor="w")
        desc_entry = tk.Entry(form, font=("Segoe UI", 12), bg=ELEVATED, fg=TEXT, insertbackground=TEXT, bd=1)
        desc_entry.pack(fill="x", pady=(4, 12), ipady=6)

        def save():
            name = name_entry.get().strip()
            if not name:
                messagebox.showwarning("Required", "Sequence name is required")
                return
            if any(s.get("name") == name for s in self.data.sequences):
                messagebox.showwarning("Duplicate", f"Sequence '{name}' already exists")
                return
            self.data.sequences.append({"name": name, "description": desc_entry.get().strip()})
            self.data.history.append(f"Sequence added: {name}")
            self.refresh_sequences()
            self.update_sidebar_info()
            dialog.destroy()

        tk.Button(dialog, text="Add Sequence", command=save, font=("Segoe UI", 11, "bold"),
                 bg=ACCENT, fg="#000", bd=0, padx=30, pady=10, cursor="hand2").pack(pady=15)

    # ===== SHOTS =====
    def show_shots(self):
        self.clear_main()
        header = tk.Frame(self.main, bg=BG)
        header.pack(fill="x", pady=(0, 15))
        tk.Label(header, text="Shots", font=("Segoe UI", 24, "bold"), bg=BG, fg=TEXT).pack(side="left")

        btn_frame = tk.Frame(header, bg=BG)
        btn_frame.pack(side="right")
        tk.Button(btn_frame, text="+ Add Shot", font=("Segoe UI", 11, "bold"),
                 bg=ACCENT, fg="#000", bd=0, cursor="hand2", padx=20, pady=8,
                 command=self.add_shot_dialog).pack(side="left", padx=4)
        tk.Button(btn_frame, text="Import CSV", font=("Segoe UI", 10, "bold"),
                 bg=ELEVATED, fg=TEXT, bd=1, cursor="hand2", padx=15, pady=8,
                 command=self.import_shots_csv).pack(side="left", padx=4)
        tk.Button(btn_frame, text="Export CSV", font=("Segoe UI", 10, "bold"),
                 bg=ELEVATED, fg=TEXT, bd=1, cursor="hand2", padx=15, pady=8,
                 command=self.export_shots_csv).pack(side="left", padx=4)

        # Filter bar
        filter_frame = tk.Frame(self.main, bg=BG)
        filter_frame.pack(fill="x", pady=(0, 10))

        tk.Label(filter_frame, text="Filter:", font=("Segoe UI", 10), bg=BG, fg=TEXT2).pack(side="left")
        self.filter_seq = ttk.Combobox(filter_frame, values=["All"] + [s["name"] for s in self.data.sequences],
                                      state="readonly", width=15, font=("Segoe UI", 10))
        self.filter_seq.set("All")
        self.filter_seq.pack(side="left", padx=8)
        self.filter_seq.bind("<<ComboboxSelected>>", lambda e: self.refresh_shots())

        self.filter_status = ttk.Combobox(filter_frame, values=["All"] + STATUSES,
                                         state="readonly", width=12, font=("Segoe UI", 10))
        self.filter_status.set("All")
        self.filter_status.pack(side="left", padx=8)
        self.filter_status.bind("<<ComboboxSelected>>", lambda e: self.refresh_shots())

        self.filter_artist = ttk.Combobox(filter_frame, values=["All"] + [a["name"] for a in self.data.artists],
                                          state="readonly", width=12, font=("Segoe UI", 10))
        self.filter_artist.set("All")
        self.filter_artist.pack(side="left", padx=8)
        self.filter_artist.bind("<<ComboboxSelected>>", lambda e: self.refresh_shots())

        tk.Label(filter_frame, text="Search:", font=("Segoe UI", 10), bg=BG, fg=TEXT2).pack(side="left", padx=(20, 0))
        self.shot_search = tk.Entry(filter_frame, font=("Segoe UI", 10), bg=ELEVATED, fg=TEXT,
                                   insertbackground=TEXT, bd=1, width=20)
        self.shot_search.pack(side="left", padx=8)
        self.shot_search.bind("<KeyRelease>", lambda e: self.refresh_shots())

        # Shots table
        table_frame = tk.Frame(self.main, bg=BG)
        table_frame.pack(fill="both", expand=True)

        columns = ("shot", "seq", "type", "status", "artist", "version", "frames", "retakes", "priority", "notes")
        self.shots_tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")

        col_config = {
            "shot": (120, "Shot"), "seq": (100, "Sequence"), "type": (100, "Type"),
            "status": (100, "Status"), "artist": (120, "Artist"), "version": (80, "Version"),
            "frames": (80, "Frames"), "retakes": (60, "Retakes"), "priority": (80, "Priority"), "notes": (250, "Notes")
        }
        for col, (width, heading) in col_config.items():
            self.shots_tree.heading(col, text=heading)
            self.shots_tree.column(col, width=width, anchor="center" if col in ("status", "version", "frames", "retakes", "priority") else "w")

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.shots_tree.yview)
        self.shots_tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.shots_tree.pack(side="left", fill="both", expand=True)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background=ELEVATED, foreground=TEXT, fieldbackground=ELEVATED,
                       rowheight=30, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", background=SURFACE, foreground=TEXT, font=("Segoe UI", 10, "bold"))
        style.map("Treeview", background=[("selected", BORDER)])

        actions = tk.Frame(self.main, bg=BG)
        actions.pack(fill="x", pady=(10, 0))
        tk.Button(actions, text="Edit", font=("Segoe UI", 10, "bold"), bg=ELEVATED, fg=TEXT,
                 bd=1, cursor="hand2", padx=15, pady=6, command=self.edit_shot).pack(side="left", padx=4)
        tk.Button(actions, text="Delete", font=("Segoe UI", 10, "bold"), bg=ELEVATED, fg=DANGER,
                 bd=1, cursor="hand2", padx=15, pady=6, command=self.delete_shot).pack(side="left", padx=4)
        tk.Button(actions, text="Bump Version", font=("Segoe UI", 10, "bold"), bg=ELEVATED, fg=TEXT,
                 bd=1, cursor="hand2", padx=15, pady=6, command=self.bump_shot_version).pack(side="left", padx=4)
        tk.Button(actions, text="Copy Name", font=("Segoe UI", 10, "bold"), bg=ELEVATED, fg=TEXT,
                 bd=1, cursor="hand2", padx=15, pady=6, command=self.copy_shot_name).pack(side="left", padx=4)

        self.shots_tree.bind("<Double-1>", lambda e: self.edit_shot())
        self.refresh_shots()

    def refresh_shots(self):
        for item in self.shots_tree.get_children():
            self.shots_tree.delete(item)

        seq_filter = self.filter_seq.get()
        status_filter = self.filter_status.get()
        artist_filter = self.filter_artist.get()
        search = self.shot_search.get().lower()

        for shot in self.data.shots:
            if seq_filter != "All" and shot.get("seq") != seq_filter:
                continue
            if status_filter != "All" and shot.get("status") != status_filter:
                continue
            if artist_filter != "All" and shot.get("artist") != artist_filter:
                continue
            if search and search not in shot.get("shot_name", "").lower():
                continue

            self.shots_tree.insert("", "end", values=(
                shot.get("shot_name", ""), shot.get("seq", ""), shot.get("type", ""),
                shot.get("status", ""), shot.get("artist", ""), shot.get("version", ""),
                shot.get("frames", ""), shot.get("retakes", 0), shot.get("priority", "Normal"),
                shot.get("notes", "")
            ))

    def add_shot_dialog(self):
        if not self.data.sequences:
            messagebox.showwarning("No Sequences", "Create at least one sequence first")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Add Shot")
        dialog.geometry("550x550")
        dialog.configure(bg=BG)
        dialog.transient(self.root)
        dialog.grab_set()

        tk.Label(dialog, text="Add New Shot", font=("Segoe UI", 16, "bold"), bg=BG, fg=TEXT).pack(pady=15)

        form = tk.Frame(dialog, bg=BG)
        form.pack(padx=30, fill="x")

        fields = [
            ("Shot Name *", "shot_name", "entry"),
            ("Sequence *", "seq", "seq_dropdown"),
            ("Shot Type", "type", "type_dropdown"),
            ("Status", "status", "status_dropdown"),
            ("Assigned Artist", "artist", "artist_dropdown"),
            ("Frame Range", "frames", "entry"),
            ("Priority", "priority", "priority_dropdown"),
            ("Notes", "notes", "text"),
        ]

        entries = {}
        for label, key, ftype in fields:
            tk.Label(form, text=label, font=("Segoe UI", 10), bg=BG, fg=TEXT2).pack(anchor="w", pady=(8, 2))

            if ftype == "entry":
                e = tk.Entry(form, font=("Segoe UI", 11), bg=ELEVATED, fg=TEXT, insertbackground=TEXT, bd=1)
                e.pack(fill="x", ipady=4)
                entries[key] = e
            elif ftype == "seq_dropdown":
                var = tk.StringVar(value=self.data.sequences[0]["name"] if self.data.sequences else "")
                dd = ttk.Combobox(form, textvariable=var, values=[s["name"] for s in self.data.sequences], state="readonly")
                dd.pack(fill="x", ipady=2)
                entries[key] = var
            elif ftype == "type_dropdown":
                var = tk.StringVar(value="VFX")
                dd = ttk.Combobox(form, textvariable=var, values=SHOT_TYPES, state="readonly")
                dd.pack(fill="x", ipady=2)
                entries[key] = var
            elif ftype == "status_dropdown":
                var = tk.StringVar(value="Not Started")
                dd = ttk.Combobox(form, textvariable=var, values=STATUSES, state="readonly")
                dd.pack(fill="x", ipady=2)
                entries[key] = var
            elif ftype == "artist_dropdown":
                var = tk.StringVar(value="Unassigned")
                dd = ttk.Combobox(form, textvariable=var, values=["Unassigned"] + [a["name"] for a in self.data.artists], state="readonly")
                dd.pack(fill="x", ipady=2)
                entries[key] = var
            elif ftype == "priority_dropdown":
                var = tk.StringVar(value="Normal")
                dd = ttk.Combobox(form, textvariable=var, values=PRIORITIES, state="readonly")
                dd.pack(fill="x", ipady=2)
                entries[key] = var
            elif ftype == "text":
                e = tk.Text(form, font=("Segoe UI", 11), bg=ELEVATED, fg=TEXT, insertbackground=TEXT, bd=1, height=3, wrap="word")
                e.pack(fill="x")
                entries[key] = e

        def save():
            name = entries["shot_name"].get().strip()
            if not name:
                messagebox.showwarning("Required", "Shot name is required")
                return
            if any(s.get("shot_name") == name for s in self.data.shots):
                messagebox.showwarning("Duplicate", f"Shot '{name}' already exists")
                return

            new_shot = {
                "shot_name": name,
                "seq": entries["seq"].get(),
                "type": entries["type"].get(),
                "status": entries["status"].get(),
                "artist": entries["artist"].get(),
                "version": "v001",
                "frames": entries["frames"].get().strip(),
                "retakes": 0,
                "priority": entries["priority"].get(),
                "notes": entries["notes"].get("1.0", "end-1c").strip(),
                "updated": datetime.now().strftime("%Y-%m-%d %H:%M")
            }
            self.data.shots.append(new_shot)
            self.data.history.append(f"Shot added: {name}")
            self.refresh_shots()
            self.update_sidebar_info()
            dialog.destroy()

        tk.Button(dialog, text="Add Shot", command=save, font=("Segoe UI", 11, "bold"),
                 bg=ACCENT, fg="#000", bd=0, padx=30, pady=10, cursor="hand2").pack(pady=15)

    def edit_shot(self):
        sel = self.shots_tree.selection()
        if not sel:
            messagebox.showinfo("Select", "Please select a shot")
            return
        idx = self.shots_tree.index(sel[0])
        shot = self.data.shots[idx]

        dialog = tk.Toplevel(self.root)
        dialog.title(f"Edit {shot['shot_name']}")
        dialog.geometry("500x500")
        dialog.configure(bg=BG)
        dialog.transient(self.root)
        dialog.grab_set()

        tk.Label(dialog, text=f"Edit {shot['shot_name']}", font=("Segoe UI", 16, "bold"), bg=BG, fg=TEXT).pack(pady=15)

        form = tk.Frame(dialog, bg=BG)
        form.pack(padx=30, fill="x")

        tk.Label(form, text="Status", font=("Segoe UI", 10), bg=BG, fg=TEXT2).pack(anchor="w")
        status_var = tk.StringVar(value=shot["status"])
        ttk.Combobox(form, textvariable=status_var, values=STATUSES, state="readonly").pack(fill="x", pady=(4, 12), ipady=2)

        tk.Label(form, text="Artist", font=("Segoe UI", 10), bg=BG, fg=TEXT2).pack(anchor="w")
        artist_var = tk.StringVar(value=shot["artist"])
        ttk.Combobox(form, textvariable=artist_var, values=["Unassigned"] + [a["name"] for a in self.data.artists], state="readonly").pack(fill="x", pady=(4, 12), ipady=2)

        tk.Label(form, text="Shot Type", font=("Segoe UI", 10), bg=BG, fg=TEXT2).pack(anchor="w")
        type_var = tk.StringVar(value=shot.get("type", "VFX"))
        ttk.Combobox(form, textvariable=type_var, values=SHOT_TYPES, state="readonly").pack(fill="x", pady=(4, 12), ipady=2)

        tk.Label(form, text="Priority", font=("Segoe UI", 10), bg=BG, fg=TEXT2).pack(anchor="w")
        priority_var = tk.StringVar(value=shot.get("priority", "Normal"))
        ttk.Combobox(form, textvariable=priority_var, values=PRIORITIES, state="readonly").pack(fill="x", pady=(4, 12), ipady=2)

        tk.Label(form, text="Frame Range", font=("Segoe UI", 10), bg=BG, fg=TEXT2).pack(anchor="w")
        frames_entry = tk.Entry(form, font=("Segoe UI", 11), bg=ELEVATED, fg=TEXT, insertbackground=TEXT, bd=1)
        frames_entry.insert(0, shot.get("frames", ""))
        frames_entry.pack(fill="x", pady=(4, 12), ipady=4)

        tk.Label(form, text="Retakes", font=("Segoe UI", 10), bg=BG, fg=TEXT2).pack(anchor="w")
        retakes_entry = tk.Entry(form, font=("Segoe UI", 11), bg=ELEVATED, fg=TEXT, insertbackground=TEXT, bd=1)
        retakes_entry.insert(0, str(shot.get("retakes", 0)))
        retakes_entry.pack(fill="x", pady=(4, 12), ipady=4)

        tk.Label(form, text="Notes", font=("Segoe UI", 10), bg=BG, fg=TEXT2).pack(anchor="w")
        notes_text = tk.Text(form, font=("Segoe UI", 11), bg=ELEVATED, fg=TEXT, insertbackground=TEXT, bd=1, height=3, wrap="word")
        notes_text.insert("1.0", shot.get("notes", ""))
        notes_text.pack(fill="x", pady=(4, 12))

        def save():
            shot["status"] = status_var.get()
            shot["artist"] = artist_var.get()
            shot["type"] = type_var.get()
            shot["priority"] = priority_var.get()
            shot["frames"] = frames_entry.get().strip()
            try:
                shot["retakes"] = int(retakes_entry.get())
            except:
                shot["retakes"] = 0
            shot["notes"] = notes_text.get("1.0", "end-1c").strip()
            shot["updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            self.refresh_shots()
            self.update_sidebar_info()
            dialog.destroy()

        tk.Button(dialog, text="Save Changes", command=save, font=("Segoe UI", 11, "bold"),
                 bg=ACCENT, fg="#000", bd=0, padx=30, pady=10, cursor="hand2").pack(pady=15)

    def delete_shot(self):
        sel = self.shots_tree.selection()
        if not sel:
            messagebox.showinfo("Select", "Please select a shot")
            return
        idx = self.shots_tree.index(sel[0])
        name = self.data.shots[idx]["shot_name"]
        if messagebox.askyesno("Confirm", f"Delete shot '{name}'?"):
            del self.data.shots[idx]
            self.refresh_shots()
            self.update_sidebar_info()

    def bump_shot_version(self):
        sel = self.shots_tree.selection()
        if not sel:
            messagebox.showinfo("Select", "Please select a shot")
            return
        idx = self.shots_tree.index(sel[0])
        shot = self.data.shots[idx]
        current = shot.get("version", "v001")
        try:
            num = int(current.replace("v", "")) + 1
            new_ver = f"v{num:03d}"
        except:
            new_ver = "v002"
        shot["version"] = new_ver
        shot["updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.refresh_shots()

    def copy_shot_name(self):
        sel = self.shots_tree.selection()
        if not sel:
            messagebox.showinfo("Select", "Please select a shot")
            return
        idx = self.shots_tree.index(sel[0])
        name = self.data.shots[idx]["shot_name"]
        self.root.clipboard_clear()
        self.root.clipboard_append(name)

    def import_shots_csv(self):
        path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if path:
            with open(path, "r") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.data.shots.append({
                        "shot_name": row.get("Shot", ""),
                        "seq": row.get("Sequence", ""),
                        "type": row.get("Type", "VFX"),
                        "status": row.get("Status", "Not Started"),
                        "artist": row.get("Artist", "Unassigned"),
                        "version": row.get("Version", "v001"),
                        "frames": row.get("Frames", ""),
                        "retakes": int(row.get("Retakes", 0)),
                        "priority": row.get("Priority", "Normal"),
                        "notes": row.get("Notes", ""),
                        "updated": datetime.now().strftime("%Y-%m-%d %H:%M")
                    })
            self.refresh_shots()
            self.update_sidebar_info()
            messagebox.showinfo("Imported", f"Imported {len(self.data.shots)} shots")

    def export_shots_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if path:
            with open(path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Shot", "Sequence", "Type", "Status", "Artist", "Version", "Frames", "Retakes", "Priority", "Notes"])
                for shot in self.data.shots:
                    writer.writerow([shot.get("shot_name", ""), shot.get("seq", ""), shot.get("type", ""),
                                   shot.get("status", ""), shot.get("artist", ""), shot.get("version", ""),
                                   shot.get("frames", ""), shot.get("retakes", 0), shot.get("priority", ""),
                                   shot.get("notes", "")])
            messagebox.showinfo("Exported", f"Exported to {path}")

    # ===== ARTISTS =====
    def show_artists(self):
        self.clear_main()
        header = tk.Frame(self.main, bg=BG)
        header.pack(fill="x", pady=(0, 20))
        tk.Label(header, text="Artists", font=("Segoe UI", 24, "bold"), bg=BG, fg=TEXT).pack(side="left")
        tk.Button(header, text="+ Add Artist", font=("Segoe UI", 11, "bold"),
                 bg=ACCENT, fg="#000", bd=0, cursor="hand2", padx=20, pady=8,
                 command=self.add_artist_dialog).pack(side="right")

        self.artist_container = tk.Frame(self.main, bg=BG)
        self.artist_container.pack(fill="both", expand=True)
        self.refresh_artists()

    def refresh_artists(self):
        for w in self.artist_container.winfo_children(): w.destroy()

        if not self.data.artists:
            tk.Label(self.artist_container, text="No artists added yet.",
                    font=("Segoe UI", 14), bg=BG, fg=TEXT2).pack(expand=True)
            return

        for artist in self.data.artists:
            card = tk.Frame(self.artist_container, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1)
            card.pack(fill="x", pady=5, padx=2)

            top = tk.Frame(card, bg=SURFACE)
            top.pack(fill="x", padx=20, pady=10)

            avatar = tk.Canvas(top, width=40, height=40, bg=SURFACE, highlightthickness=0)
            avatar.pack(side="left")
            avatar.create_oval(2, 2, 38, 38, fill=ACCENT, outline="")
            avatar.create_text(20, 20, text=artist["name"][0].upper(), fill=BG, font=("Segoe UI", 14, "bold"))

            info = tk.Frame(top, bg=SURFACE)
            info.pack(side="left", padx=15)
            tk.Label(info, text=artist["name"], font=("Segoe UI", 14, "bold"), bg=SURFACE, fg=TEXT).pack(anchor="w")
            dept = artist.get("department", "")
            status = artist.get("status", "Active")
            tk.Label(info, text=f"{dept} | {status}", font=("Segoe UI", 10), bg=SURFACE, fg=TEXT2).pack(anchor="w")

            workload = self.data.get_artist_workload().get(artist["name"], {"total": 0, "wip": 0, "approved": 0})
            tk.Label(top, text=f"{workload['total']} shots ({workload['wip']} WIP, {workload['approved']} approved)",
                    font=("Segoe UI", 11), bg=SURFACE, fg=ACCENT).pack(side="right")

    def add_artist_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Artist")
        dialog.geometry("450x400")
        dialog.configure(bg=BG)
        dialog.transient(self.root)
        dialog.grab_set()

        tk.Label(dialog, text="Add New Artist", font=("Segoe UI", 16, "bold"), bg=BG, fg=TEXT).pack(pady=15)

        form = tk.Frame(dialog, bg=BG)
        form.pack(padx=30, fill="x")

        tk.Label(form, text="Name *", font=("Segoe UI", 10), bg=BG, fg=TEXT2).pack(anchor="w")
        name_entry = tk.Entry(form, font=("Segoe UI", 12), bg=ELEVATED, fg=TEXT, insertbackground=TEXT, bd=1)
        name_entry.pack(fill="x", pady=(4, 12), ipady=6)

        tk.Label(form, text="Department", font=("Segoe UI", 10), bg=BG, fg=TEXT2).pack(anchor="w")
        dept_var = tk.StringVar(value="Compositing")
        ttk.Combobox(form, textvariable=dept_var, values=DEPARTMENTS, state="readonly").pack(fill="x", pady=(4, 12), ipady=2)

        tk.Label(form, text="Email", font=("Segoe UI", 10), bg=BG, fg=TEXT2).pack(anchor="w")
        email_entry = tk.Entry(form, font=("Segoe UI", 12), bg=ELEVATED, fg=TEXT, insertbackground=TEXT, bd=1)
        email_entry.pack(fill="x", pady=(4, 12), ipady=6)

        tk.Label(form, text="Daily Rate", font=("Segoe UI", 10), bg=BG, fg=TEXT2).pack(anchor="w")
        rate_entry = tk.Entry(form, font=("Segoe UI", 12), bg=ELEVATED, fg=TEXT, insertbackground=TEXT, bd=1)
        rate_entry.pack(fill="x", pady=(4, 12), ipady=6)

        def save():
            name = name_entry.get().strip()
            if not name:
                messagebox.showwarning("Required", "Name is required")
                return
            self.data.artists.append({
                "name": name,
                "department": dept_var.get(),
                "email": email_entry.get().strip(),
                "rate": rate_entry.get().strip(),
                "status": "Active"
            })
            self.data.history.append(f"Artist added: {name}")
            self.refresh_artists()
            self.update_sidebar_info()
            dialog.destroy()

        tk.Button(dialog, text="Add Artist", command=save, font=("Segoe UI", 11, "bold"),
                 bg=ACCENT, fg="#000", bd=0, padx=30, pady=10, cursor="hand2").pack(pady=15)

    # ===== REPORTS =====
    def show_reports(self):
        self.clear_main()
        header = tk.Frame(self.main, bg=BG)
        header.pack(fill="x", pady=(0, 20))
        tk.Label(header, text="Reports & Analytics", font=("Segoe UI", 24, "bold"), bg=BG, fg=TEXT).pack(side="left")

        if not MATPLOTLIB_AVAILABLE:
            tk.Label(self.main, text="Install matplotlib for charts: pip install matplotlib",
                    font=("Segoe UI", 14), bg=BG, fg=TEXT2).pack(expand=True)
            return

        charts = tk.Frame(self.main, bg=BG)
        charts.pack(fill="both", expand=True)

        top_row = tk.Frame(charts, bg=BG)
        top_row.pack(fill="both", expand=True, pady=5)

        c1 = tk.Frame(top_row, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1)
        c1.pack(side="left", expand=True, fill="both", padx=(0, 10))
        tk.Label(c1, text="Shot Type Distribution", font=("Segoe UI", 12, "bold"), bg=SURFACE, fg=TEXT).pack(pady=10)
        self.draw_vbar_chart(c1, self.data.get_type_counts(), ACCENT)

        c2 = tk.Frame(top_row, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1)
        c2.pack(side="right", expand=True, fill="both", padx=(10, 0))
        tk.Label(c2, text="Artist Workload", font=("Segoe UI", 12, "bold"), bg=SURFACE, fg=TEXT).pack(pady=10)
        workload = self.data.get_artist_workload()
        if workload:
            self.draw_vbar_chart(c2, {k: v["total"] for k, v in workload.items()}, PURPLE)
        else:
            tk.Label(c2, text="No data", bg=SURFACE, fg=TEXT2).pack(expand=True)

        bottom_row = tk.Frame(charts, bg=BG)
        bottom_row.pack(fill="both", expand=True, pady=5)

        c3 = tk.Frame(bottom_row, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1)
        c3.pack(side="left", expand=True, fill="both", padx=(0, 10))
        tk.Label(c3, text="Priority Breakdown", font=("Segoe UI", 12, "bold"), bg=SURFACE, fg=TEXT).pack(pady=10)
        self.draw_vbar_chart(c3, self.data.get_priority_counts(), ORANGE)

        c4 = tk.Frame(bottom_row, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1)
        c4.pack(side="right", expand=True, fill="both", padx=(10, 0))
        tk.Label(c4, text="Retakes by Shot", font=("Segoe UI", 12, "bold"), bg=SURFACE, fg=TEXT).pack(pady=10)
        retakes = self.data.get_retake_by_shot()
        if retakes:
            self.draw_vbar_chart(c4, retakes, DANGER)
        else:
            tk.Label(c4, text="No retakes yet", bg=SURFACE, fg=TEXT2).pack(expand=True)

    def draw_vbar_chart(self, parent, data, color):
        fig = Figure(figsize=(5, 3), dpi=100, facecolor=SURFACE)
        ax = fig.add_subplot(111)
        ax.set_facecolor(SURFACE)

        if data:
            labels = list(data.keys())[:10]
            values = [data[k] for k in labels]
            bars = ax.bar(labels, values, color=color, width=0.6)
            ax.tick_params(colors=TEXT2, labelsize=9)
            ax.spines['bottom'].set_color(BORDER)
            ax.spines['left'].set_color(BORDER)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            for bar, val in zip(bars, values):
                ax.text(bar.get_x() + bar.get_width()/2, val + 0.1, str(val),
                       ha='center', color=TEXT, fontsize=9, fontweight='bold')
        else:
            ax.text(0.5, 0.5, "No data yet", ha='center', va='center',
                   transform=ax.transAxes, color=TEXT2, fontsize=12)

        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

if __name__ == "__main__":
    root = tk.Tk()
    app = ShowTrackerApp(root)
    root.mainloop()
