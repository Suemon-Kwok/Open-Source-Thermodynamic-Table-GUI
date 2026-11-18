"""Thermodynamic tables GUI (SI and English units).

Copyright (c) 2026 <YOUR NAME>
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
from CoolProp.CoolProp import HAPropsSI   # humid-air properties (psychrometrics)

# Optional libraries. The app still runs without them; only the tables/charts
# that need them show a message telling you what to install.
try:
    import cantera as ct                 # NASA-polynomial data (A-24, A-25, A-26, A-28)
except Exception:
    ct = None
try:
    import numpy as np
    from matplotlib.figure import Figure  # charts (A-9, A-10, A-14, A-31)
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
except Exception:
    Figure = None

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
# Cantera-based tables: A-24, A-25 (ideal-gas O and OH), A-26 (formation data),
# A-28 (ln Kp). Values are per kmol (SI) or per lbmol (English), and h includes
# the enthalpy of formation, as in the textbook tables.
# ---------------------------------------------------------------------------
_GAS = None


def ct_state(name, T):
    """Put pure species 'name' at T (K) and 1 atm in Cantera and return the object."""
    global _GAS
    if ct is None:
        raise ValueError("Cantera is not installed.  Run:  pip install cantera")
    if _GAS is None:
        _GAS = ct.Solution("gri30.yaml")   # holds NASA polynomials for ~50 species
    _GAS.TPX = T, 101325.0, {name: 1.0}
    return _GAS


def ct_units(c):
    """Return (energy unit, entropy unit, J/kmol per energy unit, J/kmol.K per entropy unit)."""
    if c.si:
        return "kJ/kmol", "kJ/kmol.K", 1000.0, 1000.0
    return "Btu/lbmol", "Btu/lbmol.R", 2326.0, 4186.8


def ct_ideal(name, c, vals):
    """Ideal-gas h, u, s0, cp of one species (monatomic O, hydroxyl OH, ...)."""
    eu, su, ce, cs = ct_units(c)
    Tu = "K" if c.si else "R"
    h = ["T(" + Tu + ")", "h(" + eu + ")", "u(" + eu + ")", "s0(" + su + ")", "cp(" + su + ")"]
    rows = []
    for x in vals:
        g = ct_state(name, x if c.si else x / 1.8)
        rows.append([x, g.enthalpy_mole / ce, g.int_energy_mole / ce,
                     g.entropy_mole / cs, g.cp_mole / cs])
    return h, rows


SPECIES26 = ["H2", "O2", "N2", "O", "H", "N", "OH", "CO", "CO2", "H2O", "H2O2",
             "NH3", "NO", "NO2", "CH4", "C2H2", "C2H4", "C2H6", "C3H8"]
S_CARBON = 5740.0   # J/kmol.K, graphite at 25 C (hard-coded; not in Cantera's gas data)


def formation(c):
    """Table A-26: h_f, g_f and absolute entropy at 25 C (77 F) and 1 atm (gas phase)."""
    eu, su, ce, cs = ct_units(c)
    h = ["Substance", "h_f(" + eu + ")", "g_f(" + eu + ")", "s_abs(" + su + ")"]
    T = 298.15
    # absolute entropies of the elements in their reference form
    s_el = {"C": S_CARBON, "H": ct_state("H2", T).entropy_mole / 2,
            "O": ct_state("O2", T).entropy_mole / 2, "N": ct_state("N2", T).entropy_mole / 2}
    rows = []
    for n in SPECIES26:
        g = ct_state(n, T)
        hf, sa = g.enthalpy_mole, g.entropy_mole
        # entropy of formation = s(compound) - sum of element entropies
        sf = sa - sum(g.n_atoms(n, e) * s_el[e] for e in s_el if e in g.element_names)
        rows.append([n, hf / ce, (hf - T * sf) / ce, sa / cs])
    return h, rows


REACTIONS = [("H2 <-> 2H", {"H2": -1, "H": 2}), ("O2 <-> 2O", {"O2": -1, "O": 2}),
             ("N2 <-> 2N", {"N2": -1, "N": 2}),
             ("H2O <-> H2 + 1/2 O2", {"H2O": -1, "H2": 1, "O2": 0.5}),
             ("H2O <-> 1/2 H2 + OH", {"H2O": -1, "H2": 0.5, "OH": 1}),
             ("CO2 <-> CO + 1/2 O2", {"CO2": -1, "CO": 1, "O2": 0.5}),
             ("1/2 N2 + 1/2 O2 <-> NO", {"N2": -0.5, "O2": -0.5, "NO": 1})]


def lnkp(c, vals):
    """Table A-28: ln Kp = -(sum nu_i g_i(T)) / (Ru T), with g = h - T s at 1 atm."""
    h = ["T(" + ("K" if c.si else "R") + ")"] + ["lnKp " + r[0] for r in REACTIONS]
    rows = []
    for x in vals:
        T = x if c.si else x / 1.8
        g = {}
        for n in {sp for _, r in REACTIONS for sp in r}:
            st = ct_state(n, T)
            g[n] = st.enthalpy_mole - T * st.entropy_mole   # Gibbs function, J/kmol
        rows.append([x] + [-sum(nu * g[n] for n, nu in r.items()) / (RU * T)
                           for _, r in REACTIONS])
    return h, rows


# ---------------------------------------------------------------------------
# Charts (matplotlib): A-9 T-s water, A-10 Mollier water, A-14 P-h R-134a,
# A-31 psychrometric. Each returns a matplotlib Figure.
# ---------------------------------------------------------------------------
def path_isobar(f, P, Tmax, c, xkey, ykey):
    """Points along a constant-pressure line: liquid, saturation jump, vapor."""
    Ts = CP.PropsSI("T", "P", P, "Q", 0, f)
    Tmin = CP.PropsSI("Tmin", f) + 1
    pts = []
    for T in list(np.linspace(Tmin, Ts - 0.01, 40)) + [None] + list(np.linspace(Ts + 0.01, Tmax, 60)):
        if T is None:   # saturation: go from sat. liquid to sat. vapor
            pts += [("l",) + tuple(pp(f, "P", P, "Q", 0, "SH")), ("v",) + tuple(pp(f, "P", P, "Q", 1, "SH"))]
        else:
            pts.append(("x",) + tuple(pp(f, "T", T, "P", P, "SH")) + (T,))
    return pts


def make_chart(kind, c):
    """Build the requested chart in the chosen unit system."""
    if Figure is None:
        raise ValueError("matplotlib is not installed.  Run:  pip install matplotlib")
    if kind in ("chart_z", "chart_zh", "chart_zs"):
        return cs_chart(kind)
    fig = Figure(figsize=(8, 6), dpi=100)
    ax = fig.add_subplot(111)
    if kind in ("chart_ts", "chart_hs"):
        f = "Water"
        Tc = CP.PropsSI("Tcrit", f)
        Td = np.linspace(273.17, Tc - 0.05, 200)
        sf = [c.s(CP.PropsSI("S", "T", T, "Q", 0, f)) for T in Td]
        sg = [c.s(CP.PropsSI("S", "T", T, "Q", 1, f)) for T in Td]
        if kind == "chart_ts":     # T-s diagram
            y_l = [c.To(T) for T in Td]
            ax.plot(sf, y_l, "k"); ax.plot(sg, y_l, "k")
            ax.set_ylabel("T (" + c.Tu + ")")
        else:                      # Mollier h-s diagram
            hf = [c.e(CP.PropsSI("H", "T", T, "Q", 0, f)) for T in Td]
            hg = [c.e(CP.PropsSI("H", "T", T, "Q", 1, f)) for T in Td]
            ax.plot(sf, hf, "k"); ax.plot(sg, hg, "k")
            ax.set_ylabel("h (" + c.eu + ")")
        for Pm in (0.01e6, 0.1e6, 1e6, 5e6, 10e6, 20e6):   # isobars
            xs, ys = [], []
            for tag, S, H, *T in path_isobar(f, Pm, 1073.15, c, 0, 0):
                xs.append(c.s(S)); ys.append(c.To(T[0]) if (kind == "chart_ts" and T) else
                                             (c.e(H) if kind == "chart_hs" else None))
            ys = [y for y in ys]
            if kind == "chart_ts":   # saturation points carry no T; fill with Tsat
                Ts = c.To(CP.PropsSI("T", "P", Pm, "Q", 0, f))
                ys = [Ts if y is None else y for y in ys]
            ax.plot(xs, ys, lw=0.8, label="%.5g %s" % (c.Po(Pm), c.Pu))
        ax.set_xlabel("s (" + c.su + ")"); ax.legend(title="Isobars", fontsize=8)
        ax.set_title("T-s diagram for water" if kind == "chart_ts" else "Mollier diagram for water")
    elif kind == "chart_ph":        # P-h diagram for R-134a
        f = "R134a"
        Tc = CP.PropsSI("Tcrit", f)
        Td = np.linspace(CP.PropsSI("Tmin", f) + 1, Tc - 0.05, 200)
        P_s = [c.Po(CP.PropsSI("P", "T", T, "Q", 0, f)) for T in Td]
        ax.plot([c.e(CP.PropsSI("H", "T", T, "Q", 0, f)) for T in Td], P_s, "k")
        ax.plot([c.e(CP.PropsSI("H", "T", T, "Q", 1, f)) for T in Td], P_s, "k")
        Pg = np.logspace(np.log10(5e4), np.log10(3e7), 120)
        for Tc_ in (-20, 0, 20, 40, 60, 80, 100, 120, 140, 160):   # isotherms (C)
            T = Tc_ + 273.15
            Ps = CP.PropsSI("P", "T", T, "Q", 0, f) if T < Tc else 0
            xs, ys = [], []
            for P in Pg:
                if T < Tc and abs(P - Ps) / Ps < 0.01:
                    continue   # skip the two-phase region
                try:
                    xs.append(c.e(CP.PropsSI("H", "T", T, "P", P, f))); ys.append(c.Po(P))
                except Exception:
                    pass
            ax.plot(xs, ys, lw=0.8, label="%g C" % Tc_ if c.si else "%g F" % (Tc_ * 1.8 + 32))
        ax.set_yscale("log"); ax.set_xlabel("h (" + c.eu + ")"); ax.set_ylabel("P (" + c.Pu + ")")
        ax.legend(title="Isotherms", fontsize=8); ax.set_title("P-h diagram for R-134a")
    else:                           # psychrometric chart at 1 atm
        Pa = 101325.0
        Tk = np.linspace(263.15, 323.15, 61)
        for phi in [i / 10 for i in range(1, 11)]:     # relative-humidity lines
            ax.plot([c.To(T) for T in Tk], [HAPropsSI("W", "T", T, "R", phi, "P", Pa) for T in Tk],
                    "k" if phi == 1 else "gray", lw=1.2 if phi == 1 else 0.7)
            ax.text(c.To(323.15), HAPropsSI("W", "T", 323.15, "R", phi, "P", Pa), "%d%%" % (phi * 100), fontsize=7)
        for Twb in range(0, 31, 5):                    # wet-bulb lines
            xs, ys = [], []
            for T in np.linspace(Twb + 273.15, 323.15, 25):
                try:
                    ys.append(HAPropsSI("W", "T", T, "B", Twb + 273.15, "P", Pa)); xs.append(c.To(T))
                except Exception:
                    pass
            ax.plot(xs, ys, "b", lw=0.5)
        ax.set_xlabel("Dry-bulb T (" + c.Tu + ")")
        ax.set_ylabel("Humidity ratio (" + ("kg water/kg dry air" if c.si else "lbm water/lbm dry air") + ")")
        ax.set_title("Psychrometric chart at 1 atm (blue = constant wet-bulb)")
    ax.grid(alpha=0.3)
    return fig


# ---------------------------------------------------------------------------
# A-8: saturated ice-water vapor. Ice properties use IAPWS-06 and the sublimation
# pressure uses the IAPWS equation, both from the optional "iapws" package
# (GPL-3; imported only when this table is opened). Vapor is from CoolProp.
# ---------------------------------------------------------------------------
def ice_vapor(c, vals):
    try:
        from iapws import IAPWS95   # same IAPWS-95 equation as CoolProp, but allows T below 273.16 K
        from iapws._iapws import _Sublimation_Pressure, _Ice
    except Exception:
        raise ValueError("The iapws package is not installed.  Run:  pip install iapws")
    import warnings                       # iapws warns when extrapolating below 273 K; expected here
    warnings.filterwarnings("ignore", message="Using extrapolated values")
    h = ["T(" + c.Tu + ")", "Psat(" + c.Pu + ")", "v_i", "v_g", "u_i", "u_ig", "u_g",
         "h_i", "h_ig", "h_g", "s_i", "s_ig", "s_g"]
    rows = []
    for x in vals:
        T = c.T(x)
        if T > 273.16:
            continue                       # ice only exists below the triple point here
        try:
            Pm = _Sublimation_Pressure(T)  # MPa
            i = _Ice(T, Pm)                # v m3/kg, u and h kJ/kg, s kJ/kg.K
            w = IAPWS95(T=T, P=Pm)         # metastable vapor at the sublimation pressure
            g = [w.rho, w.u * 1000, w.h * 1000, w.s * 1000]      # density in kg/m3, rest in J/kg
            ui, hi, si = i["u"] * 1000, i["h"] * 1000, i["s"] * 1000
            rows.append([x, c.Po(Pm * 1e6), c.v(i["v"]), c.v(1 / g[0]),
                         c.e(ui), c.e(g[1] - ui), c.e(g[1]),
                         c.e(hi), c.e(g[2] - hi), c.e(g[2]),
                         c.s(si), c.s(g[3] - si), c.s(g[3])])
        except Exception:
            continue
    return h, rows


# ---------------------------------------------------------------------------
# A-3 (liquid part only): boiling point, h_fg, density and cp, from CoolProp
# ---------------------------------------------------------------------------
LIQ3 = ["Ammonia", "Argon", "Benzene", "Ethanol", "Methanol", "n-Butane", "IsoButane",
        "Methane", "Nitrogen", "Oxygen", "n-Octane", "Propane", "R134a", "Water",
        "Hydrogen", "Helium", "Mercury"]


def liquids(c, T0):
    """T0 (Start box) is the liquid temperature; if it is above a substance's normal
    boiling point, the boiling point itself is used (as the book does for cryogens)."""
    h = ["Substance", "Tboil(" + c.Tu + ")", "h_fg(" + c.eu + ")", "T_used(" + c.Tu + ")",
         "rho(" + ("kg/m3" if c.si else "lbm/ft3") + ")", "cp(" + c.su + ")"]
    rows = []
    for f in LIQ3:
        try:
            Tb = CP.PropsSI("T", "P", 101325, "Q", 0, f)
            hfg = CP.PropsSI("H", "P", 101325, "Q", 1, f) - CP.PropsSI("H", "P", 101325, "Q", 0, f)
            T = min(c.T(T0), Tb)
            o = ("Q", 0) if T >= Tb - 1e-6 else ("P", 101325)
            rho, cp = (CP.PropsSI(k, "T", T, o[0], o[1], f) for k in ("D", "C"))
            rows.append([f, c.To(Tb), c.e(hfg), c.To(T), c.rho(rho), c.s(cp)])
        except Exception:
            continue
    return h, rows


# ---------------------------------------------------------------------------
# A-27 (gaseous fuels only): heating values from formation enthalpies (Cantera)
# ---------------------------------------------------------------------------
FUELS = ["H2", "CO", "CH4", "C2H2", "C2H4", "C2H6", "C3H8"]


def fuels(c):
    """HHV/LHV per kg of fuel for complete combustion at 25 C.
    LHV = h_f(fuel) - x h_f(CO2) - (y/2) h_f(H2O gas);  HHV adds (y/2) h_fg of water."""
    h = ["Fuel", "M(" + ("kg/kmol" if c.si else "lbm/lbmol") + ")",
         "HHV(" + c.eu + ")", "LHV(" + c.eu + ")"]
    T = 298.15
    hf = {n: ct_state(n, T).enthalpy_mole for n in ("CO2", "H2O")}
    Mw = CP.PropsSI("molar_mass", "Water") * 1000
    hfg = (CP.PropsSI("H", "T", T, "Q", 1, "Water") - CP.PropsSI("H", "T", T, "Q", 0, "Water")) * Mw
    rows = []
    for n in FUELS:
        g = ct_state(n, T)
        x, y = g.n_atoms(n, "C"), g.n_atoms(n, "H")
        M = g.mean_molecular_weight
        lhv = (g.enthalpy_mole - x * hf["CO2"] - y / 2 * hf["H2O"]) / M   # J/kg
        hhv = lhv + y / 2 * hfg / M
        rows.append([n, M, c.e(hhv), c.e(lhv)])
    return h, rows


# ---------------------------------------------------------------------------
# A-15, A-29, A-30: generalized charts by corresponding states. A high-accuracy
# simple fluid (argon, acentric factor about 0) is evaluated at Tr, Pr:
#   Z, Zh = (h* - h)/(R Tc), Zs = (s* - s)/R   (* = ideal gas at same T and P)
# These are NOT the Nelson-Obert / Lee-Kesler tables, but the same idea.
# ---------------------------------------------------------------------------
def argon_cs(Tr, Pr):
    f = "Argon"
    Tc, Pc = CP.PropsSI("Tcrit", f), CP.PropsSI("pcrit", f)
    R = 8.314462618 / CP.PropsSI("molar_mass", f)
    if abs(Tr - 1.0) < 1e-6:
        Tr = 1.0005      # exactly at Tc some CoolProp versions fail; this is visually identical
    T, P, Plow = Tr * Tc, Pr * Pc, 1.0           # Plow = 1 Pa stands in for ideal gas
    Z = CP.PropsSI("Z", "T", T, "P", P, f)
    Zh = (CP.PropsSI("H", "T", T, "P", Plow, f) - CP.PropsSI("H", "T", T, "P", P, f)) / (R * Tc)
    Zs = (CP.PropsSI("S", "T", T, "P", Plow, f) - R * math.log(P / Plow)
          - CP.PropsSI("S", "T", T, "P", P, f)) / R
    return Z, Zh, Zs


def cs_chart(kind):
    """Draw Z, Zh or Zs against Pr with one curve per reduced temperature Tr."""
    idx = {"chart_z": 0, "chart_zh": 1, "chart_zs": 2}[kind]
    fig = Figure(figsize=(8, 6), dpi=100)
    ax = fig.add_subplot(111)
    Pc = CP.PropsSI("pcrit", "Argon")
    grid = np.linspace(0.02, 10, 250) if kind == "chart_z" else np.logspace(-1, 1, 140)
    for Tr in (0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.5, 2.0, 3.0):
        Ps = CP.PropsSI("P", "T", Tr * CP.PropsSI("Tcrit", "Argon"), "Q", 0, "Argon") / Pc if Tr < 1 else None
        segs = {"v": ([], []), "l": ([], [])}      # vapor side and liquid side
        for Pr in grid:
            k = "v"
            if Ps:
                if abs(Pr - Ps) / Ps < 0.02:
                    continue                       # skip the two-phase region
                k = "v" if Pr < Ps else "l"
            try:
                val = argon_cs(Tr, Pr)[idx]
            except Exception:
                continue                           # skip a point CoolProp cannot evaluate
            segs[k][0].append(Pr); segs[k][1].append(val)
        col = None
        for k in ("v", "l"):
            if segs[k][0]:
                ln, = ax.plot(*segs[k], color=col, lw=1, label="Tr = %g" % Tr if col is None else None)
                col = ln.get_color()
    names = {"chart_z": ("Z", "Generalized compressibility chart (simple fluid)"),
             "chart_zh": ("Zh = (h* - h)/(Ru Tc)", "Generalized enthalpy departure chart"),
             "chart_zs": ("Zs = (s* - s)/Ru", "Generalized entropy departure chart")}[kind]
    ax.set_xlabel("Reduced pressure Pr"); ax.set_ylabel(names[0]); ax.set_title(names[1])
    if kind != "chart_z":
        ax.set_xscale("log")
    ax.legend(fontsize=8); ax.grid(alpha=0.3)
    return fig

# ---------------------------------------------------------------------------
# Menu definition.
# name -> (kind, fixed fluid, SI defaults, English defaults)
# Defaults are (start, stop, step, fixed P). They fill the input boxes
# whenever the table or the unit system changes.
# ---------------------------------------------------------------------------
TABLES = {
    "A-1/1E  Molar mass, R, critical point": ("a1", None, (0, 0, 1, 0), (0, 0, 1, 0)),
    "A-2/2E  Ideal-gas props - any gas (pick gas)": ("ideal", "Air", (200, 1000, 50, 0), (400, 1800, 100, 0)),
    "A-4/4E  Sat. water - temperature": ("satT", "Water", (0.01, 370, 10, 0), (32.02, 700, 20, 0)),
    "A-5/5E  Sat. water - pressure": ("satP", "Water", (10, 3000, 200, 0), (1, 500, 25, 0)),
    "A-6/6E  Superheated water": ("sh", "Water", (100, 700, 50, 100), (212, 1200, 100, 14.7)),
    "A-7/7E  Compressed liquid water": ("cl", "Water", (0, 300, 20, 5000), (32, 500, 40, 1000)),
    "A-11/11E  Sat. R-134a - temperature": ("satT", "R134a", (-40, 100, 10, 0), (-40, 200, 20, 0)),
    "A-12/12E  Sat. R-134a - pressure": ("satP", "R134a", (60, 1600, 100, 0), (10, 200, 10, 0)),
    "A-13/13E  Superheated R-134a": ("sh", "R134a", (-20, 100, 10, 400), (0, 200, 20, 60)),
    "A-16/16E  Atmosphere at high altitude": ("atm", None, (0, 30000, 1000, 0), (0, 100000, 5000, 0)),
    "A-17/17E  Ideal-gas air": ("ideal", "Air", (200, 1000, 50, 0), (400, 1800, 100, 0)),
    "A-18/18E  Ideal-gas nitrogen, N2": ("ideal", "Nitrogen", (200, 1000, 50, 0), (400, 1800, 100, 0)),
    "A-19/19E  Ideal-gas oxygen, O2": ("ideal", "Oxygen", (200, 1000, 50, 0), (400, 1800, 100, 0)),
    "A-20/20E  Ideal-gas carbon dioxide, CO2": ("ideal", "CarbonDioxide", (200, 1000, 50, 0), (400, 1800, 100, 0)),
    "A-21/21E  Ideal-gas carbon monoxide, CO": ("ideal", "CarbonMonoxide", (200, 1000, 50, 0), (400, 1800, 100, 0)),
    "A-22/22E  Ideal-gas hydrogen, H2": ("ideal", "Hydrogen", (200, 1000, 50, 0), (400, 1800, 100, 0)),
    "A-23/23E  Ideal-gas water vapor, H2O": ("ideal", "Water", (300, 1800, 100, 0), (540, 3200, 200, 0)),
    "A-24/24E  Ideal-gas monatomic oxygen, O": ("ctgas", "O", (300, 3000, 100, 0), (540, 5400, 200, 0)),
    "A-25/25E  Ideal-gas hydroxyl, OH": ("ctgas", "OH", (300, 3000, 100, 0), (540, 5400, 200, 0)),
    "A-26/26E  Formation h, g, abs. entropy (25 C)": ("form", None, (0, 0, 1, 0), (0, 0, 1, 0)),
    "A-28  ln Kp equilibrium constants": ("lnkp", None, (300, 3000, 100, 0), (540, 5400, 200, 0)),
    "A-9/9E  T-s diagram, water (chart)": ("chart_ts", "Water", (0, 0, 1, 0), (0, 0, 1, 0)),
    "A-10/10E  Mollier diagram, water (chart)": ("chart_hs", "Water", (0, 0, 1, 0), (0, 0, 1, 0)),
    "A-14/14E  P-h diagram, R-134a (chart)": ("chart_ph", "R134a", (0, 0, 1, 0), (0, 0, 1, 0)),
    "A-31/31E  Psychrometric chart, 1 atm (chart)": ("chart_psy", None, (0, 0, 1, 0), (0, 0, 1, 0)),
    "A-3/3E  Liquids: boiling pt, h_fg, rho, cp (partial)": ("liq", None, (25, 25, 1, 0), (77, 77, 1, 0)),
    "A-8/8E  Sat. ice-water vapor": ("ice", "Water", (-40, 0, 5, 0), (-40, 32, 8, 0)),
    "A-15  Generalized compressibility chart (chart)": ("chart_z", None, (0, 0, 1, 0), (0, 0, 1, 0)),
    "A-27/27E  Heating values of gaseous fuels (partial)": ("fuels", None, (0, 0, 1, 0), (0, 0, 1, 0)),
    "A-29  Generalized enthalpy departure chart (chart)": ("chart_zh", None, (0, 0, 1, 0), (0, 0, 1, 0)),
    "A-30  Generalized entropy departure chart (chart)": ("chart_zs", None, (0, 0, 1, 0), (0, 0, 1, 0)),
    "A-32  Isentropic flow, k=1.4": ("isen", None, (0.1, 3, 0.1, 0), (0.1, 3, 0.1, 0)),
    "A-33  Normal shock, k=1.4": ("shock", None, (1, 3, 0.1, 0), (1, 3, 0.1, 0)),
    "A-34  Rayleigh flow, k=1.4": ("ray", None, (0.1, 3, 0.1, 0), (0.1, 3, 0.1, 0)),
}


# Put the menu in textbook order (A-1, A-2, A-4, A-5 ... by table number)
TABLES = dict(sorted(TABLES.items(), key=lambda kv: int(kv[0][2:].split("/")[0].split(" ")[0])))


def build(name, units, fluid, a, b, s, P):
    """Pick the right builder for the selected table and run it."""
    kind, fl, _, _ = TABLES[name]
    c = Conv(units)
    v = frange(a, b, s)  # the list of values for the first column
    if kind == "a1":
        return a1(c)
    if kind == "ctgas":
        return ct_ideal(fl, c, v)
    if kind == "ice":
        return ice_vapor(c, v)
    if kind == "liq":
        return liquids(c, a)
    if kind == "fuels":
        return fuels(c)
    if kind == "form":
        return formation(c)
    if kind == "lnkp":
        return lnkp(c, v)
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
    "ctgas": "Temperature in K (SI) or R (English).",
    "lnkp": "Temperature in K (SI) or R (English).",
    "form": "Not used for this table.",
    "ice": "Temperature in C (SI) or F (English), at or below the triple point.",
    "liq": "Start = liquid temperature in C or F (used if below the boiling point). Stop and Step are unused.",
    "fuels": "Not used for this table.",
    "chart_z": "Not used (chart).", "chart_zh": "Not used (chart).", "chart_zs": "Not used (chart).",
    "chart_ts": "Not used (chart).", "chart_hs": "Not used (chart).",
    "chart_ph": "Not used (chart).", "chart_psy": "Not used (chart).",
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
    "ctgas": "NASA polynomial data (GRI-Mech 3.0) via Cantera; h includes formation enthalpy",
    "form": "NASA polynomial data (GRI-Mech 3.0) via Cantera, gas phase; carbon s = 5.74 hard-coded",
    "lnkp": "ln Kp from Gibbs functions (NASA polynomials via Cantera), at 1 atm",
    "ice": "ice (IAPWS-06), sublimation pressure and vapor (IAPWS-95), all via the iapws package",
    "liq": "CoolProp equations of state (liquids CoolProp supports; solids and foods not included)",
    "fuels": "heating values from formation enthalpies (NASA polynomials via Cantera), gas-phase fuels only",
    "chart_z": "simple-fluid corresponding states from CoolProp's argon equation of state (not Nelson-Obert data)",
    "chart_zh": "simple-fluid corresponding states from CoolProp's argon equation of state (not Lee-Kesler tables)",
    "chart_zs": "simple-fluid corresponding states from CoolProp's argon equation of state (not Lee-Kesler tables)",
    "chart_ts": "CoolProp equation of state: {eos}",
    "chart_hs": "CoolProp equation of state: {eos}",
    "chart_ph": "CoolProp equation of state: {eos}",
    "chart_psy": "CoolProp humid-air functions at 101.325 kPa",
}
EOS = {"Water": "IAPWS-95 (Wagner and Pruss, 2002)",
       "R134a": "Tillner-Roth and Baehr (1994), ASHRAE reference state"}


def source_text(name):
    """Build the one-line 'where do these values come from' message."""
    kind, fl = TABLES[name][0], TABLES[name][1]
    msg = SOURCES[kind].format(eos=EOS.get(fl, ""))
    if kind in ("atm", "isen", "shock", "ray"):   # no CoolProp involved
        return "Source: " + msg
    if kind in ("ctgas", "form", "lnkp", "fuels"):
        return "Source: " + msg + "  |  Cantera " + (ct.__version__ if ct else "(not installed)")
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
                          values=FLUIDS[:12] + FLUIDS[13:], width=16,
                          state="readonly")
        gb.grid(row=0, column=7, padx=4)
        gb.bind("<<ComboboxSelected>>", lambda e: self.run())  # refresh on change

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
        gas_tip = lambda: ("Gas: which gas to tabulate in the ideal-gas tables "
                           "(A-2 and A-17 to A-23). Picking table A-17 to A-23 "
                           "pre-selects its gas; you can change it here at any "
                           "time. Ignored by all other tables.")
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
        kind, fl = TABLES[self.name.get()][:2]
        if kind == "ideal" and fl:
            self.fluid.set(fl)   # e.g. A-22 selects Hydrogen
        d = TABLES[self.name.get()][2 if self.u.get() == "SI" else 3]
        for k, x in zip("absP", d):
            self.ent[k].set(str(x))
        self.run()

    def run(self):
        """Read the inputs, build the table and show it."""
        if TABLES[self.name.get()][0].startswith("chart"):
            self.src.set(source_text(self.name.get()))
            self.tree.delete(*self.tree.get_children())   # remove the previous table
            self.tree["columns"] = []
            self.show_chart()      # charts open in their own window
            return
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

    def show_chart(self):
        """Draw the chart in a separate window (replaces any chart already open)."""
        try:
            fig = make_chart(TABLES[self.name.get()][0], Conv(self.u.get()))
        except Exception as ex:
            messagebox.showerror("Error", str(ex))
            return
        if getattr(self, "chartwin", None):
            try:
                self.chartwin.destroy()
            except Exception:
                pass
        self.chartwin = tk.Toplevel(self.tree)
        self.chartwin.title(self.name.get())
        canvas = FigureCanvasTkAgg(fig, master=self.chartwin)
        canvas.draw()
        NavigationToolbar2Tk(canvas, self.chartwin)   # zoom / pan / save-as-PNG toolbar
        canvas.get_tk_widget().pack(fill="both", expand=True)

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