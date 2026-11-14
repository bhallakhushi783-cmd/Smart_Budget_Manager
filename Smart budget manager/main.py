"""
SMART BUDGET MANAGER ULTIMATE
A polished desktop personal-finance application built with:
- Python standard library: tkinter, csv, json, pathlib, datetime
- Matplotlib for charts

Files created beside this script:
    expenses.csv          Permanent transaction storage
    budget_settings.json  Budget and preferences
    categories.json       Custom categories

Run:
    pip install matplotlib
    python smart_budget_ultimate.py
"""

import csv
import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from datetime import datetime, date
from collections import defaultdict
import calendar

try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


# ============================================================
# APPLICATION CONFIGURATION
# ============================================================

APP_NAME = "NOVA  |  SMART BUDGET"
APP_VERSION = "3.0"
BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "expenses.csv"
SETTINGS_FILE = BASE_DIR / "budget_settings.json"
CATEGORY_FILE = BASE_DIR / "categories.json"

DEFAULT_CATEGORIES = [
    "Food", "Transport", "Shopping", "Bills",
    "Education", "Entertainment", "Health", "Travel",
    "Personal Care", "Subscriptions", "Others"
]

PALETTE = {
    "background": "#0D1020",
    "sidebar": "#13172B",
    "surface": "#191F36",
    "surface_alt": "#202944",
    "surface_hover": "#293653",
    "border": "#303B59",
    "text": "#F4F6FF",
    "muted": "#9BA8C7",
    "purple": "#9B7BFF",
    "pink": "#F27CB8",
    "cyan": "#5BCBEB",
    "green": "#49D6A1",
    "yellow": "#F6C66B",
    "red": "#FF718B",
    "blue": "#669CFF",
    "white": "#FFFFFF",
}

LIGHT_PALETTE = {
    "background": "#F3F5FB",
    "sidebar": "#FFFFFF",
    "surface": "#FFFFFF",
    "surface_alt": "#E9EDF7",
    "surface_hover": "#DDE4F3",
    "border": "#D5DCEC",
    "text": "#202943",
    "muted": "#69758F",
    "purple": "#7654DB",
    "pink": "#D94E99",
    "cyan": "#168EAF",
    "green": "#15966A",
    "yellow": "#B47A16",
    "red": "#D9435F",
    "blue": "#356FD4",
    "white": "#FFFFFF",
}

CURRENCY = "₹"
CSV_FIELDS = ["id", "date", "category", "amount", "note", "payment", "type"]
PAYMENT_METHODS = [
    "Cash", "UPI", "Debit Card", "Credit Card",
    "Net Banking", "Wallet", "Other"
]
TRANSACTION_TYPES = ["Expense", "Income"]


# ============================================================
# SMALL REUSABLE UI HELPERS
# ============================================================

def money(value):
    """Format a number as Indian rupees."""
    try:
        return f"{CURRENCY}{float(value):,.2f}"
    except (TypeError, ValueError):
        return f"{CURRENCY}0.00"


def today_string():
    return date.today().strftime("%Y-%m-%d")


def month_key(value):
    return value[:7]


def safe_float(value, default=0.0):
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


class RoundedButton(tk.Button):
    """Consistent button style for the entire application."""

    def __init__(self, parent, text, command=None, color=None,
                 text_color=None, compact=False, **kwargs):
        self.app = parent.winfo_toplevel()
        colors = getattr(self.app, "colors", PALETTE)
        super().__init__(
            parent,
            text=text,
            command=command,
            bg=color or colors["purple"],
            fg=text_color or colors["white"],
            activebackground=colors["surface_hover"],
            activeforeground=colors["text"],
            relief="flat",
            bd=0,
            cursor="hand2",
            font=("Segoe UI", 9 if compact else 10, "bold"),
            padx=12 if compact else 16,
            pady=7 if compact else 11,
            highlightthickness=0,
            **kwargs
        )
        self.default_color = color or colors["purple"]
        self.bind("<Enter>", self._hover_on)
        self.bind("<Leave>", self._hover_off)

    def _hover_on(self, _event):
        colors = getattr(self.app, "colors", PALETTE)
        self.configure(bg=colors["surface_hover"])

    def _hover_off(self, _event):
        self.configure(bg=self.default_color)


class Card(tk.Frame):
    """Reusable dashboard card."""

    def __init__(self, parent, accent=None, **kwargs):
        app = parent.winfo_toplevel()
        colors = getattr(app, "colors", PALETTE)
        super().__init__(
            parent,
            bg=colors["surface"],
            highlightbackground=accent or colors["border"],
            highlightthickness=1,
            bd=0,
            **kwargs
        )


class PageBase(tk.Frame):
    """Base class shared by all navigation pages."""

    def __init__(self, app, parent):
        super().__init__(parent, bg=app.colors["background"])
        self.app = app
        self.colors = app.colors

    def heading(self, title, subtitle):
        top = tk.Frame(self, bg=self.colors["background"])
        top.pack(fill="x", pady=(0, 18))
        tk.Label(
            top, text=title, bg=self.colors["background"],
            fg=self.colors["text"], font=("Segoe UI", 22, "bold")
        ).pack(anchor="w")
        tk.Label(
            top, text=subtitle, bg=self.colors["background"],
            fg=self.colors["muted"], font=("Segoe UI", 10)
        ).pack(anchor="w", pady=(4, 0))
        return top

    def make_label(self, parent, text, size=10, color=None, bold=False):
        return tk.Label(
            parent, text=text, bg=self.colors["surface"],
            fg=color or self.colors["text"],
            font=("Segoe UI", size, "bold" if bold else "normal")
        )

    def entry(self, parent, variable, width=None):
        widget = tk.Entry(
            parent, textvariable=variable, width=width,
            bg=self.colors["surface_alt"],
            fg=self.colors["text"],
            insertbackground=self.colors["text"],
            relief="flat", bd=0,
            font=("Segoe UI", 10)
        )
        widget.pack(fill="x", ipady=9, pady=(5, 12))
        return widget


# ============================================================
# MAIN APPLICATION
# ============================================================

class SmartBudgetApp(tk.Tk):

    def __init__(self):
        super().__init__()

        self.title(f"{APP_NAME}  •  Ultimate Edition")
        self.geometry("1320x830")
        self.minsize(1080, 700)

        self.settings = self.load_settings()
        self.categories = self.load_categories()
        self.dark_mode = self.settings.get("dark_mode", True)
        self.colors = PALETTE if self.dark_mode else LIGHT_PALETTE

        self.transactions = []
        self.current_page = "Dashboard"
        self.selected_transaction_id = None
        self.page_objects = {}
        self.nav_buttons = {}

        self.configure(bg=self.colors["background"])
        self.load_transactions()
        self.build_shell()
        self.show_page("Dashboard")
        self.update_clock()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    # --------------------------------------------------------
    # PERSISTENT SETTINGS
    # --------------------------------------------------------

    def load_settings(self):
        defaults = {
            "monthly_budget": 2000.0,
            "dark_mode": True,
            "currency": "₹",
            "budget_alert": True,
            "last_page": "Dashboard"
        }
        if SETTINGS_FILE.exists():
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as file:
                    loaded = json.load(file)
                defaults.update(loaded)
            except (OSError, json.JSONDecodeError):
                pass
        return defaults

    def save_settings(self):
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as file:
                json.dump(self.settings, file, indent=4)
            return True
        except OSError as error:
            messagebox.showerror("Settings", f"Could not save settings:\n{error}")
            return False

    def load_categories(self):
        if CATEGORY_FILE.exists():
            try:
                with open(CATEGORY_FILE, "r", encoding="utf-8") as file:
                    values = json.load(file)
                if isinstance(values, list) and values:
                    return values
            except (OSError, json.JSONDecodeError):
                pass
        return DEFAULT_CATEGORIES.copy()

    def save_categories(self):
        try:
            with open(CATEGORY_FILE, "w", encoding="utf-8") as file:
                json.dump(self.categories, file, indent=4)
        except OSError as error:
            messagebox.showerror("Categories", str(error))

    # --------------------------------------------------------
    # CSV DATABASE
    # --------------------------------------------------------

    def load_transactions(self):
        self.transactions = []
        if not DATA_FILE.exists():
            return

        try:
            with open(DATA_FILE, "r", newline="", encoding="utf-8-sig") as file:
                reader = csv.DictReader(file)
                for row_number, row in enumerate(reader, start=1):
                    try:
                        # Older project CSVs only had Category and Amount.
                        category = (row.get("category") or row.get("Category") or "Others").strip()
                        amount = float(row.get("amount") or row.get("Amount") or 0)
                        tx_date = (row.get("date") or row.get("Date") or today_string()).strip()
                        note = (row.get("note") or row.get("Note") or "").strip()
                        payment = (row.get("payment") or "Cash").strip()
                        tx_type = (row.get("type") or "Expense").strip()
                        datetime.strptime(tx_date, "%Y-%m-%d")
                        if amount <= 0:
                            continue
                        identifier = row.get("id") or f"OLD-{row_number:05d}"
                        self.transactions.append({
                            "id": identifier,
                            "date": tx_date,
                            "category": category,
                            "amount": amount,
                            "note": note,
                            "payment": payment,
                            "type": tx_type if tx_type in TRANSACTION_TYPES else "Expense"
                        })
                    except (ValueError, TypeError):
                        continue
        except (OSError, csv.Error) as error:
            messagebox.showerror("CSV Database", f"Could not read expenses.csv:\n{error}")

    def save_transactions(self):
        try:
            with open(DATA_FILE, "w", newline="", encoding="utf-8") as file:
                writer = csv.DictWriter(file, fieldnames=CSV_FIELDS)
                writer.writeheader()
                writer.writerows(self.transactions)
            return True
        except OSError as error:
            messagebox.showerror("CSV Database", f"Could not save expenses.csv:\n{error}")
            return False

    def add_record(self, record):
        self.transactions.append(record)
        if not self.save_transactions():
            self.transactions.pop()
            return False
        self.refresh_everything()
        return True

    def update_record(self, identifier, replacement):
        index = self.find_index(identifier)
        if index is None:
            return False
        previous = self.transactions[index].copy()
        self.transactions[index] = replacement
        if not self.save_transactions():
            self.transactions[index] = previous
            return False
        self.refresh_everything()
        return True

    def delete_record(self, identifier):
        index = self.find_index(identifier)
        if index is None:
            return False
        previous = self.transactions.pop(index)
        if not self.save_transactions():
            self.transactions.insert(index, previous)
            return False
        self.refresh_everything()
        return True

    def find_index(self, identifier):
        for index, item in enumerate(self.transactions):
            if item["id"] == identifier:
                return index
        return None

    # --------------------------------------------------------
    # DATA CALCULATIONS
    # --------------------------------------------------------

    def all_expenses(self):
        return [x for x in self.transactions if x["type"] == "Expense"]

    def all_income(self):
        return [x for x in self.transactions if x["type"] == "Income"]

    def total_expenses(self):
        return sum(x["amount"] for x in self.all_expenses())

    def total_income(self):
        return sum(x["amount"] for x in self.all_income())

    def month_expenses(self, selected_month=None):
        selected_month = selected_month or datetime.now().strftime("%Y-%m")
        return sum(
            x["amount"] for x in self.all_expenses()
            if x["date"].startswith(selected_month)
        )

    def month_income(self, selected_month=None):
        selected_month = selected_month or datetime.now().strftime("%Y-%m")
        return sum(
            x["amount"] for x in self.all_income()
            if x["date"].startswith(selected_month)
        )

    def balance(self):
        return self.total_income() - self.total_expenses()

    def category_totals(self, tx_type="Expense", selected_month=None):
        totals = defaultdict(float)
        for item in self.transactions:
            if item["type"] != tx_type:
                continue
            if selected_month and not item["date"].startswith(selected_month):
                continue
            totals[item["category"]] += item["amount"]
        return dict(totals)

    def recent_transactions(self, limit=8):
        return sorted(
            self.transactions,
            key=lambda x: (x["date"], x["id"]),
            reverse=True
        )[:limit]

    # --------------------------------------------------------
    # APPLICATION SHELL / SIDEBAR
    # --------------------------------------------------------

    def build_shell(self):
        self.shell = tk.Frame(self, bg=self.colors["background"])
        self.shell.pack(fill="both", expand=True)

        self.sidebar = tk.Frame(
            self.shell, bg=self.colors["sidebar"], width=230
        )
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        self.main_area = tk.Frame(
            self.shell, bg=self.colors["background"]
        )
        self.main_area.pack(side="left", fill="both", expand=True)

        self.build_sidebar()
        self.build_topbar()

        self.content = tk.Frame(
            self.main_area, bg=self.colors["background"]
        )
        self.content.pack(fill="both", expand=True, padx=25, pady=20)

    def build_sidebar(self):
        brand = tk.Frame(self.sidebar, bg=self.colors["sidebar"])
        brand.pack(fill="x", padx=18, pady=(25, 28))

        tk.Label(
            brand, text="✦  NOVA", bg=self.colors["sidebar"],
            fg=self.colors["purple"], font=("Segoe UI", 21, "bold")
        ).pack(anchor="w")
        tk.Label(
            brand, text="PERSONAL FINANCE", bg=self.colors["sidebar"],
            fg=self.colors["muted"], font=("Segoe UI", 8, "bold")
        ).pack(anchor="w", pady=(3, 0))

        nav_items = [
            ("⌂", "Dashboard"),
            ("＋", "Add Transaction"),
            ("▤", "Transactions"),
            ("◉", "Analytics"),
            ("◈", "Budget Planner"),
            ("⇩", "Reports"),
            ("⚙", "Settings"),
            ("ⓘ", "About Project"),
        ]

        tk.Label(
            self.sidebar, text="WORKSPACE", bg=self.colors["sidebar"],
            fg=self.colors["muted"], font=("Segoe UI", 8, "bold")
        ).pack(anchor="w", padx=20, pady=(0, 8))

        for symbol, name in nav_items:
            button = tk.Button(
                self.sidebar,
                text=f"  {symbol}    {name}",
                anchor="w",
                command=lambda page=name: self.show_page(page),
                bg=self.colors["sidebar"],
                fg=self.colors["muted"],
                activebackground=self.colors["surface_hover"],
                activeforeground=self.colors["text"],
                font=("Segoe UI", 10, "bold"),
                relief="flat", bd=0, cursor="hand2",
                padx=13, pady=12
            )
            button.pack(fill="x", padx=10, pady=2)
            self.nav_buttons[name] = button

        spacer = tk.Frame(self.sidebar, bg=self.colors["sidebar"])
        spacer.pack(fill="both", expand=True)

        self.sidebar_budget = tk.Frame(
            self.sidebar, bg=self.colors["surface"], padx=13, pady=13
        )
        self.sidebar_budget.pack(fill="x", padx=12, pady=14)

        tk.Label(
            self.sidebar_budget, text="MONTHLY BUDGET",
            bg=self.colors["surface"], fg=self.colors["muted"],
            font=("Segoe UI", 8, "bold")
        ).pack(anchor="w")

        self.sidebar_budget_value = tk.Label(
            self.sidebar_budget, text=money(self.settings["monthly_budget"]),
            bg=self.colors["surface"], fg=self.colors["green"],
            font=("Segoe UI", 16, "bold")
        )
        self.sidebar_budget_value.pack(anchor="w", pady=(5, 0))

        tk.Label(
            self.sidebar, text=f"Version {APP_VERSION}",
            bg=self.colors["sidebar"], fg=self.colors["muted"],
            font=("Segoe UI", 8)
        ).pack(anchor="w", padx=20, pady=(0, 15))

    def build_topbar(self):
        topbar = tk.Frame(
            self.main_area, bg=self.colors["surface"], height=58
        )
        topbar.pack(fill="x")
        topbar.pack_propagate(False)

        self.breadcrumb = tk.Label(
            topbar, text="Dashboard",
            bg=self.colors["surface"], fg=self.colors["text"],
            font=("Segoe UI", 11, "bold")
        )
        self.breadcrumb.pack(side="left", padx=24)

        self.clock_label = tk.Label(
            topbar, text="", bg=self.colors["surface"],
            fg=self.colors["muted"], font=("Segoe UI", 9)
        )
        self.clock_label.pack(side="right", padx=15)

        RoundedButton(
            topbar, "＋  Add New", self.open_add_page,
            color=self.colors["purple"], compact=True
        ).pack(side="right", padx=8, pady=10)

        RoundedButton(
            topbar, "◐ Theme", self.toggle_theme,
            color=self.colors["surface_alt"],
            text_color=self.colors["text"], compact=True
        ).pack(side="right", padx=4, pady=10)

    def update_clock(self):
        if self.winfo_exists():
            self.clock_label.config(
                text=datetime.now().strftime("%A, %d %B %Y   •   %I:%M %p")
            )
            self.after(30000, self.update_clock)

    # --------------------------------------------------------
    # PAGE NAVIGATION
    # --------------------------------------------------------

    def show_page(self, page_name):
        self.current_page = page_name
        self.settings["last_page"] = page_name
        self.breadcrumb.config(text=page_name)

        for name, button in self.nav_buttons.items():
            if name == page_name:
                button.config(
                    bg=self.colors["surface_alt"],
                    fg=self.colors["purple"]
                )
            else:
                button.config(
                    bg=self.colors["sidebar"],
                    fg=self.colors["muted"]
                )

        for child in self.content.winfo_children():
            child.destroy()

        page_map = {
            "Dashboard": DashboardPage,
            "Add Transaction": AddTransactionPage,
            "Transactions": TransactionsPage,
            "Analytics": AnalyticsPage,
            "Budget Planner": BudgetPlannerPage,
            "Reports": ReportsPage,
            "Settings": SettingsPage,
            "About Project": AboutPage,
        }

        page_class = page_map.get(page_name, DashboardPage)
        page = page_class(self, self.content)
        page.pack(fill="both", expand=True)
        self.page_objects[page_name] = page

    def open_add_page(self):
        self.show_page("Add Transaction")

    def refresh_everything(self):
        self.sidebar_budget_value.config(
            text=money(self.settings["monthly_budget"])
        )
        if self.current_page in self.nav_buttons:
            self.show_page(self.current_page)
        else:
            self.show_page("Dashboard")

    # --------------------------------------------------------
    # THEME
    # --------------------------------------------------------

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        self.colors = PALETTE if self.dark_mode else LIGHT_PALETTE
        self.settings["dark_mode"] = self.dark_mode
        self.save_settings()
        messagebox.showinfo(
            "Theme Changed",
            "Theme preference saved. The screen will refresh."
        )
        self.rebuild_window()

    def rebuild_window(self):
        for child in self.winfo_children():
            child.destroy()
        self.configure(bg=self.colors["background"])
        self.page_objects.clear()
        self.nav_buttons.clear()
        self.build_shell()
        self.show_page(self.current_page)

    # --------------------------------------------------------
    # BUDGET ALERTS AND EXPORT HELPERS
    # --------------------------------------------------------

    def check_budget_alert(self):
        limit = safe_float(self.settings.get("monthly_budget"), 0)
        spent = self.month_expenses()
        if limit > 0 and spent > limit and self.settings.get("budget_alert", True):
            messagebox.showwarning(
                "Budget limit crossed",
                f"This month's spending is {money(spent)}.\n"
                f"Your budget is {money(limit)}."
            )

    def export_records(self, records, suggested_name="budget_report.csv"):
        if not records:
            messagebox.showinfo("No Data", "There are no records to export.")
            return
        destination = filedialog.asksaveasfilename(
            title="Save CSV report",
            defaultextension=".csv",
            initialfile=suggested_name,
            filetypes=[("CSV files", "*.csv")]
        )
        if not destination:
            return
        try:
            with open(destination, "w", newline="", encoding="utf-8") as file:
                writer = csv.DictWriter(file, fieldnames=CSV_FIELDS)
                writer.writeheader()
                writer.writerows(records)
            messagebox.showinfo("Export Complete", f"Report saved:\n{destination}")
        except OSError as error:
            messagebox.showerror("Export Error", str(error))

    def on_close(self):
        self.save_settings()
        self.destroy()


# ============================================================
# DASHBOARD PAGE
# ============================================================

class DashboardPage(PageBase):

    def __init__(self, app, parent):
        super().__init__(app, parent)
        self.heading(
            "Good to see you! ✨",
            "Here is your personal finance overview."
        )
        self.build_summary_cards()
        self.build_middle_section()
        self.build_recent_table()

    def build_summary_cards(self):
        row = tk.Frame(self, bg=self.colors["background"])
        row.pack(fill="x", pady=(0, 17))

        month_spent = self.app.month_expenses()
        budget = safe_float(self.app.settings.get("monthly_budget"), 0)
        remaining = budget - month_spent

        self.summary_card(row, "TOTAL EXPENSES",
                          money(self.app.total_expenses()), self.colors["purple"])
        self.summary_card(row, "THIS MONTH",
                          money(month_spent), self.colors["pink"])
        self.summary_card(row, "TOTAL INCOME",
                          money(self.app.total_income()), self.colors["green"])
        self.summary_card(row, "BUDGET LEFT",
                          money(remaining), self.colors["cyan"] if remaining >= 0 else self.colors["red"])

    def summary_card(self, parent, title, value, accent):
        card = Card(parent, accent)
        card.pack(side="left", fill="both", expand=True, padx=5, ipady=11)
        tk.Label(
            card, text=title, bg=self.colors["surface"],
            fg=self.colors["muted"], font=("Segoe UI", 8, "bold")
        ).pack(anchor="w", padx=15, pady=(10, 5))
        tk.Label(
            card, text=value, bg=self.colors["surface"],
            fg=accent, font=("Segoe UI", 18, "bold")
        ).pack(anchor="w", padx=15, pady=(0, 10))

    def build_middle_section(self):
        middle = tk.Frame(self, bg=self.colors["background"])
        middle.pack(fill="both", expand=True, pady=(0, 15))

        budget_card = Card(middle)
        budget_card.pack(side="left", fill="both", expand=True, padx=(0, 8))

        tk.Label(
            budget_card, text="Monthly budget health",
            bg=self.colors["surface"], fg=self.colors["text"],
            font=("Segoe UI", 13, "bold")
        ).pack(anchor="w", padx=18, pady=(18, 5))

        spent = self.app.month_expenses()
        budget = safe_float(self.app.settings.get("monthly_budget"), 0)
        percent = (spent / budget * 100) if budget else 0

        tk.Label(
            budget_card, text=f"{percent:.1f}% used",
            bg=self.colors["surface"], fg=self.colors["purple"],
            font=("Segoe UI", 25, "bold")
        ).pack(anchor="w", padx=18, pady=(9, 3))

        progress = ttk.Progressbar(
            budget_card, maximum=100, value=min(percent, 100),
            style="Horizontal.TProgressbar"
        )
        progress.pack(fill="x", padx=18, pady=12)

        tk.Label(
            budget_card,
            text=f"Spent: {money(spent)}\nBudget: {money(budget)}\nRemaining: {money(budget-spent)}",
            justify="left", bg=self.colors["surface"],
            fg=self.colors["muted"], font=("Segoe UI", 10)
        ).pack(anchor="w", padx=18, pady=(3, 15))

        quick_card = Card(middle)
        quick_card.pack(side="left", fill="both", expand=True, padx=(8, 0))

        tk.Label(
            quick_card, text="Quick actions",
            bg=self.colors["surface"], fg=self.colors["text"],
            font=("Segoe UI", 13, "bold")
        ).pack(anchor="w", padx=18, pady=(18, 10))

        RoundedButton(
            quick_card, "＋  Add a transaction",
            lambda: self.app.show_page("Add Transaction")
        ).pack(fill="x", padx=18, pady=5)

        RoundedButton(
            quick_card, "◉  View analytics",
            lambda: self.app.show_page("Analytics"),
            color=self.colors["surface_alt"],
            text_color=self.colors["text"]
        ).pack(fill="x", padx=18, pady=5)

        RoundedButton(
            quick_card, "⇩  Export my report",
            lambda: self.app.show_page("Reports"),
            color=self.colors["surface_alt"],
            text_color=self.colors["text"]
        ).pack(fill="x", padx=18, pady=5)

        tk.Label(
            quick_card,
            text="Small steps today, better savings tomorrow.",
            bg=self.colors["surface"], fg=self.colors["muted"],
            font=("Segoe UI", 9, "italic")
        ).pack(anchor="w", padx=18, pady=(12, 10))

    def build_recent_table(self):
        card = Card(self)
        card.pack(fill="both", expand=True)

        top = tk.Frame(card, bg=self.colors["surface"])
        top.pack(fill="x", padx=15, pady=(13, 5))

        tk.Label(
            top, text="Recent activity",
            bg=self.colors["surface"], fg=self.colors["text"],
            font=("Segoe UI", 13, "bold")
        ).pack(side="left")

        RoundedButton(
            top, "See all",
            lambda: self.app.show_page("Transactions"),
            compact=True, color=self.colors["surface_alt"],
            text_color=self.colors["text"]
        ).pack(side="right")

        self.table = ttk.Treeview(
            card,
            columns=("date", "category", "type", "amount", "note"),
            show="headings", height=5
        )
        for col, title, width in [
            ("date", "DATE", 110),
            ("category", "CATEGORY", 130),
            ("type", "TYPE", 90),
            ("amount", "AMOUNT", 120),
            ("note", "DESCRIPTION", 250)
        ]:
            self.table.heading(col, text=title)
            self.table.column(col, width=width, anchor="w")
        self.table.pack(fill="both", expand=True, padx=15, pady=(5, 14))

        for item in self.app.recent_transactions(7):
            self.table.insert(
                "", "end",
                values=(
                    item["date"], item["category"], item["type"],
                    money(item["amount"]), item["note"]
                )
            )


# ============================================================
# ADD TRANSACTION PAGE
# ============================================================

class AddTransactionPage(PageBase):

    def __init__(self, app, parent):
        super().__init__(app, parent)
        self.editing_id = None
        self.heading(
            "Add transaction",
            "Record money coming in or going out. Your data is saved to CSV."
        )
        self.build_form()

    def build_form(self):
        wrapper = tk.Frame(self, bg=self.colors["background"])
        wrapper.pack(fill="both", expand=True)

        form = Card(wrapper)
        form.pack(anchor="nw", fill="x", padx=5, pady=5)

        inner = tk.Frame(form, bg=self.colors["surface"])
        inner.pack(fill="x", padx=25, pady=22)

        self.type_var = tk.StringVar(value="Expense")
        self.category_var = tk.StringVar(value=self.app.categories[0])
        self.amount_var = tk.StringVar()
        self.date_var = tk.StringVar(value=today_string())
        self.note_var = tk.StringVar()
        self.payment_var = tk.StringVar(value="UPI")

        self.field_label(inner, "Transaction type")
        type_box = ttk.Combobox(
            inner, textvariable=self.type_var,
            values=TRANSACTION_TYPES, state="readonly"
        )
        type_box.pack(fill="x", ipady=5, pady=(4, 13))
        type_box.bind("<<ComboboxSelected>>", self.update_category_options)

        self.field_label(inner, "Category")
        self.category_box = ttk.Combobox(
            inner, textvariable=self.category_var,
            values=self.app.categories, state="readonly"
        )
        self.category_box.pack(fill="x", ipady=5, pady=(4, 13))

        self.field_label(inner, "Amount (₹)")
        self.form_entry(inner, self.amount_var)

        self.field_label(inner, "Date (YYYY-MM-DD)")
        self.form_entry(inner, self.date_var)

        self.field_label(inner, "Description")
        self.form_entry(inner, self.note_var)

        self.field_label(inner, "Payment method")
        ttk.Combobox(
            inner, textvariable=self.payment_var,
            values=PAYMENT_METHODS, state="readonly"
        ).pack(fill="x", ipady=5, pady=(4, 15))

        buttons = tk.Frame(inner, bg=self.colors["surface"])
        buttons.pack(fill="x", pady=(8, 0))

        RoundedButton(
            buttons, "✓  SAVE TRANSACTION", self.save_form
        ).pack(side="left", padx=(0, 8))

        RoundedButton(
            buttons, "CLEAR FORM", self.clear,
            color=self.colors["surface_alt"],
            text_color=self.colors["text"]
        ).pack(side="left")

        self.status_label = tk.Label(
            inner, text="All fields are stored locally on your computer.",
            bg=self.colors["surface"], fg=self.colors["muted"],
            font=("Segoe UI", 9)
        )
        self.status_label.pack(anchor="w", pady=(15, 0))

    def field_label(self, parent, text):
        tk.Label(
            parent, text=text, bg=self.colors["surface"],
            fg=self.colors["muted"], font=("Segoe UI", 9, "bold")
        ).pack(anchor="w", pady=(5, 0))

    def form_entry(self, parent, variable):
        tk.Entry(
            parent, textvariable=variable,
            bg=self.colors["surface_alt"], fg=self.colors["text"],
            insertbackground=self.colors["text"], relief="flat",
            font=("Segoe UI", 10)
        ).pack(fill="x", ipady=9, pady=(4, 13))

    def update_category_options(self, _event=None):
        self.category_box.configure(values=self.app.categories)
        if self.category_var.get() not in self.app.categories:
            self.category_var.set(self.app.categories[0])

    def clear(self):
        self.type_var.set("Expense")
        self.category_var.set(self.app.categories[0])
        self.amount_var.set("")
        self.date_var.set(today_string())
        self.note_var.set("")
        self.payment_var.set("UPI")
        self.editing_id = None
        self.status_label.config(text="Form cleared.")

    def validate(self):
        try:
            amount = float(self.amount_var.get().strip())
            if amount <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid amount", "Enter an amount greater than zero.")
            return None

        tx_date = self.date_var.get().strip()
        try:
            datetime.strptime(tx_date, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Invalid date", "Date must use YYYY-MM-DD.")
            return None

        if self.category_var.get() not in self.app.categories:
            messagebox.showerror("Category", "Please select a valid category.")
            return None

        return {
            "id": self.editing_id or datetime.now().strftime("%Y%m%d%H%M%S%f"),
            "date": tx_date,
            "category": self.category_var.get(),
            "amount": amount,
            "note": self.note_var.get().strip(),
            "payment": self.payment_var.get(),
            "type": self.type_var.get()
        }

    def save_form(self):
        record = self.validate()
        if record is None:
            return

        if self.editing_id:
            success = self.app.update_record(self.editing_id, record)
            message = "Transaction updated successfully."
        else:
            success = self.app.add_record(record)
            message = "Transaction saved successfully."

        if success:
            self.clear()
            messagebox.showinfo("Saved", message)
            self.app.check_budget_alert()


# ============================================================
# TRANSACTIONS PAGE
# ============================================================

class TransactionsPage(PageBase):

    def __init__(self, app, parent):
        super().__init__(app, parent)
        self.search_var = tk.StringVar()
        self.category_var = tk.StringVar(value="All")
        self.type_var = tk.StringVar(value="All")
        self.heading(
            "All transactions",
            "Search, filter, edit, delete and review every saved record."
        )
        self.build_controls()
        self.build_table()
        self.refresh_table()

    def build_controls(self):
        bar = Card(self)
        bar.pack(fill="x", pady=(0, 12))

        row = tk.Frame(bar, bg=self.colors["surface"])
        row.pack(fill="x", padx=14, pady=13)

        tk.Label(
            row, text="Search", bg=self.colors["surface"],
            fg=self.colors["muted"], font=("Segoe UI", 9, "bold")
        ).pack(side="left")

        search = tk.Entry(
            row, textvariable=self.search_var,
            bg=self.colors["surface_alt"], fg=self.colors["text"],
            insertbackground=self.colors["text"], relief="flat", width=25
        )
        search.pack(side="left", padx=8, ipady=7)
        self.search_var.trace_add("write", lambda *_: self.refresh_table())

        self.category_box = ttk.Combobox(
            row, textvariable=self.category_var,
            values=["All"] + self.app.categories,
            state="readonly", width=17
        )
        self.category_box.pack(side="left", padx=6)
        self.category_box.bind("<<ComboboxSelected>>", lambda _e: self.refresh_table())

        ttk.Combobox(
            row, textvariable=self.type_var,
            values=["All"] + TRANSACTION_TYPES,
            state="readonly", width=12
        ).pack(side="left", padx=6)
        row.winfo_children()[-1].bind(
            "<<ComboboxSelected>>", lambda _e: self.refresh_table()
        )

        RoundedButton(
            row, "RESET FILTERS", self.reset_filters,
            color=self.colors["surface_alt"],
            text_color=self.colors["text"], compact=True
        ).pack(side="right")

    def build_table(self):
        card = Card(self)
        card.pack(fill="both", expand=True)

        columns = ("date", "category", "type", "amount", "payment", "note")
        self.table = ttk.Treeview(card, columns=columns, show="headings")
        specs = [
            ("date", "DATE", 105),
            ("category", "CATEGORY", 125),
            ("type", "TYPE", 85),
            ("amount", "AMOUNT", 120),
            ("payment", "PAYMENT", 115),
            ("note", "DESCRIPTION", 230),
        ]
        for key, label, width in specs:
            self.table.heading(key, text=label)
            self.table.column(key, width=width, anchor="w")

        ybar = ttk.Scrollbar(card, orient="vertical", command=self.table.yview)
        self.table.configure(yscrollcommand=ybar.set)
        self.table.pack(side="left", fill="both", expand=True, padx=(12, 0), pady=12)
        ybar.pack(side="right", fill="y", padx=(0, 12), pady=12)
        self.table.bind("<Double-1>", self.edit_selected)

        actions = tk.Frame(self, bg=self.colors["background"])
        actions.pack(fill="x", pady=12)

        RoundedButton(actions, "＋ ADD NEW", lambda: self.app.show_page("Add Transaction")).pack(side="left", padx=4)
        RoundedButton(actions, "✎ EDIT SELECTED", self.edit_selected).pack(side="left", padx=4)
        RoundedButton(actions, "✕ DELETE SELECTED", self.delete_selected, color=self.colors["red"]).pack(side="left", padx=4)
        RoundedButton(actions, "⇩ EXPORT VIEW", self.export_view, color=self.colors["green"]).pack(side="right", padx=4)

    def reset_filters(self):
        self.search_var.set("")
        self.category_var.set("All")
        self.type_var.set("All")
        self.refresh_table()

    def refresh_table(self):
        if not hasattr(self, "table"):
            return
        for item in self.table.get_children():
            self.table.delete(item)

        query = self.search_var.get().lower().strip()
        category = self.category_var.get()
        tx_type = self.type_var.get()

        for record in sorted(self.app.transactions, key=lambda x: x["date"], reverse=True):
            if category != "All" and record["category"] != category:
                continue
            if tx_type != "All" and record["type"] != tx_type:
                continue
            searchable = " ".join([
                record["date"], record["category"], record["note"],
                record["payment"], record["type"]
            ]).lower()
            if query and query not in searchable:
                continue
            self.table.insert(
                "", "end", iid=record["id"],
                values=(
                    record["date"], record["category"], record["type"],
                    money(record["amount"]), record["payment"], record["note"]
                )
            )

    def selected_id(self):
        selection = self.table.selection()
        return selection[0] if selection else None

    def edit_selected(self, _event=None):
        identifier = self.selected_id()
        if not identifier:
            messagebox.showwarning("Select row", "Select a transaction first.")
            return
        index = self.app.find_index(identifier)
        if index is None:
            return
        record = self.app.transactions[index]
        page = AddTransactionPage(self.app, self.app.content)
        page.pack(fill="both", expand=True)
        for child in self.app.content.winfo_children():
            if child is not page:
                child.destroy()
        page.type_var.set(record["type"])
        page.category_var.set(record["category"])
        page.amount_var.set(str(record["amount"]))
        page.date_var.set(record["date"])
        page.note_var.set(record["note"])
        page.payment_var.set(record["payment"])
        page.editing_id = identifier
        page.status_label.config(text="Editing selected transaction. Save to apply changes.")
        self.app.current_page = "Add Transaction"
        self.app.breadcrumb.config(text="Edit Transaction")

    def delete_selected(self):
        identifier = self.selected_id()
        if not identifier:
            messagebox.showwarning("Select row", "Select a transaction first.")
            return
        if not messagebox.askyesno("Confirm delete", "Permanently delete this transaction?"):
            return
        if self.app.delete_record(identifier):
            messagebox.showinfo("Deleted", "Transaction deleted.")
            self.app.show_page("Transactions")

    def export_view(self):
        ids = set(self.table.get_children())
        records = [x for x in self.app.transactions if x["id"] in ids]
        self.app.export_records(records, "filtered_transactions.csv")


# ============================================================
# ANALYTICS PAGE
# ============================================================

class AnalyticsPage(PageBase):

    def __init__(self, app, parent):
        super().__init__(app, parent)
        self.heading(
            "Spending analytics",
            "Understand where your money goes with category-wise visual reports."
        )
        self.build_metrics()
        self.build_charts()

    def build_metrics(self):
        row = tk.Frame(self, bg=self.colors["background"])
        row.pack(fill="x", pady=(0, 15))
        self.metric(row, "TOTAL EXPENSES", money(self.app.total_expenses()), self.colors["pink"])
        self.metric(row, "TOTAL INCOME", money(self.app.total_income()), self.colors["green"])
        self.metric(row, "NET BALANCE", money(self.app.balance()), self.colors["cyan"])

    def metric(self, parent, title, value, accent):
        card = Card(parent, accent)
        card.pack(side="left", fill="both", expand=True, padx=5, ipady=8)
        tk.Label(card, text=title, bg=self.colors["surface"], fg=self.colors["muted"],
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=14, pady=(10, 4))
        tk.Label(card, text=value, bg=self.colors["surface"], fg=accent,
                 font=("Segoe UI", 17, "bold")).pack(anchor="w", padx=14, pady=(0, 10))

    def build_charts(self):
        if not MATPLOTLIB_AVAILABLE:
            card = Card(self)
            card.pack(fill="both", expand=True)
            tk.Label(
                card, text="Install matplotlib to display charts:\npip install matplotlib",
                bg=self.colors["surface"], fg=self.colors["text"],
                font=("Segoe UI", 13, "bold")
            ).pack(expand=True)
            return

        chart_area = tk.Frame(self, bg=self.colors["background"])
        chart_area.pack(fill="both", expand=True)

        left = Card(chart_area)
        left.pack(side="left", fill="both", expand=True, padx=(0, 7))
        right = Card(chart_area)
        right.pack(side="left", fill="both", expand=True, padx=(7, 0))

        self.draw_pie(left)
        self.draw_bar(right)

    def draw_pie(self, parent):
        summary = self.app.category_totals("Expense")
        if not summary:
            tk.Label(
                parent, text="No expense data yet.",
                bg=self.colors["surface"], fg=self.colors["muted"]
            ).pack(expand=True)
            return

        fig, ax = plt.subplots(figsize=(5, 4), facecolor=self.colors["surface"])
        ax.set_facecolor(self.colors["surface"])
        ax.pie(
            list(summary.values()),
            labels=list(summary.keys()),
            autopct="%1.1f%%",
            startangle=130,
            textprops={"color": self.colors["text"], "fontsize": 8}
        )
        ax.set_title("Expense share", color=self.colors["text"], fontsize=12)
        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)

    def draw_bar(self, parent):
        summary = self.app.category_totals("Expense")
        if not summary:
            tk.Label(
                parent, text="Add expenses to view category comparison.",
                bg=self.colors["surface"], fg=self.colors["muted"]
            ).pack(expand=True)
            return

        fig, ax = plt.subplots(figsize=(5, 4), facecolor=self.colors["surface"])
        ax.set_facecolor(self.colors["surface"])
        bars = ax.bar(
            list(summary.keys()), list(summary.values()),
            color=[self.colors["purple"], self.colors["pink"],
                   self.colors["cyan"], self.colors["green"],
                   self.colors["yellow"], self.colors["blue"]]
        )
        ax.set_title("Category comparison", color=self.colors["text"], fontsize=12)
        ax.tick_params(axis="x", labelrotation=25, labelcolor=self.colors["text"])
        ax.tick_params(axis="y", labelcolor=self.colors["text"])
        for spine in ax.spines.values():
            spine.set_color(self.colors["border"])
        ax.bar_label(bars, fmt="%.0f", fontsize=8)
        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)


# ============================================================
# BUDGET PLANNER PAGE
# ============================================================

class BudgetPlannerPage(PageBase):

    def __init__(self, app, parent):
        super().__init__(app, parent)
        self.heading(
            "Budget planner",
            "Set a monthly spending limit and monitor your progress."
        )
        self.build_budget_form()
        self.build_category_budget()

    def build_budget_form(self):
        card = Card(self)
        card.pack(fill="x", pady=(0, 15))

        inner = tk.Frame(card, bg=self.colors["surface"])
        inner.pack(fill="x", padx=20, pady=20)

        tk.Label(
            inner, text="Your monthly budget",
            bg=self.colors["surface"], fg=self.colors["text"],
            font=("Segoe UI", 13, "bold")
        ).pack(anchor="w")

        self.budget_var = tk.StringVar(
            value=str(self.app.settings.get("monthly_budget", 2000))
        )
        entry = tk.Entry(
            inner, textvariable=self.budget_var,
            bg=self.colors["surface_alt"], fg=self.colors["text"],
            insertbackground=self.colors["text"], relief="flat",
            font=("Segoe UI", 12), width=22
        )
        entry.pack(anchor="w", ipady=9, pady=10)

        RoundedButton(inner, "SAVE MONTHLY BUDGET", self.save_budget).pack(anchor="w")

        spent = self.app.month_expenses()
        limit = safe_float(self.app.settings.get("monthly_budget"), 0)
        remaining = limit - spent
        percent = spent / limit * 100 if limit else 0

        tk.Label(
            inner, text=f"Spent this month: {money(spent)}",
            bg=self.colors["surface"], fg=self.colors["pink"],
            font=("Segoe UI", 11, "bold")
        ).pack(anchor="w", pady=(17, 4))

        tk.Label(
            inner, text=f"Remaining: {money(remaining)}  •  Used: {percent:.1f}%",
            bg=self.colors["surface"], fg=self.colors["muted"],
            font=("Segoe UI", 10)
        ).pack(anchor="w")

        bar = ttk.Progressbar(inner, maximum=100, value=min(percent, 100))
        bar.pack(fill="x", pady=12)

        if remaining < 0:
            tk.Label(
                inner, text="You are over your monthly budget.",
                bg=self.colors["surface"], fg=self.colors["red"],
                font=("Segoe UI", 10, "bold")
            ).pack(anchor="w")

    def save_budget(self):
        amount = safe_float(self.budget_var.get(), -1)
        if amount <= 0:
            messagebox.showerror("Invalid budget", "Enter a positive budget amount.")
            return
        self.app.settings["monthly_budget"] = amount
        if self.app.save_settings():
            messagebox.showinfo("Budget saved", "Your monthly budget has been saved.")
            self.app.refresh_everything()

    def build_category_budget(self):
        card = Card(self)
        card.pack(fill="both", expand=True)
        tk.Label(
            card, text="Where your expenses are going",
            bg=self.colors["surface"], fg=self.colors["text"],
            font=("Segoe UI", 13, "bold")
        ).pack(anchor="w", padx=18, pady=(16, 8))

        summary = self.app.category_totals("Expense", datetime.now().strftime("%Y-%m"))
        if not summary:
            tk.Label(
                card, text="No expenses recorded for this month yet.",
                bg=self.colors["surface"], fg=self.colors["muted"]
            ).pack(anchor="w", padx=18, pady=10)
            return

        max_value = max(summary.values())
        for category, amount in sorted(summary.items(), key=lambda x: x[1], reverse=True):
            row = tk.Frame(card, bg=self.colors["surface"])
            row.pack(fill="x", padx=18, pady=7)

            tk.Label(
                row, text=category, width=18, anchor="w",
                bg=self.colors["surface"], fg=self.colors["text"],
                font=("Segoe UI", 9, "bold")
            ).pack(side="left")

            bar = ttk.Progressbar(
                row, maximum=max_value, value=amount
            )
            bar.pack(side="left", fill="x", expand=True, padx=10)

            tk.Label(
                row, text=money(amount), width=14, anchor="e",
                bg=self.colors["surface"], fg=self.colors["muted"],
                font=("Segoe UI", 9)
            ).pack(side="right")


# ============================================================
# REPORTS PAGE
# ============================================================

class ReportsPage(PageBase):

    def __init__(self, app, parent):
        super().__init__(app, parent)
        self.heading(
            "Reports & exports",
            "Create a portable copy of your financial records."
        )
        self.build_report_options()
        self.build_report_summary()

    def build_report_options(self):
        card = Card(self)
        card.pack(fill="x", pady=(0, 15))
        inner = tk.Frame(card, bg=self.colors["surface"])
        inner.pack(fill="x", padx=20, pady=20)

        tk.Label(
            inner, text="Export your records",
            bg=self.colors["surface"], fg=self.colors["text"],
            font=("Segoe UI", 14, "bold")
        ).pack(anchor="w", pady=(0, 5))

        tk.Label(
            inner,
            text="Download all transactions as a CSV file. You can open it in Excel.",
            bg=self.colors["surface"], fg=self.colors["muted"],
            font=("Segoe UI", 9)
        ).pack(anchor="w", pady=(0, 14))

        RoundedButton(
            inner, "⇩  EXPORT ALL TRANSACTIONS",
            lambda: self.app.export_records(
                self.app.transactions, "all_budget_transactions.csv"
            )
        ).pack(anchor="w")

    def build_report_summary(self):
        card = Card(self)
        card.pack(fill="x")

        tk.Label(
            card, text="Financial summary",
            bg=self.colors["surface"], fg=self.colors["text"],
            font=("Segoe UI", 14, "bold")
        ).pack(anchor="w", padx=20, pady=(18, 12))

        values = [
            ("All-time income", money(self.app.total_income())),
            ("All-time expenses", money(self.app.total_expenses())),
            ("Net balance", money(self.app.balance())),
            ("This month's expenses", money(self.app.month_expenses())),
            ("Total transactions", str(len(self.app.transactions))),
        ]

        for label, value in values:
            row = tk.Frame(card, bg=self.colors["surface"])
            row.pack(fill="x", padx=20, pady=8)
            tk.Label(
                row, text=label, bg=self.colors["surface"],
                fg=self.colors["muted"], font=("Segoe UI", 10)
            ).pack(side="left")
            tk.Label(
                row, text=value, bg=self.colors["surface"],
                fg=self.colors["text"], font=("Segoe UI", 10, "bold")
            ).pack(side="right")


# ============================================================
# SETTINGS PAGE
# ============================================================

class SettingsPage(PageBase):

    def __init__(self, app, parent):
        super().__init__(app, parent)
        self.heading(
            "Application settings",
            "Manage your preferences and your locally stored data."
        )
        self.build_preferences()
        self.build_category_manager()
        self.build_data_tools()

    def build_preferences(self):
        card = Card(self)
        card.pack(fill="x", pady=(0, 14))
        inner = tk.Frame(card, bg=self.colors["surface"])
        inner.pack(fill="x", padx=18, pady=18)

        tk.Label(
            inner, text="Preferences",
            bg=self.colors["surface"], fg=self.colors["text"],
            font=("Segoe UI", 13, "bold")
        ).pack(anchor="w", pady=(0, 12))

        self.alert_var = tk.BooleanVar(
            value=self.app.settings.get("budget_alert", True)
        )
        tk.Checkbutton(
            inner, text="Show a warning when monthly budget is exceeded",
            variable=self.alert_var,
            bg=self.colors["surface"], fg=self.colors["text"],
            selectcolor=self.colors["surface_alt"],
            activebackground=self.colors["surface"],
            activeforeground=self.colors["text"],
            font=("Segoe UI", 10)
        ).pack(anchor="w", pady=5)

        RoundedButton(inner, "SAVE PREFERENCES", self.save_preferences).pack(anchor="w", pady=8)

    def save_preferences(self):
        self.app.settings["budget_alert"] = self.alert_var.get()
        if self.app.save_settings():
            messagebox.showinfo("Settings", "Preferences saved.")

    def build_category_manager(self):
        card = Card(self)
        card.pack(fill="x", pady=(0, 14))
        inner = tk.Frame(card, bg=self.colors["surface"])
        inner.pack(fill="x", padx=18, pady=18)

        tk.Label(
            inner, text="Custom categories",
            bg=self.colors["surface"], fg=self.colors["text"],
            font=("Segoe UI", 13, "bold")
        ).pack(anchor="w", pady=(0, 8))

        self.category_list = tk.Listbox(
            inner, height=5, bg=self.colors["surface_alt"],
            fg=self.colors["text"], relief="flat",
            selectbackground=self.colors["purple"],
            font=("Segoe UI", 10)
        )
        self.category_list.pack(side="left", fill="x", expand=True, padx=(0, 12))
        self.refresh_category_list()

        controls = tk.Frame(inner, bg=self.colors["surface"])
        controls.pack(side="left", fill="y")

        self.new_category_var = tk.StringVar()
        tk.Entry(
            controls, textvariable=self.new_category_var,
            bg=self.colors["surface_alt"], fg=self.colors["text"],
            insertbackground=self.colors["text"], relief="flat"
        ).pack(fill="x", ipady=7, pady=(0, 8))

        RoundedButton(controls, "＋ ADD", self.add_category, compact=True).pack(fill="x", pady=3)
        RoundedButton(
            controls, "REMOVE", self.remove_category,
            color=self.colors["red"], compact=True
        ).pack(fill="x", pady=3)

    def refresh_category_list(self):
        self.category_list.delete(0, tk.END)
        for category in self.app.categories:
            self.category_list.insert(tk.END, category)

    def add_category(self):
        name = self.new_category_var.get().strip()
        if not name:
            messagebox.showwarning("Category", "Type a category name.")
            return
        if name.lower() in [x.lower() for x in self.app.categories]:
            messagebox.showwarning("Category", "This category already exists.")
            return
        self.app.categories.append(name)
        self.app.save_categories()
        self.new_category_var.set("")
        self.refresh_category_list()
        messagebox.showinfo("Category", f"{name} added.")

    def remove_category(self):
        selection = self.category_list.curselection()
        if not selection:
            messagebox.showwarning("Category", "Select a category to remove.")
            return
        name = self.app.categories[selection[0]]
        used = any(x["category"] == name for x in self.app.transactions)
        if used:
            messagebox.showwarning(
                "Category in use",
                "This category is used by saved transactions, so it cannot be removed."
            )
            return
        if messagebox.askyesno("Remove category", f"Remove {name}?"):
            self.app.categories.remove(name)
            self.app.save_categories()
            self.refresh_category_list()

    def build_data_tools(self):
        card = Card(self)
        card.pack(fill="x")
        inner = tk.Frame(card, bg=self.colors["surface"])
        inner.pack(fill="x", padx=18, pady=18)

        tk.Label(
            inner, text="Local data files",
            bg=self.colors["surface"], fg=self.colors["text"],
            font=("Segoe UI", 13, "bold")
        ).pack(anchor="w")

        tk.Label(
            inner,
            text=f"Transactions: {DATA_FILE.name}\nPreferences: {SETTINGS_FILE.name}\nCategories: {CATEGORY_FILE.name}",
            justify="left", bg=self.colors["surface"],
            fg=self.colors["muted"], font=("Segoe UI", 9)
        ).pack(anchor="w", pady=8)

        RoundedButton(
            inner, "EXPORT BACKUP CSV",
            lambda: self.app.export_records(
                self.app.transactions, "budget_backup.csv"
            ), color=self.colors["green"]
        ).pack(anchor="w", pady=4)

        RoundedButton(
            inner, "RESET ALL TRANSACTIONS",
            self.reset_transactions, color=self.colors["red"]
        ).pack(anchor="w", pady=4)

    def reset_transactions(self):
        if not self.app.transactions:
            messagebox.showinfo("Reset", "There are no transactions to clear.")
            return
        confirm = messagebox.askyesno(
            "Danger zone",
            "This permanently removes all transactions from expenses.csv.\n"
            "Your budget settings and categories will remain.\n\nContinue?"
        )
        if not confirm:
            return
        old = self.app.transactions.copy()
        self.app.transactions.clear()
        if not self.app.save_transactions():
            self.app.transactions = old
            return
        messagebox.showinfo("Reset", "All transactions have been removed.")
        self.app.refresh_everything()


# ============================================================
# ABOUT PAGE
# ============================================================

class AboutPage(PageBase):

    def __init__(self, app, parent):
        super().__init__(app, parent)
        self.heading(
            "About this project",
            "A desktop application for recording and understanding personal spending."
        )
        self.build_about_cards()

    def build_about_cards(self):
        intro = Card(self)
        intro.pack(fill="x", pady=(0, 14))

        tk.Label(
            intro, text="✦  NOVA SMART BUDGET MANAGER",
            bg=self.colors["surface"], fg=self.colors["purple"],
            font=("Segoe UI", 18, "bold")
        ).pack(anchor="w", padx=22, pady=(22, 8))

        tk.Label(
            intro,
            text=(
                "This project helps users record income and expenses, "
                "organise transactions into categories, monitor a monthly "
                "budget and understand spending patterns through charts."
            ),
            wraplength=850, justify="left",
            bg=self.colors["surface"], fg=self.colors["muted"],
            font=("Segoe UI", 11)
        ).pack(anchor="w", padx=22, pady=(0, 22))

        features = Card(self)
        features.pack(fill="x", pady=(0, 14))

        tk.Label(
            features, text="Key features",
            bg=self.colors["surface"], fg=self.colors["text"],
            font=("Segoe UI", 14, "bold")
        ).pack(anchor="w", padx=22, pady=(18, 8))

        feature_text = [
            "• Add, edit and delete income or expense records",
            "• Permanent local CSV storage",
            "• Search and filter transaction history",
            "• Monthly budget planner and alerts",
            "• Category-wise pie and bar charts",
            "• CSV export for spreadsheet applications",
            "• Custom categories and saved preferences",
        ]
        for item in feature_text:
            tk.Label(
                features, text=item, bg=self.colors["surface"],
                fg=self.colors["muted"], font=("Segoe UI", 10)
            ).pack(anchor="w", padx=24, pady=3)

        tk.Label(
            features, text="",
            bg=self.colors["surface"]
        ).pack(pady=5)

        tech = Card(self)
        tech.pack(fill="x")

        tk.Label(
            tech, text="Technology used",
            bg=self.colors["surface"], fg=self.colors["text"],
            font=("Segoe UI", 14, "bold")
        ).pack(anchor="w", padx=22, pady=(18, 8))

        tk.Label(
            tech, text="Python  •  Tkinter  •  CSV  •  JSON  •  Matplotlib",
            bg=self.colors["surface"], fg=self.colors["cyan"],
            font=("Segoe UI", 11, "bold")
        ).pack(anchor="w", padx=22, pady=(0, 20))


# ============================================================
# START APPLICATION
# ============================================================

if __name__ == "__main__":
    application = SmartBudgetApp()
    application.mainloop()