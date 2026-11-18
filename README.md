# Open Source Thermodynamic Table GUI

A desktop app that generates thermodynamic property tables and charts on demand, in both SI and English units. Values are computed live from published equations of state using open-source libraries, so every number has a traceable source. They are not copied from a textbook.

Built for engineering students and tutorial makers who want steam, refrigerant and ideal-gas tables without relying on a copyrighted book.

## Features

- SI and English unit toggle
- Choose your own start, stop and step, so you can generate exactly the rows you need
- Export any table to CSV
- Charts open in their own window with zoom, pan and save-as-PNG
- Tooltips on every input explaining what it does
- A status bar showing where each table's values come from

## Tables and charts included

| Table | Content |
|---|---|
| A-1 / 1E | Molar mass, gas constant, critical-point properties |
| A-2 / 2E | Ideal-gas properties for any gas (pick from the Gas dropdown) |
| A-3 / 3E | Liquids: boiling point, h_fg, density, cp (**partial**, CoolProp liquids only) |
| A-4 / 4E, A-5 / 5E | Saturated water, temperature and pressure tables |
| A-6 / 6E, A-7 / 7E | Superheated water, compressed liquid water |
| A-8 / 8E | Saturated ice-water vapor |
| A-9, A-10 (chart) | T-s diagram and Mollier diagram for water |
| A-11 to A-13 (and E) | Saturated and superheated R-134a |
| A-14 (chart) | P-h diagram for R-134a |
| A-15 (chart) | Generalized compressibility chart |
| A-16 / 16E | Atmosphere at high altitude |
| A-17 to A-23 (and E) | Ideal-gas properties of air, N2, O2, CO2, CO, H2, water vapor |
| A-24, A-25 | Ideal-gas properties of monatomic oxygen (O) and hydroxyl (OH) |
| A-26 / 26E | Enthalpy and Gibbs function of formation, absolute entropy at 25 C (gas-phase species) |
| A-27 / 27E | Heating values (HHV, LHV) of gaseous fuels (**partial**) |
| A-28 | ln Kp equilibrium constants |
| A-29, A-30 (chart) | Generalized enthalpy and entropy departure charts |
| A-31 (chart) | Psychrometric chart at 1 atm |
| A-32 to A-34 | Isentropic flow, normal shock, Rayleigh flow (k = 1.4) |

## Installation

Requires Python 3 with Tkinter (included with most Python installs).

Core (needed for most tables):

```bash
pip install CoolProp
```

Optional (only the items listed need them; everything else still works without them):

```bash
pip install cantera matplotlib iapws
```

| Package | Needed for |
|---|---|
| cantera | A-24, A-25, A-26, A-27, A-28 |
| matplotlib | All charts (A-9, A-10, A-14, A-15, A-29, A-30, A-31) |
| iapws | A-8 (ice-water vapor) |

On some Linux distributions, install Tkinter separately, for example `sudo apt install python3-tk`.

## Usage

```bash
python thermo_tables_gui.py
```

1. Pick a table from the dropdown.
2. Choose SI or English.
3. Set **Start**, **Stop** and **Step** for the first column (temperature, pressure, altitude or Mach number, depending on the table).
4. For superheated and compressed-liquid tables, set **P (fixed)**, the single pressure for the whole table.
5. For the ideal-gas tables, choose the **Gas**. Picking A-17 to A-23 pre-selects its gas.
6. Click **Generate**, then **Export CSV** if you want to save it. Charts open automatically when selected.

Hover over any input for a description.

## Where the values come from

| Tables | Source |
|---|---|
| Water | IAPWS-95 (Wagner and Pruss, 2002) via CoolProp |
| R-134a | Tillner-Roth and Baehr (1994) via CoolProp, ASHRAE reference state |
| Ideal gases (A-2, A-17 to A-23) | CoolProp ideal-gas heat capacity and enthalpy |
| A-24 to A-28, A-27 | NASA polynomial data (GRI-Mech 3.0) via Cantera |
| A-8 | Ice (IAPWS-06), sublimation pressure and vapor (IAPWS-95) via the iapws package |
| A-15, A-29, A-30 | Simple-fluid corresponding states, evaluated with CoolProp's argon equation of state |
| Psychrometric chart | CoolProp humid-air functions at 101.325 kPa |
| Atmosphere, compressible flow | Closed-form equations (standard-atmosphere layers; ideal gas, k = 1.4) |

## Known differences from textbook tables

- Textbook tables list fixed rows and round their values. This app computes values at whatever rows you request, so the last digit or two may differ.
- Ideal-gas h and s0 for A-2 and A-17 to A-23 use CoolProp's reference state and are per kg, so absolute values differ from textbook tables. Differences between states agree.
- The generalized charts (A-15, A-29, A-30) are computed from a single simple fluid (argon). They show the same behavior as the Nelson-Obert and Lee-Kesler charts but are not those data.
- A-3 covers liquids only. A-27 covers gaseous fuels only. A-26 covers gas-phase species only (no carbon, liquid water or heavier hydrocarbons).
- ln Kp values above about 3500 K may be missing or less reliable.
- Not included: solids and foods (A-3), and liquid and solid fuels (A-27).

## Credits and licences

This project's code is released under the MIT Licence (see [LICENSE](LICENSE)).

It relies on the following open-source projects:

- [CoolProp](http://www.coolprop.org) (MIT). If you use this tool in published work, please cite: Bell, I. H., Wronski, J., Quoilin, S., Lemort, V. (2014). Pure and Pseudo-pure Fluid Thermophysical Property Evaluation and the Open-Source Thermophysical Property Library CoolProp. *Industrial & Engineering Chemistry Research*, 53(6), 2498-2508.
- [Cantera](https://cantera.org) (BSD), optional, for the NASA-polynomial tables.
- [matplotlib](https://matplotlib.org), optional, for charts.
- [iapws](https://github.com/jjgomera/iapws) (**GPL-3.0**), optional, used only for A-8 and loaded only when that table is opened. If you redistribute this project bundled with iapws, the GPL terms apply to iapws.

Water properties follow the standards of the [International Association for the Properties of Water and Steam (IAPWS)](http://www.iapws.org).

## Disclaimer

Provided as is, for education. For safety-critical or certified engineering work, verify values against an authoritative source.
