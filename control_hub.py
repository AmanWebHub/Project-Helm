"""Helm - a dashboard for launching Windows system tools.

Run: python control_hub.py
Add or remove tools by editing the TOOLS list below.
"""
import json
import os
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog

SYSTEM32 = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32")
APP_DATA = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
                        "ControlHub", "custom_apps.json")
# (name, description, command, required file, category, icon text, accent, featured[, custom])
TOOLS = [
    ("Registry Editor", "Browse and edit the Windows registry.", "regedit", None,
     "System", "REG", "#7b8cff", True),
    ("Power Options", "Adjust power plans, sleep, and battery settings.", "control powercfg.cpl", None,
     "Power", "PWR", "#e9ad58", True),
    ("Account Manager", "Manage local user accounts and sign-in options.", "netplwiz", None,
     "System", "USR", "#56a9e8", True),
    ("Group Policy Editor", "Manage local policies (Pro, Enterprise, or Education).", "gpedit.msc",
     os.path.join(SYSTEM32, "gpedit.msc"), "System", "POL", "#b78af2", True),
    ("Device Manager", "View hardware, drivers, and device status.", "devmgmt.msc", None,
     "Devices", "DEV", "#57c6b6", True),
    ("Devices and Printers", "Manage printers, scanners, and connected devices.", "control printers", None,
     "Devices", "I/O", "#56a9e8", True),
    ("Programs and Features", "Uninstall or change installed programs.", "appwiz.cpl", None,
     "Apps", "APP", "#e4819b", False),
    ("Network Connections", "Manage network adapters and connections.", "ncpa.cpl", None,
     "System", "NET", "#57c6b6", False),
    ("System Properties", "Computer name, performance, and advanced settings.", "sysdm.cpl", None,
     "System", "SYS", "#7b8cff", False),
    ("Services", "View and configure Windows background services.", "services.msc", None,
     "System", "SVC", "#b78af2", False),
    ("Disk Management", "Manage disk partitions and storage volumes.", "diskmgmt.msc", None,
     "System", "DSK", "#e9ad58", False),
    ("Event Viewer", "Review Windows system and application logs.", "eventvwr.msc", None,
     "System", "LOG", "#56a9e8", False),
    ("Task Manager", "Check running apps and system performance.", "taskmgr", None,
     "System", "CPU", "#e4819b", False),
]

BG = "#10141c"
PANEL = "#171d27"
CARD = "#1b2330"
HOVER = "#242e3d"
BORDER = "#2a3443"
ACCENT = "#79aaff"
TEXT = "#edf2f8"
MUTED = "#929eaf"
CARD_W = 270
CATEGORIES = ("All tools", "System", "Power", "Devices", "Apps")


def launch(name, command, required):
    if required and not os.path.exists(required):
        messagebox.showinfo(
            name, f"{name} isn't available on this edition of Windows "
                  "(for example, Windows 11 Home).")
        return
    try:
        subprocess.Popen(command, shell=True, creationflags=0x08000000)
    except Exception as exc:
        messagebox.showerror(name, f"Could not open {name}:\n{exc}")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Helm")
        self.geometry("980x720")
        self._set_app_icon()
        self.minsize(600, 540)
        self.configure(bg=BG)
        self.active_category = "All tools"
        self.visible_tools = []
        self.cards = []

        self._build_header()
        self._build_search()
        self._build_categories()
        self._build_tool_area()
        self._build_footer()

        self.custom_apps = self.load_custom_apps()
        for tool in TOOLS + self.custom_tool_entries():
            self.cards.append((tool, self.make_card(tool)))
        self.set_category("All tools")
        self.bind("<Control-f>", self.focus_search)
        self.bind("<Escape>", self.reset_filters)

    def _set_app_icon(self):
        size = 32
        image = tk.PhotoImage(width=size, height=size)
        rows = []
        scale = 256 / size
        for y in range(size):
            row = []
            for x in range(size):
                px, py = (x + 0.5) * scale, (y + 0.5) * scale
                color = "#11151c" if 8 <= px < 248 and 8 <= py < 248 else "#000000"
                if 8 <= px < 248 and 8 <= py < 248:
                    color = "#11151c"
                    tiles = ((52, 52, 120, 120, "#4f9cf9"),
                             (136, 52, 204, 120, "#2a3546"),
                             (52, 136, 120, 204, "#2a3546"),
                             (136, 136, 204, 204, "#2a3546"))
                    for left, top, right, bottom, fill in tiles:
                        if left <= px < right and top <= py < bottom:
                            color = fill
                    if self._near_line(px, py, 80, 72, 98, 86, 4.5) or self._near_line(
                            px, py, 98, 86, 80, 100, 4.5):
                        color = "#11151c"
                    if (px - 170) ** 2 + (py - 170) ** 2 <= 9 ** 2:
                        color = "#4f9cf9"
                row.append(color)
            rows.append(row)
        for y, row in enumerate(rows):
            image.put("{" + " ".join(row) + "}", to=(0, y))
        self._helm_icon_image = image
        self.iconphoto(True, image)

    @staticmethod
    def _near_line(px, py, x1, y1, x2, y2, radius):
        dx, dy = x2 - x1, y2 - y1
        length_squared = dx * dx + dy * dy
        position = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / length_squared))
        nearest_x, nearest_y = x1 + position * dx, y1 + position * dy
        return (px - nearest_x) ** 2 + (py - nearest_y) ** 2 <= radius ** 2

    @staticmethod
    def _draw_helm_mark(canvas, size):
        scale = size / 256
        def box(x1, y1, x2, y2, fill, radius=18):
            x1, y1, x2, y2, radius = (value * scale for value in (x1, y1, x2, y2, radius))
            canvas.create_rectangle(x1 + radius, y1, x2 - radius, y2, fill=fill, outline="")
            canvas.create_rectangle(x1, y1 + radius, x2, y2 - radius, fill=fill, outline="")
            for x, y in ((x1, y1), (x2 - radius * 2, y1),
                         (x1, y2 - radius * 2), (x2 - radius * 2, y2 - radius * 2)):
                canvas.create_oval(x, y, x + radius * 2, y + radius * 2, fill=fill, outline="")

        box(8, 8, 248, 248, "#11151c", 56)
        for bounds, color in (((52, 52, 120, 120), "#4f9cf9"),
                              ((136, 52, 204, 120), "#2a3546"),
                              ((52, 136, 120, 204), "#2a3546"),
                              ((136, 136, 204, 204), "#2a3546")):
            box(*bounds, color)
        canvas.create_line(80 * scale, 72 * scale, 98 * scale, 86 * scale,
                           80 * scale, 100 * scale, fill="#11151c",
                           width=9 * scale, capstyle="round", joinstyle="round")
        canvas.create_oval(161 * scale, 161 * scale, 179 * scale, 179 * scale,
                           fill="#4f9cf9", outline="")

    def _build_header(self):
        top = tk.Frame(self, bg=BG)
        top.pack(fill="x", padx=30, pady=(25, 16))

        brand = tk.Frame(top, bg=BG)
        brand.pack(fill="x")
        mark = tk.Canvas(brand, width=38, height=38, bg=BG, bd=0, highlightthickness=0)
        mark.pack(side="left", padx=(0, 10))
        self._draw_helm_mark(mark, 38)
        tk.Label(brand, text="HELM", font=("Segoe UI", 9, "bold"),
                 bg=BG, fg=MUTED).pack(side="left")
        tk.Button(brand, text="+  Add a program", command=self.add_custom_app,
                  font=("Segoe UI", 9, "bold"), bg="#263954", fg=ACCENT,
                  activebackground="#314969", activeforeground=TEXT,
                  relief="flat", bd=0, cursor="hand2", padx=12, pady=7).pack(side="right")
        tk.Label(top, text="Windows, within reach.", font=("Segoe UI", 24, "bold"),
                 bg=BG, fg=TEXT).pack(anchor="w", pady=(14, 2))
        tk.Label(top, text="Your everyday system tools, together in one place.",
                 font=("Segoe UI", 10), bg=BG, fg=MUTED).pack(anchor="w")

    def _build_search(self):
        row = tk.Frame(self, bg=BG)
        row.pack(fill="x", padx=30, pady=(0, 13))
        search_box = tk.Frame(row, bg=PANEL, highlightthickness=1,
                              highlightbackground=BORDER, highlightcolor=ACCENT)
        search_box.pack(fill="x")
        tk.Label(search_box, text="SEARCH", font=("Segoe UI", 8, "bold"),
                 bg=PANEL, fg=MUTED).pack(side="left", padx=(13, 9))
        self.query = tk.StringVar()
        self.search_placeholder = "Find a tool or setting..."
        self.placeholder_active = True
        self.search = tk.Entry(search_box, textvariable=self.query, font=("Segoe UI", 11),
                                bg=PANEL, fg=MUTED, insertbackground=TEXT,
                                relief="flat", bd=0)
        self.search.pack(side="left", fill="x", expand=True, ipady=13, pady=2)
        self.search.insert(0, self.search_placeholder)
        clear = tk.Button(search_box, text="Clear", command=self.clear_search,
                          font=("Segoe UI", 9), bg=PANEL, fg=MUTED,
                          activebackground=PANEL, activeforeground=TEXT,
                          relief="flat", bd=0, cursor="hand2")
        clear.pack(side="right", padx=12)
        self.search.bind("<FocusIn>", self._clear_placeholder)
        self.search.bind("<FocusOut>", self._restore_placeholder)
        self.search.bind("<Return>", self.open_first)
        self.query.trace_add("write", lambda *_: self.refresh())

    def _build_categories(self):
        bar = tk.Frame(self, bg=BG)
        bar.pack(fill="x", padx=30, pady=(0, 13))
        self.category_buttons = {}
        for category in CATEGORIES:
            button = tk.Button(
                bar, text=category, command=lambda value=category: self.set_category(value),
                font=("Segoe UI", 9, "bold"), relief="flat", bd=0, cursor="hand2",
                padx=13, pady=7, highlightthickness=0)
            button.pack(side="left", padx=(0, 7))
            self.category_buttons[category] = button
        self.result_label = tk.Label(bar, text="", font=("Segoe UI", 9), bg=BG, fg=MUTED)
        self.result_label.pack(side="right", padx=(8, 0))

    def _build_tool_area(self):
        shell = tk.Frame(self, bg=BG)
        shell.pack(fill="both", expand=True, padx=(24, 20), pady=(0, 10))
        self.canvas = tk.Canvas(shell, bg=BG, bd=0, highlightthickness=0)
        scrollbar = tk.Scrollbar(shell, orient="vertical", command=self.canvas.yview,
                                 bg=BG, troughcolor=BG, activebackground=BORDER,
                                 relief="flat", bd=0, width=9)
        self.canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y", padx=(5, 0))
        self.canvas.pack(side="left", fill="both", expand=True)
        self.grid_frame = tk.Frame(self.canvas, bg=BG)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.grid_frame, anchor="nw")
        self.grid_frame.bind("<Configure>", self._update_scroll_region)
        self.grid_frame.bind("<MouseWheel>", self._scroll)
        self.canvas.bind("<Configure>", self._resize_grid)
        self.canvas.bind("<MouseWheel>", self._scroll)
        self.empty_label = tk.Label(
            self.grid_frame, text="No tools match that search.\nTry a different name or category.",
            font=("Segoe UI", 11), bg=BG, fg=MUTED, justify="center")

    def _build_footer(self):
        footer = tk.Frame(self, bg=BG)
        footer.pack(fill="x", padx=30, pady=(0, 16))
        tk.Frame(footer, bg=BORDER, height=1).pack(fill="x", pady=(0, 10))
        tk.Label(footer, text="Select a tile to open a Windows utility",
                 font=("Segoe UI", 9), bg=BG, fg=MUTED).pack(side="left")
        tk.Label(footer, text="CTRL + F  Search   ·   ESC  Reset",
                 font=("Segoe UI", 9), bg=BG, fg=MUTED).pack(side="right")

    def load_custom_apps(self):
        try:
            with open(APP_DATA, "r", encoding="utf-8") as settings:
                apps = json.load(settings)
            if not isinstance(apps, list):
                raise ValueError("The saved app list must be a list.")
            for app in apps:
                if (not isinstance(app, dict) or not isinstance(app.get("name"), str)
                        or not app["name"].strip() or not isinstance(app.get("path"), str)
                        or not app["path"].strip()):
                    raise ValueError("A saved app entry is missing its name or file path.")
            return apps
        except FileNotFoundError:
            return []
        except (OSError, ValueError) as exc:
            self.custom_apps_load_failed = True
            messagebox.showerror(
                "Couldn't load custom apps",
                f"The saved app list couldn't be read. You can still use the built-in tools.\n\n{exc}",
                parent=self)
            return []

    def save_custom_apps(self, apps):
        temporary = APP_DATA + ".tmp"
        try:
            os.makedirs(os.path.dirname(APP_DATA), exist_ok=True)
            with open(temporary, "w", encoding="utf-8") as settings:
                json.dump(apps, settings, indent=2, ensure_ascii=False)
            os.replace(temporary, APP_DATA)
            return True
        except OSError as exc:
            try:
                os.remove(temporary)
            except FileNotFoundError:
                pass
            messagebox.showerror("Couldn't save custom apps", str(exc), parent=self)
            return False

    def custom_tool_entries(self):
        return [
            (app["name"], "Your custom app or program.", app["path"], None,
             "Apps", "APP", "#8ec9a6", False, True)
            for app in self.custom_apps
        ]

    def add_custom_app(self):
        if getattr(self, "custom_apps_load_failed", False):
            messagebox.showerror(
                "Custom apps unavailable",
                "The saved app list couldn't be read, so changes are disabled to protect it.",
                parent=self)
            return
        path = filedialog.askopenfilename(
            parent=self, title="Choose a program or app",
            filetypes=[("Programs and shortcuts", "*.exe *.lnk *.url *.bat *.cmd"),
                       ("All files", "*.*")])
        if not path:
            return
        if not os.path.isfile(path):
            messagebox.showerror("Can't add this app", "Choose an existing program or shortcut.",
                                 parent=self)
            return
        normalized_path = os.path.normcase(os.path.abspath(path))
        if any(os.path.normcase(os.path.abspath(app["path"])) == normalized_path
               for app in self.custom_apps):
            messagebox.showinfo("Already added", "That program is already on your dashboard.",
                                parent=self)
            return
        default_name = os.path.splitext(os.path.basename(path))[0]
        name = simpledialog.askstring("Name this shortcut", "What should this shortcut be called?",
                                      initialvalue=default_name, parent=self)
        if name is None:
            return
        name = name.strip()
        if not name:
            messagebox.showerror("Name required", "Enter a name for this shortcut.", parent=self)
            return
        apps = self.custom_apps + [{"name": name, "path": os.path.abspath(path)}]
        if not self.save_custom_apps(apps):
            return
        self.custom_apps = apps
        tool = self.custom_tool_entries()[-1]
        self.cards.append((tool, self.make_card(tool)))
        self.refresh()

    def remove_custom_app(self, path):
        if not messagebox.askyesno("Remove shortcut", "Remove this app from the dashboard?",
                                   parent=self):
            return
        apps = [app for app in self.custom_apps if app["path"] != path]
        if len(apps) == len(self.custom_apps) or not self.save_custom_apps(apps):
            return
        self.custom_apps = apps
        for index, (tool, card) in enumerate(self.cards):
            if len(tool) > 8 and tool[8] and tool[2] == path:
                self.cards.pop(index)
                card.destroy()
                break
        self.refresh()

    def open_tool(self, tool):
        name, _description, command, required = tool[:4]
        if len(tool) > 8 and tool[8]:
            try:
                if hasattr(os, "startfile"):
                    os.startfile(command)
                else:
                    subprocess.Popen([command], shell=False)
            except OSError as exc:
                messagebox.showerror(name, f"Could not open {name}:\n{exc}", parent=self)
        else:
            launch(name, command, required)

    def _clear_placeholder(self, _event=None):
        if self.placeholder_active:
            self.search.delete(0, "end")
            self.search.configure(fg=TEXT)
            self.placeholder_active = False

    def _restore_placeholder(self, _event=None):
        if not self.search.get().strip():
            self.placeholder_active = True
            self.search.delete(0, "end")
            self.search.insert(0, self.search_placeholder)
            self.search.configure(fg=MUTED)

    def _search_text(self):
        return "" if self.placeholder_active else self.query.get().strip().lower()

    def clear_search(self):
        self._clear_placeholder()
        self.search.delete(0, "end")
        self.search.focus_set()

    def focus_search(self, _event=None):
        self.search.focus_set()
        self._clear_placeholder()
        self.search.select_range(0, "end")
        return "break"

    def reset_filters(self, _event=None):
        self.set_category("All tools")
        self.clear_search()
        return "break"

    def set_category(self, category):
        self.active_category = category
        for name, button in self.category_buttons.items():
            selected = name == category
            button.configure(bg="#263954" if selected else BG,
                             fg=ACCENT if selected else MUTED,
                             activebackground="#263954" if selected else HOVER,
                             activeforeground=TEXT)
        self.refresh()

    def make_card(self, tool):
        name, desc, command, required, category, icon, accent, featured = tool[:8]
        custom = len(tool) > 8 and tool[8]
        card = tk.Frame(self.grid_frame, bg=CARD, cursor="hand2", padx=15, pady=14,
                        highlightthickness=1, highlightbackground=BORDER)
        top = tk.Frame(card, bg=CARD)
        top.pack(fill="x")
        badge = tk.Label(top, text=icon, font=("Segoe UI", 8, "bold"), width=5, height=2,
                         bg="#263040", fg=accent)
        badge.pack(side="left", anchor="n", padx=(0, 11))
        heading = tk.Frame(top, bg=CARD)
        heading.pack(side="left", fill="x", expand=True)
        tk.Label(heading, text=name, font=("Segoe UI", 11, "bold"),
                 bg=CARD, fg=TEXT, anchor="w").pack(fill="x", pady=(1, 2))
        caption = "QUICK ACCESS" if featured else category.upper()
        tk.Label(heading, text=caption, font=("Segoe UI", 8, "bold"),
                 bg=CARD, fg=accent if featured else MUTED, anchor="w").pack(fill="x")
        tk.Label(card, text=desc, font=("Segoe UI", 9), bg=CARD, fg=MUTED,
                 anchor="w", justify="left", wraplength=CARD_W - 32).pack(
                     fill="x", pady=(11, 12))
        tk.Frame(card, bg=BORDER, height=1).pack(fill="x", pady=(0, 9))
        remove_button = None
        if custom:
            actions = tk.Frame(card, bg=CARD)
            actions.pack(fill="x")
            tk.Label(actions, text="OPEN APP     >", font=("Segoe UI", 8, "bold"),
                     bg=CARD, fg=accent, anchor="w").pack(side="left", fill="x", expand=True)
            remove_button = tk.Button(
                actions, text="Remove", command=lambda value=command: self.remove_custom_app(value),
                font=("Segoe UI", 8), bg=CARD, fg=MUTED, activebackground=HOVER,
                activeforeground=TEXT, relief="flat", bd=0, cursor="hand2")
            remove_button.pack(side="right")
        else:
            tk.Label(card, text="OPEN TOOL     >", font=("Segoe UI", 8, "bold"),
                     bg=CARD, fg=accent, anchor="w").pack(fill="x")

        widgets = [card]
        for child in card.winfo_children():
            if child is remove_button:
                continue
            widgets.append(child)
            widgets.extend(widget for widget in child.winfo_children()
                           if widget is not remove_button)
            for nested in child.winfo_children():
                widgets.extend(nested.winfo_children())

        def paint(color):
            card.configure(bg=color, highlightbackground=accent if color == HOVER else BORDER)
            for widget in widgets[1:]:
                if widget is not badge and widget.winfo_exists():
                    try:
                        widget.configure(bg=color)
                    except tk.TclError:
                        pass

        def enter(_event):
            paint(HOVER)

        def leave(_event):
            paint(CARD)

        def open_tool(_event):
            self.open_tool(tool)
            return "break"

        for widget in widgets:
            widget.bind("<Enter>", enter)
            widget.bind("<Leave>", leave)
            widget.bind("<Button-1>", open_tool)
            widget.bind("<MouseWheel>", self._scroll)
        return card

    def visible(self):
        query = self._search_text()
        matches = []
        for tool, card in self.cards:
            name, desc, _command, _required, category = tool[:5]
            category_match = self.active_category == "All tools" or category == self.active_category
            text_match = not query or query in name.lower() or query in desc.lower()
            if category_match and text_match:
                matches.append((tool, card))
        return matches

    def refresh(self):
        if not hasattr(self, "cards"):
            return
        self.visible_tools = self.visible()
        total = len(self.visible_tools)
        self.result_label.configure(text=f"{total} {('tool' if total == 1 else 'tools')}")
        self._layout_cards()

    def _resize_grid(self, event):
        self.canvas.itemconfigure(self.canvas_window, width=event.width)
        self._layout_cards()

    def _update_scroll_region(self, _event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _layout_cards(self):
        if not hasattr(self, "visible_tools"):
            return
        for _, card in self.cards:
            card.grid_forget()
        self.empty_label.grid_forget()
        width = max(1, self.canvas.winfo_width())
        columns = max(1, min(4, width // (CARD_W + 18)))
        for column in range(4):
            self.grid_frame.grid_columnconfigure(column, weight=1 if column < columns else 0,
                                                 uniform="cards" if column < columns else "")
        if not self.visible_tools:
            self.empty_label.grid(row=0, column=0, columnspan=columns, sticky="ew", pady=55)
        else:
            for index, (_tool, card) in enumerate(self.visible_tools):
                card.grid(row=index // columns, column=index % columns,
                          padx=6, pady=6, sticky="nsew")
        self.canvas.yview_moveto(0)
        self.after_idle(self._update_scroll_region)

    def _scroll(self, event):
        delta = -1 * int(event.delta / 120)
        if not delta:
            delta = -1 if event.delta > 0 else 1
        self.canvas.yview_scroll(delta, "units")
        return "break"

    def open_first(self, _event=None):
        matches = self.visible()
        if matches:
            self.open_tool(matches[0][0])
            return "break"


if __name__ == "__main__":
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    App().mainloop()
