# Open Source Thermodynamic Table GUI

A desktop app that generates thermodynamic property tables on demand, in both SI and English units. Values are computed live from published equations of state using the open-source [CoolProp](http://www.coolprop.org) library, so every number has a traceable source. They are not copied from a textbook.

Built for engineering students and tutorial makers who need steam, refrigerant and ideal-gas tables without relying on a copyrighted book.

## Features

- SI and English unit toggle
- Choose your own start, stop and step, so you can generate exactly the rows you need
- Export any table to CSV
- Tooltips on every input explaining what it does
- A status bar showing where each table's values come from

## Tables included

| Table | Content |
|---|---|
| A-1 / 1E | Molar mass, gas constant, critical-point properties |
| A-2 / 2E, A-17 to A-23 | Ideal-gas properties (h, u, s0, cp, cv, k) for air, N2, O2, CO2, CO, H2 and others |
| A-4 / 4E | Saturated water, temperature table |
| A-5 / 5E | Saturated water, pressure table |
| A-6 / 6E | Superheated water |
| A-7 / 7E | Compressed liquid water |
| A-11 to A-13 (and E) | Saturated and superheated R-134a |
| A-16 / 16E | Atmosphere at high altitude |
| A-32 to A-34 | Isentropic flow, normal shock and Rayleigh flow (k = 1.4) |

## Installation

Requires Python 3 with Tkinter (included with most Python installs).

```bash
pip install CoolProp
```

On some Linux distributions, install Tkinter separately, for example `sudo apt install python3-tk`.

## Usage

```bash
python thermo_tables_gui.py
```

1. Pick a table from the dropdown.
2. Choose SI or English.
3. Set **Start**, **Stop** and **Step** for the first column (temperature, pressure, altitude or Mach number, depending on the table).
4. For superheated and compressed-liquid tables, set **P (fixed)**, the single pressure for the whole table.
5. For the ideal-gas table, choose the **Gas**.
6. Click **Generate**, then **Export CSV** if you want to save it.

Hover over any input for a description.

## Where the values come from

| Tables | Source |
|---|---|
| Water | IAPWS-95 (Wagner and Pruss, 2002) via CoolProp |
| R-134a | Tillner-Roth and Baehr (1994) via CoolProp, ASHRAE reference state |
| Ideal gases | CoolProp ideal-gas heat capacity and enthalpy |
| Atmosphere, compressible flow | Closed-form equations (standard-atmosphere layers; ideal gas, k = 1.4) |

## Known differences from textbook tables

- Textbook tables list fixed rows and round their values. This app computes values at whatever rows you request, so the last digit or two may differ.
- Ideal-gas h and s0 use CoolProp's reference state, so absolute values differ from textbook tables. Differences between states agree.
- Ideal-gas values are per kg, not per kmol.
- Not included: property charts (T-s, Mollier, P-h, psychrometric, compressibility), and tables of liquids/solids/foods, formation enthalpies, fuels and equilibrium constants.

## Credits

Property calculations use CoolProp. If you use this tool in published work, please cite:

> Bell, I. H., Wronski, J., Quoilin, S., Lemort, V. (2014). Pure and Pseudo-pure Fluid Thermophysical Property Evaluation and the Open-Source Thermophysical Property Library CoolProp. *Industrial & Engineering Chemistry Research*, 53(6), 2498-2508.

Water properties follow the standards of the [International Association for the Properties of Water and Steam (IAPWS)](http://www.iapws.org).

## Licence

Released under the MIT Licence. See [LICENSE](LICENSE).

## Disclaimer

Provided as is, for education. For safety-critical or certified engineering work, verify values against an authoritative source.
