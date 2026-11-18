"""Thermodynamic tables GUI (SI and English units).

Copyright (c) 2026 Suemon Kwok
Released under the MIT licence (edit or replace as you prefer).

Property values are NOT copied from any textbook. They are computed live by
the open-source CoolProp library (MIT licence, www.coolprop.org). Please cite:
  I. H. Bell, J. Wronski, S. Quoilin, V. Lemort, "Pure and Pseudo-pure Fluid
  Thermophysical Property Evaluation and the Open-Source Thermophysical
  Property Library CoolProp", Ind. Eng. Chem. Res. 53 (2014) 2498-2508.

Open-source property engine: CoolProp.   Install:  pip install CoolProp
Run:  python thermo_tables_gui.py

How the program is organised:
  1. Unit conversion class (Conv)       - SI <-> English conversions
  2. Table builder functions            - one function per kind of table
  3. TABLES dictionary                  - menu text, table kind, default inputs
  4. Tooltip class                      - hover help text for the input boxes
  5. App class                          - the Tkinter window itself
"""
import csv
import math
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import CoolProp.CoolProp as CP

# CoolProp's default R-134a reference state is IIR (h = 200 kJ/kg at 0 C).
# The Cengel tables use ASHRAE (h = 0 and s = 0 for saturated liquid at -40 C),
# so switch to ASHRAE to make the numbers match the textbook.
try:
    CP.set_reference_state("R134a", "ASHRAE")
except Exception:
    pass

# ---------------------------------------------------------------------------
# Constants used for English-unit conversions
# ---------------------------------------------------------------------------
BTU = 2326.0        # 1 Btu/lbm   = 2326 J/kg
BTUS = 4186.8       # 1 Btu/lbm.R = 4186.8 J/kg.K
FT3 = 0.06242796    # 1 ft3/lbm   = 0.06242796 m3/kg
PSI = 6894.757      # 1 psi       = 6894.757 Pa
RU = 8314.462618    # universal gas constant, J/kmol.K


class Conv:
    """Converts between the units the user sees and the SI units CoolProp uses.

    Input methods  (T, P)       : user units -> CoolProp units (K, Pa)
    Output methods (To, Po, ...): CoolProp units -> user units
    CoolProp always works in K, Pa, J/kg, J/kg.K, m3/kg.
    """

    def __init__(self, units):
        self.si = units == "SI"
        # Unit labels used in column headers
        self.Tu, self.Pu = ("C", "kPa") if self.si else ("F", "psia")
        self.vu = "m3/kg" if self.si else "ft3/lbm"
        self.eu = "kJ/kg" if self.si else "Btu/lbm"
        self.su = "kJ/kg.K" if self.si else "Btu/lbm.R"

    def T(self, x):    # C or F -> K
        return x + 273.15 if self.si else (x - 32) / 1.8 + 273.15

    def To(self, K):   # K -> C or F
        return K - 273.15 if self.si else (K - 273.15) * 1.8 + 32

    def P(self, x):    # kPa or psia -> Pa
        return x * 1000 if self.si else x * PSI

    def Po(self, Pa):  # Pa -> kPa or psia
        return Pa / 1000 if self.si else Pa / PSI

    def v(self, v):    # m3/kg -> m3/kg or ft3/lbm
        return v if self.si else v / FT3

    def e(self, J):    # J/kg -> kJ/kg or Btu/lbm (u and h)
        return J / 1000 if self.si else J / BTU

    def s(self, J):    # J/kg.K -> kJ/kg.K or Btu/lbm.R (s, cp, cv)
        return J / 1000 if self.si else J / BTUS

    def rho(self, r):  # kg/m3 -> kg/m3 or lbm/ft3
        return r if self.si else r * FT3


def frange(a, b, s):
    """Return [a, a+s, a+2s, ... <= b]. Capped at 2000 rows to avoid freezing."""
    out, x = [], a
    while x <= b + 1e-9 and len(out) < 2000:
        out.append(x)
        x += s
    return out


def pp(f, o1, v1, o2, v2, keys):
    """Shortcut: look up several CoolProp properties at one state.

    f = fluid name, (o1, v1) and (o2, v2) = the two independent properties
    that fix the state, keys = string of property letters, e.g. "DUHS"
    (D = density, U = internal energy, H = enthalpy, S = entropy).
    """
    return [CP.PropsSI(k, o1, v1, o2, v2, f) for k in keys]


# ---------------------------------------------------------------------------
# Table builders. Each returns (list_of_column_headers, list_of_rows).
# ---------------------------------------------------------------------------
def sat_table(f, c, vals, byT):
    """Saturated liquid/vapor table (A-4, A-5, A-11, A-12).

    byT = True : the user's range is temperature, pressure is looked up.
    byT = False: the user's range is pressure, temperature is looked up.
    Columns: v, u, h, s for saturated liquid (f), evaporation (fg) and vapor (g).
    """
    h = ["T(" + c.Tu + ")", "Psat(" + c.Pu + ")", "v_f", "v_g", "u_f", "u_fg",
         "u_g", "h_f", "h_fg", "h_g", "s_f", "s_fg", "s_g"]
    if not byT:  # swap the first two headers for the pressure-based table
        h[0], h[1] = "P(" + c.Pu + ")", "Tsat(" + c.Tu + ")"
    rows = []
    for x in vals:
        try:
            if byT:
                T = c.T(x)
                P = CP.PropsSI("P", "T", T, "Q", 0, f)
            else:
                P = c.P(x)
                T = CP.PropsSI("T", "P", P, "Q", 0, f)
            # Q = 0 is saturated liquid, Q = 1 is saturated vapor
            l = pp(f, "T", T, "Q", 0, "DUHS")
            g = pp(f, "T", T, "Q", 1, "DUHS")
            first = (c.To(T), c.Po(P)) if byT else (c.Po(P), c.To(T))
            rows.append(list(first) + [
                c.v(1 / l[0]), c.v(1 / g[0]),               # v_f, v_g
                c.e(l[1]), c.e(g[1] - l[1]), c.e(g[1]),     # u_f, u_fg, u_g
                c.e(l[2]), c.e(g[2] - l[2]), c.e(g[2]),     # h_f, h_fg, h_g
                c.s(l[3]), c.s(g[3] - l[3]), c.s(g[3])])    # s_f, s_fg, s_g
        except Exception:
            continue  # skip rows outside the valid range (e.g. above critical point)
    return h, rows


def superheated(f, c, P, vals):
    """Superheated vapor table (A-6, A-13) at one fixed pressure P."""
    h = ["T(" + c.Tu + ") [first row = sat. vapor]", "v(" + c.vu + ")",
         "u(" + c.eu + ")", "h(" + c.eu + ")", "s(" + c.su + ")"]
    Pa = c.P(P)
    Ts = CP.PropsSI("T", "P", Pa, "Q", 1, f)  # saturation temperature at P
    g = pp(f, "T", Ts, "Q", 1, "DUHS")
    # First row is the saturated vapor state, like the "Sat." row in the book
    rows = [[c.To(Ts), c.v(1 / g[0]), c.e(g[1]), c.e(g[2]), c.s(g[3])]]
    for x in vals:
        T = c.T(x)
        if T <= Ts + 1e-6:
            continue  # at or below Tsat the fluid is not superheated
        try:
            d = pp(f, "T", T, "P", Pa, "DUHS")
            rows.append([x, c.v(1 / d[0]), c.e(d[1]), c.e(d[2]), c.s(d[3])])
        except Exception:
            continue
    return h, rows


def compressed(f, c, P, vals):
    """Compressed (subcooled) liquid table (A-7) at one fixed pressure P."""
    h = ["T(" + c.Tu + ")", "v(" + c.vu + ")", "u(" + c.eu + ")",
         "h(" + c.eu + ")", "s(" + c.su + ")"]
    Pa = c.P(P)
    Ts = CP.PropsSI("T", "P", Pa, "Q", 0, f)
    rows = []
    for x in vals:
        T = c.T(x)
        if T >= Ts:
            continue  # at or above Tsat the fluid is not a compressed liquid
        try:
            d = pp(f, "T", T, "P", Pa, "DUHS")
            rows.append([x, c.v(1 / d[0]), c.e(d[1]), c.e(d[2]), c.s(d[3])])
        except Exception:
            continue
    return h, rows


def ideal_gas(f, c, vals):
    """Ideal-gas properties vs temperature (A-2, A-17 to A-23).

    A very low pressure (100 Pa) is used so the real-gas behaviour is
    essentially ideal. s0 is the entropy at 1 atm, found by correcting the
    entropy at 100 Pa:  s0 = s(T, P) + R ln(P / 101325).
    Values are per kg and use CoolProp's reference state, so absolute h and s0
    differ from the book, but differences between states agree.
    """
    Tu = "K" if c.si else "R"
    h = ["T(" + Tu + ")", "h(" + c.eu + ")", "u(" + c.eu + ")",
         "s0(" + c.su + ")", "cp", "cv", "k"]
    M = CP.PropsSI("molar_mass", f)   # kg/mol
    R = 8.314462618 / M               # gas constant, J/kg.K
    P0 = 100.0                        # Pa
    rows = []
    for x in vals:
        T = x if c.si else x / 1.8    # R -> K for English units
        try:
            d = pp(f, "T", T, "P", P0, "HUS")
            cp = CP.PropsSI("CP0MASS", "T", T, "P", P0, f)  # ideal-gas cp
            s0 = d[2] + R * math.log(P0 / 101325.0)
            # cv = cp - R for an ideal gas, k = cp / cv
            rows.append([x, c.e(d[0]), c.e(d[1]), c.s(s0), c.s(cp),
                         c.s(cp - R), cp / (cp - R)])
        except Exception:
            continue
    return h, rows


# Substances listed in Table A-1 and in the Gas dropdown
FLUIDS = ["Water", "Air", "Nitrogen", "Oxygen", "CarbonDioxide",
          "CarbonMonoxide", "Hydrogen", "Methane", "Ethane", "Propane",
          "n-Butane", "Ammonia", "R134a", "Argon", "Helium", "Neon",
          "Ethylene", "Xenon"]


def a1(c):
    """Table A-1: molar mass, gas constant and critical-point properties."""
    h = ["Substance", "M(" + ("kg/kmol" if c.si else "lbm/lbmol") + ")",
         "R(" + c.su + ")", "Tcr(" + ("K" if c.si else "R") + ")",
         "Pcr(" + ("MPa" if c.si else "psia") + ")",
         "Vcr(" + ("m3/kmol" if c.si else "ft3/lbmol") + ")"]
    rows = []
    for f in FLUIDS:
        try:
            M = CP.PropsSI("molar_mass", f) * 1000          # kg/kmol
            Tc = CP.PropsSI("Tcrit", f)                     # K
            Pc = CP.PropsSI("pcrit", f)                     # Pa
            Vc = M / CP.PropsSI("rhomass_critical", f)      # m3/kmol
            if c.si:
                rows.append([f, M, RU / M / 1000, Tc, Pc / 1e6, Vc])
            else:
                rows.append([f, M, RU / M / BTUS, Tc * 1.8, Pc / PSI, Vc * FT3])
        except Exception:
            continue
    return h, rows


def atmosphere(c, vals):
    """Standard atmosphere (A-16) from simple layer equations (up to 32 km)."""
    h = ["Alt(" + ("m" if c.si else "ft") + ")", "T(" + c.Tu + ")",
         "P(" + c.Pu + ")", "g(" + ("m/s2" if c.si else "ft/s2") + ")",
         "c(" + ("m/s" if c.si else "ft/s") + ")",
         "rho(" + ("kg/m3" if c.si else "lbm/ft3") + ")"]
    rows = []
    for x in vals:
        z = x if c.si else x * 0.3048          # altitude in metres
        if z <= 11000:                          # troposphere: T falls linearly
            T = 288.15 - 0.0065 * z
            P = 101325 * (T / 288.15) ** 5.25588
        elif z <= 20000:                        # lower stratosphere: isothermal
            T = 216.65
            P = 22632.06 * math.exp(-9.80665 * (z - 11000) / (287.053 * T))
        else:                                   # upper stratosphere: T rises
            T = 216.65 + 0.001 * (z - 20000)
            P = 5474.889 * (T / 216.65) ** (-34.1632)
        g = 9.807 - 3.32e-6 * z                 # gravity falls slightly with height
        cs = math.sqrt(1.4 * 287.053 * T)       # speed of sound
        rho = P / (287.053 * T)                 # ideal-gas density
        rows.append([x, c.To(T), c.Po(P), g if c.si else g / 0.3048,
                     cs if c.si else cs / 0.3048, c.rho(rho)])
    return h, rows


K = 1.4  # specific heat ratio used by the compressible-flow tables


def isentropic(vals):
    """Table A-32: isentropic flow functions for an ideal gas, k = 1.4."""
    h = ["Ma", "T/T0", "P/P0", "rho/rho0", "A/A*"]
    rows = []
    for M in vals:
        if M <= 0:
            continue
        t = 1 / (1 + (K - 1) / 2 * M * M)       # T/T0
        a = (1 / M) * ((2 / (K + 1)) * (1 + (K - 1) / 2 * M * M)) ** ((K + 1) / (2 * (K - 1)))
        rows.append([M, t, t ** (K / (K - 1)), t ** (1 / (K - 1)), a])
    return h, rows


def shock(vals):
    """Table A-33: normal-shock functions for an ideal gas, k = 1.4."""
    h = ["Ma1", "Ma2", "P2/P1", "rho2/rho1", "T2/T1", "P02/P01", "P02/P1"]
    rows = []
    for M in vals:
        if M < 1:
            continue  # a normal shock needs supersonic upstream flow
        m2 = math.sqrt((M * M + 2 / (K - 1)) / (2 * K / (K - 1) * M * M - 1))
        p = 1 + 2 * K / (K + 1) * (M * M - 1)                  # P2/P1
        r = (K + 1) * M * M / ((K - 1) * M * M + 2)            # rho2/rho1
        p0 = r ** (K / (K - 1)) * (1 / p) ** (1 / (K - 1))     # P02/P01
        p01 = (1 + (K - 1) / 2 * M * M) ** (K / (K - 1))       # P01/P1
        rows.append([M, m2, p, r, p / r, p0, p0 * p01])
    return h, rows


def rayleigh(vals):
    """Table A-34: Rayleigh flow (frictionless flow with heat transfer), k = 1.4."""
    h = ["Ma", "T0/T0*", "P/P*", "T/T*", "rho/rho*", "V/V*", "P0/P0*"]
    rows = []
    for M in vals:
        if M <= 0:
            continue
        d = 1 + K * M * M
        rows.append([M,
                     (K + 1) * M * M * (2 + (K - 1) * M * M) / d ** 2,
                     (K + 1) / d,
                     (M * (K + 1) / d) ** 2,
                     d / ((K + 1) * M * M),
                     (K + 1) * M * M / d,
                     (K + 1) / d * ((2 + (K - 1) * M * M) / (K + 1)) ** (K / (K - 1))])
    return h, rows


# ---------------------------------------------------------------------------
# Menu definition.
# name -> (kind, fixed fluid, SI defaults, English defaults)
# Defaults are (start, stop, step, fixed P). They fill the input boxes
# whenever the table or the unit system changes.
# ---------------------------------------------------------------------------
TABLES = {
    "A-1/1E  Molar mass, R, critical point": ("a1", None, (0, 0, 1, 0), (0, 0, 1, 0)),
    "A-2/2E, 17-23  Ideal-gas props (pick gas)": ("ideal", "Air", (200, 1000, 50, 0), (400, 1800, 100, 0)),
    "A-4/4E  Sat. water - temperature": ("satT", "Water", (0.01, 370, 10, 0), (32.02, 700, 20, 0)),
    "A-5/5E  Sat. water - pressure": ("satP", "Water", (10, 3000, 200, 0), (1, 500, 25, 0)),
    "A-6/6E  Superheated water": ("sh", "Water", (100, 700, 50, 100), (212, 1200, 100, 14.7)),
    "A-7/7E  Compressed liquid water": ("cl", "Water", (0, 300, 20, 5000), (32, 500, 40, 1000)),
    "A-11/11E  Sat. R-134a - temperature": ("satT", "R134a", (-40, 100, 10, 0), (-40, 200, 20, 0)),
    "A-12/12E  Sat. R-134a - pressure": ("satP", "R134a", (60, 1600, 100, 0), (10, 200, 10, 0)),
    "A-13/13E  Superheated R-134a": ("sh", "R134a", (-20, 100, 10, 400), (0, 200, 20, 60)),
    "A-16/16E  Atmosphere at high altitude": ("atm", None, (0, 30000, 1000, 0), (0, 100000, 5000, 0)),
    "A-32  Isentropic flow, k=1.4": ("isen", None, (0.1, 3, 0.1, 0), (0.1, 3, 0.1, 0)),
    "A-33  Normal shock, k=1.4": ("shock", None, (1, 3, 0.1, 0), (1, 3, 0.1, 0)),
    "A-34  Rayleigh flow, k=1.4": ("ray", None, (0.1, 3, 0.1, 0), (0.1, 3, 0.1, 0)),
}


def build(name, units, fluid, a, b, s, P):
    """Pick the right builder for the selected table and run it."""
    kind, fl, _, _ = TABLES[name]
    c = Conv(units)
    v = frange(a, b, s)  # the list of values for the first column
    if kind == "a1":
        return a1(c)
    if kind == "ideal":
        return ideal_gas(fluid, c, v)   # uses the Gas dropdown
    if kind == "satT":
        return sat_table(fl, c, v, True)
    if kind == "satP":
        return sat_table(fl, c, v, False)
    if kind == "sh":
        return superheated(fl, c, P, v)
    if kind == "cl":
        return compressed(fl, c, P, v)
    if kind == "atm":
        return atmosphere(c, v)
    if kind == "isen":
        return isentropic(v)
    if kind == "shock":
        return shock(v)
    return rayleigh(v)


# ---------------------------------------------------------------------------
# Tooltip help text. What "Start" and "Stop" mean depends on the table, so the
# text is looked up from the table kind each time the mouse hovers.
# ---------------------------------------------------------------------------
RANGE_MEANING = {
    "a1": "Not used for this table.",
    "ideal": "Temperature in K (SI) or R (English).",
    "satT": "Temperature in C (SI) or F (English).",
    "satP": "Pressure in kPa (SI) or psia (English).",
    "sh": "Temperature in C (SI) or F (English).",
    "cl": "Temperature in C (SI) or F (English).",
    "atm": "Altitude in m (SI) or ft (English).",
    "isen": "Mach number.",
    "shock": "Mach number (must be 1 or more).",
    "ray": "Mach number.",
}


# Where each table's numbers come from, shown in the status bar of the window
SOURCES = {
    "a1": "critical constants and molar masses from CoolProp's fluid files",
    "ideal": "CoolProp ideal-gas heat capacity and enthalpy; s0 corrected to 1 atm",
    "satT": "CoolProp equation of state: {eos}",
    "satP": "CoolProp equation of state: {eos}",
    "sh": "CoolProp equation of state: {eos}",
    "cl": "CoolProp equation of state: {eos}",
    "atm": "standard-atmosphere layer equations (ideal gas, R = 287.053 J/kg.K)",
    "isen": "closed-form ideal-gas equations, k = 1.4",
    "shock": "closed-form ideal-gas equations, k = 1.4",
    "ray": "closed-form ideal-gas equations, k = 1.4",
}
EOS = {"Water": "IAPWS-95 (Wagner and Pruss, 2002)",
       "R134a": "Tillner-Roth and Baehr (1994), ASHRAE reference state"}


def source_text(name):
    """Build the one-line 'where do these values come from' message."""
    kind, fl = TABLES[name][0], TABLES[name][1]
    msg = SOURCES[kind].format(eos=EOS.get(fl, ""))
    if kind in ("atm", "isen", "shock", "ray"):   # no CoolProp involved
        return "Source: " + msg
    return "Source: " + msg + "  |  CoolProp " + CP.get_global_param_string("version")


class Tooltip:
    """Small popup text that appears when the mouse hovers over a widget.

    text_fn is a function returning the text, so the message can change
    with the selected table.
    """

    def __init__(self, widget, text_fn):
        self.widget, self.text_fn, self.tip = widget, text_fn, None
        widget.bind("<Enter>", self.show)    # mouse enters -> show
        widget.bind("<Leave>", self.hide)    # mouse leaves -> hide
        widget.bind("<ButtonPress>", self.hide)

    def show(self, _event=None):
        if self.tip:
            return
        # Borderless window placed just below the widget
        x = self.widget.winfo_rootx() + 10
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry("+%d+%d" % (x, y))
        tk.Label(self.tip, text=self.text_fn(), justify="left", wraplength=320,
                 background="#ffffe0", relief="solid", borderwidth=1,
                 padx=6, pady=4).pack()

    def hide(self, _event=None):
        if self.tip:
            self.tip.destroy()
            self.tip = None


class App:
    """The main window: input controls on top, results table below."""

    def __init__(self, root):
        root.title("Thermodynamic Tables (CoolProp)")
        root.geometry("1100x620")
        # Tk variables linked to the widgets
        self.u = tk.StringVar(value="SI")
        self.name = tk.StringVar(value=list(TABLES)[2])
        self.fluid = tk.StringVar(value="Air")
        self.ent = {k: tk.StringVar() for k in "absP"}  # start, stop, step, P

        top = ttk.Frame(root, padding=6)
        top.pack(fill="x")

        # Table selector; re-load defaults whenever it changes
        cb = ttk.Combobox(top, textvariable=self.name, values=list(TABLES),
                          width=42, state="readonly")
        cb.grid(row=0, column=0, columnspan=4, sticky="w")
        cb.bind("<<ComboboxSelected>>", lambda e: self.reset())

        # SI / English radio buttons
        for i, t in enumerate(("SI", "English")):
            ttk.Radiobutton(top, text=t, variable=self.u, value=t,
                            command=self.reset).grid(row=0, column=4 + i)

        # Gas dropdown (only used by the ideal-gas table). Water and R134a are
        # left out because they have their own tables.
        gas_label = ttk.Label(top, text="Gas:")
        gas_label.grid(row=0, column=6, padx=(10, 0))
        gb = ttk.Combobox(top, textvariable=self.fluid,
                          values=FLUIDS[1:12] + FLUIDS[13:], width=16,
                          state="readonly")
        gb.grid(row=0, column=7, padx=4)

        # Start / Stop / Step / P entry boxes, each with a label
        labels = (("a", "Start"), ("b", "Stop"), ("s", "Step"), ("P", "P (fixed)"))
        self.widgets = {}
        for i, (k, lab) in enumerate(labels):
            lbl = ttk.Label(top, text=lab)
            lbl.grid(row=1, column=2 * i)
            en = ttk.Entry(top, textvariable=self.ent[k], width=10)
            en.grid(row=1, column=2 * i + 1)
            self.widgets[k] = (lbl, en)

        ttk.Button(top, text="Generate", command=self.run).grid(row=1, column=8, padx=6)
        ttk.Button(top, text="Export CSV", command=self.export).grid(row=1, column=9)

        # Tooltips (label and box both show the same text)
        meaning = lambda: RANGE_MEANING[TABLES[self.name.get()][0]]
        tips = {
            "a": lambda: "Start: first value of the table's first column.\n"
                         "Here: " + meaning(),
            "b": lambda: "Stop: last value of the table's first column. Rows "
                         "run from Start to Stop.\nHere: " + meaning(),
            "s": lambda: "Step: increment between rows. Smaller step = more rows.",
            "P": lambda: "Fixed pressure (kPa in SI, psia in English). Used only "
                         "by the superheated and compressed-liquid tables, where "
                         "every row is at this one pressure. Ignored otherwise.",
        }
        for k, fn in tips.items():
            for w in self.widgets[k]:
                Tooltip(w, fn)
        gas_tip = lambda: ("Gas: which gas to tabulate in the ideal-gas table "
                           "(A-2 and A-17 to A-23). Ignored by all other tables, "
                           "which use a fixed fluid.")
        Tooltip(gas_label, gas_tip)
        Tooltip(gb, gas_tip)

        # Status bar at the bottom showing where the values come from
        self.src = tk.StringVar()
        ttk.Label(root, textvariable=self.src, relief="sunken",
                  anchor="w", padding=3).pack(side="bottom", fill="x")

        # Results table (Treeview) with a vertical scrollbar
        self.tree = ttk.Treeview(root, show="headings")
        sb = ttk.Scrollbar(root, command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)

        self.h, self.rows = [], []  # last result, kept for CSV export
        self.reset()

    def reset(self):
        """Load default Start/Stop/Step/P for the chosen table and units, then run."""
        d = TABLES[self.name.get()][2 if self.u.get() == "SI" else 3]
        for k, x in zip("absP", d):
            self.ent[k].set(str(x))
        self.run()

    def run(self):
        """Read the inputs, build the table and show it."""
        try:
            a, b, s, P = (float(self.ent[k].get()) for k in "absP")
            if s <= 0:
                raise ValueError("Step must be > 0")
            self.h, self.rows = build(self.name.get(), self.u.get(),
                                      self.fluid.get(), a, b, s, P)
        except Exception as ex:
            messagebox.showerror("Error", str(ex))
            return
        self.src.set(source_text(self.name.get()))
        # Rebuild the Treeview: clear old rows, set new columns, insert rows
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = list(range(len(self.h)))
        for i, t in enumerate(self.h):
            self.tree.heading(i, text=t)
            self.tree.column(i, width=max(80, 9 * len(t)), anchor="e")
        for r in self.rows:
            first = r[0] if isinstance(r[0], str) else "%.6g" % r[0]
            self.tree.insert("", "end", values=[first] + ["%.6g" % x for x in r[1:]])

    def export(self):
        """Save the table currently shown to a CSV file."""
        p = filedialog.asksaveasfilename(defaultextension=".csv")
        if p:
            with open(p, "w", newline="") as fh:
                w = csv.writer(fh)
                w.writerow(self.h)
                w.writerows(self.rows)


if __name__ == "__main__":
    r = tk.Tk()
    App(r)
    r.mainloop()