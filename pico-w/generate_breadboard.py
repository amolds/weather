import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

fig, ax = plt.subplots(figsize=(26, 13))
ax.axis('off')
fig.patch.set_facecolor('#f0ede0')

# ── Grid constants ────────────────────────────────────────────────────────────
PITCH   = 0.5      # hole pitch in inches (display units)
COLS    = 74       # extended to fit SD card + LEDs
BB_X0   = 3.5      # breadboard left edge
BB_Y0   = 1.2      # breadboard bottom edge
BB_W    = COLS * PITCH + 0.5
BB_H    = 10 * PITCH + 3.7  # rows a-j + power rails (added 5V rail)

def row_y(r):
    row_map = {'j':0,'i':1,'h':2,'g':3,'f':4,'e':5,'d':6,'c':7,'b':8,'a':9}
    base = BB_Y0 + 0.4
    idx = row_map[r]
    gap = 0.5 if idx >= 5 else 0
    return base + idx * PITCH + gap

def col_x(c):
    return BB_X0 + 0.3 + (c - 1) * PITCH

# Power rails (from bottom of rail area upward)
PWR_5V_Y  = BB_Y0 + BB_H - 0.55   # new: VSYS / 5V for SD card
PWR_3V3_Y = BB_Y0 + BB_H - 1.05
PWR_GND_Y = BB_Y0 + BB_H - 1.55
PWR_SCL_Y = BB_Y0 + BB_H - 2.05
PWR_SDA_Y = BB_Y0 + BB_H - 2.55

# ── Draw breadboard body ──────────────────────────────────────────────────────
bb = patches.FancyBboxPatch((BB_X0, BB_Y0), BB_W, BB_H,
    boxstyle="round,pad=0,rounding_size=0.15",
    facecolor='#e8e0c8', edgecolor='#999', linewidth=1.5)
ax.add_patch(bb)

ax.add_patch(patches.Rectangle((BB_X0+0.2, row_y('f')-0.3), BB_W-0.4, 0.38,
    facecolor='#d0c8b0', edgecolor='none'))

for r in ['a','b','c','d','e','f','g','h','i','j']:
    for c in range(1, COLS+1):
        ax.plot(col_x(c), row_y(r), 's', color='#555544', markersize=2.8, zorder=3)

# Power rail holes and strips
rail_defs = [
    (PWR_5V_Y,  '#cc3333', '#ffd0d0', '5V'),
    (PWR_3V3_Y, '#cc3333', '#ffdddd', '3V3'),
    (PWR_GND_Y, '#555555', '#dddddd', 'GND'),
    (PWR_SCL_Y, '#bbaa00', '#ffffcc', 'SCL'),
    (PWR_SDA_Y, '#cc6600', '#ffe5cc', 'SDA'),
]
for ry, hcol, fc, lbl in rail_defs:
    for c in range(1, COLS+1):
        ax.plot(col_x(c), ry, 's', color=hcol, markersize=2.5, alpha=0.4, zorder=3)
    ax.add_patch(patches.Rectangle((BB_X0+0.2, ry-0.12), BB_W-0.4, 0.24,
        facecolor=fc, edgecolor='none', alpha=0.6, zorder=1))
    ax.text(BB_X0 + BB_W + 0.15, ry, lbl, va='center',
            color=hcol if lbl != 'GND' else '#555555',
            fontsize=7.5, fontweight='bold')

# ── Pico W (cols 4-23, rows a-j) ─────────────────────────────────────────────
PX0 = col_x(4) - 0.15
PY0 = row_y('j') - 0.2
PW  = col_x(23) - col_x(4) + 0.35
PH  = row_y('a') - row_y('j') + 0.4

ax.add_patch(patches.FancyBboxPatch((PX0, PY0), PW, PH,
    boxstyle="round,pad=0,rounding_size=0.12",
    facecolor='#1a5276', edgecolor='#aaddff', linewidth=1.5, zorder=4))
ax.text(PX0+PW/2, PY0+PH/2+0.2, 'Raspberry Pi', ha='center', va='center',
        color='white', fontsize=8, fontweight='bold', zorder=5)
ax.text(PX0+PW/2, PY0+PH/2-0.2, 'Pico W', ha='center', va='center',
        color='#aaddff', fontsize=9, fontweight='bold', zorder=5)

# Left-side (row a) Pico pin labels
# Pin 1=GP0, 2=GP1, 3=GND, 5=GND, 8=3V3(out)...
# Pin 14=GP10(SCK), 15=GP11(MOSI), 16=GP12(MISO), 17=GP13(CS)
# Pin 18=GND, 19=GP14(LED_HTTP/RED), 20=GP15(LED_SD/WHITE)
pico_top_pins = {
    4:  ('GP0\nSDA',   '#cc6600'),
    5:  ('GP1\nSCL',   '#999900'),
    8:  ('GND',        '#555555'),
    9:  ('3V3',        '#cc2222'),
    17: ('GP10\nSCK',  '#3366ff'),
    18: ('GP11\nMOSI', '#9933cc'),
    19: ('GP12\nMISO', '#009988'),
    20: ('GP13\nCS',   '#886600'),
    21: ('GND',        '#555555'),
    22: ('GP14\nRED',  '#dd0000'),
    23: ('GP15\nWHT',  '#aaaaaa'),
}
for c, (lbl, col) in pico_top_pins.items():
    ax.plot(col_x(c), row_y('a'), 'o', color=col, markersize=5, zorder=6)
    ax.text(col_x(c), row_y('a')+0.35, lbl, ha='center', va='bottom',
            color=col, fontsize=5.5, fontweight='bold', zorder=6)

# Right-side (row j): VSYS at col 5
ax.plot(col_x(5), row_y('j'), 'o', color='#cc2222', markersize=5, zorder=6)
ax.text(col_x(5), row_y('j')-0.35, 'VSYS\n5V', ha='center', va='top',
        color='#cc2222', fontsize=5.5, fontweight='bold', zorder=6)

# ── Sensor helper ─────────────────────────────────────────────────────────────
def draw_sensor(col_start, label, addr, color, pin_names):
    x0 = col_x(col_start) - 0.2
    y0 = row_y('c') - 0.15
    w  = len(pin_names) * PITCH - 0.05
    h  = row_y('g') - row_y('c') + 0.3
    ax.add_patch(patches.FancyBboxPatch((x0, y0), w, h,
        boxstyle="round,pad=0,rounding_size=0.1",
        facecolor=color, edgecolor='#333', linewidth=1.2, zorder=4))
    ax.text(x0+w/2, y0+h*0.65, label,  ha='center', va='center',
            color='white', fontsize=7.5, fontweight='bold', zorder=5)
    ax.text(x0+w/2, y0+h*0.28, addr,   ha='center', va='center',
            color='#dddddd', fontsize=6.5, zorder=5)
    for i, (pname, pcol) in enumerate(pin_names):
        cx = col_x(col_start + i)
        ax.plot(cx, row_y('b'), 'o', color='#cccccc', markersize=4.5,
                markeredgecolor='#333', zorder=6)
        ax.text(cx, row_y('b')-0.28, pname, ha='center', va='top',
                color='#444', fontsize=6, zorder=6)
        ax.plot([cx, cx], [y0, row_y('b')+0.1], color='#888', lw=1, zorder=3)
    return {pin_names[i][0]: col_x(col_start+i) for i in range(len(pin_names))}

sht_pins = draw_sensor(28, 'SHT31',   '0x44  Temp+RH',  '#7b2d2d',
    [('VIN','#cc2222'),('GND','#555'),('SCL','#999900'),('SDA','#cc6600')])
tsl_pins = draw_sensor(34, 'TSL2591', '0x29  Lux',      '#1a4a7a',
    [('VIN','#cc2222'),('GND','#555'),('SCL','#999900'),('SDA','#cc6600')])
bmp_pins = draw_sensor(40, 'BMP390',  '0x77  Pressure', '#1a5c1a',
    [('VIN','#cc2222'),('GND','#555'),('SCK','#999900'),('SDI','#cc6600')])

ax.text(col_x(44), row_y('b')-0.72, 'CS + SDO:\nleave open',
        ha='center', va='top', color='#cc4400', fontsize=5.5, style='italic')

# ── SD card module (cols 48-53, upper half) ───────────────────────────────────
SD_COL = 48
sd_pin_defs = [
    ('3V3',  '#cc2222'),
    ('CS',   '#886600'),
    ('MOSI', '#9933cc'),
    ('CLK',  '#3366ff'),
    ('MISO', '#009988'),
    ('GND',  '#555555'),
]
sd_pins = draw_sensor(SD_COL, 'SD Card', 'SPI1  GP10-13', '#4a3060', sd_pin_defs)

ax.text(col_x(SD_COL+2), row_y('g')+0.65, 'VCC → 5V (Pin 39)',
        ha='center', va='bottom', color='#cc2222', fontsize=5.5, style='italic', zorder=7)

# ── LEDs with resistors (cols 57-63, lower half of board) ────────────────────
def draw_led(col, color_hex, label, pico_col, resistor_row='h', led_row='i'):
    rx = col_x(col)
    ry_res = row_y(resistor_row)
    ry_led = row_y(led_row)
    # Resistor body
    ax.add_patch(patches.FancyBboxPatch(
        (rx-0.12, ry_res-0.12), 0.24, 0.24,
        boxstyle="round,pad=0,rounding_size=0.04",
        facecolor='#d4c88a', edgecolor='#555', linewidth=1.2, zorder=6))
    ax.text(rx, ry_res, '330Ω', ha='center', va='center',
            fontsize=4.5, color='#222', zorder=7)
    # LED body (circle)
    led_circle = plt.Circle((rx, ry_led), 0.18,
        color=color_hex, ec='#333', lw=1.2, zorder=6)
    ax.add_patch(led_circle)
    ax.text(rx, ry_led, label, ha='center', va='center',
            fontsize=5, color='white', fontweight='bold', zorder=7)
    # Wire from Pico pin to resistor top (via row a → breadboard hole → down)
    px = col_x(pico_col)
    ax.plot([px, px, rx, rx], [row_y('a'), row_y('a')+0.25, row_y('a')+0.25, ry_res+0.12],
            color=color_hex, lw=2, solid_capstyle='round', zorder=2)
    # Wire from resistor bottom to LED top
    ax.plot([rx, rx], [ry_res-0.12, ry_led+0.18],
            color=color_hex, lw=2, solid_capstyle='round', zorder=2)
    # Wire from LED bottom to GND rail
    ax.plot([rx, rx], [ry_led-0.18, PWR_GND_Y],
            color='#888888', lw=2, solid_capstyle='round', zorder=2)

draw_led(57, '#cc2222', 'RED', pico_col=22)   # GP14, Pin 19
draw_led(60, '#dddddd', 'WHT', pico_col=23)   # GP15, Pin 20

# Labels under LEDs
ax.text(col_x(57), row_y('j')-0.2, 'GP14\nPin 19\nHTTP', ha='center', va='top',
        color='#cc2222', fontsize=5.5, fontweight='bold')
ax.text(col_x(60), row_y('j')-0.2, 'GP15\nPin 20\nSD log', ha='center', va='top',
        color='#777777', fontsize=5.5, fontweight='bold')

# ── Wires: I2C sensors → power rails ─────────────────────────────────────────
i2c_wires = [
    (sht_pins['VIN'], PWR_3V3_Y, '#ee2222'),
    (sht_pins['GND'], PWR_GND_Y, '#888888'),
    (sht_pins['SCL'], PWR_SCL_Y, '#ccbb00'),
    (sht_pins['SDA'], PWR_SDA_Y, '#ee7700'),
    (tsl_pins['VIN'], PWR_3V3_Y, '#ee2222'),
    (tsl_pins['GND'], PWR_GND_Y, '#888888'),
    (tsl_pins['SCL'], PWR_SCL_Y, '#ccbb00'),
    (tsl_pins['SDA'], PWR_SDA_Y, '#ee7700'),
    (bmp_pins['VIN'], PWR_3V3_Y, '#ee2222'),
    (bmp_pins['GND'], PWR_GND_Y, '#888888'),
    (bmp_pins['SCK'], PWR_SCL_Y, '#ccbb00'),
    (bmp_pins['SDI'], PWR_SDA_Y, '#ee7700'),
]
for xw, ry, col in i2c_wires:
    ax.plot([xw, xw], [row_y('b'), ry], color=col, lw=2.5,
            solid_capstyle='round', zorder=2)

# ── Wires: Pico I2C + 3V3/GND → power rails ──────────────────────────────────
for xp, ry, col in [
    (col_x(9),  PWR_3V3_Y, '#ee2222'),
    (col_x(8),  PWR_GND_Y, '#888888'),
    (col_x(5),  PWR_SCL_Y, '#ccbb00'),
    (col_x(4),  PWR_SDA_Y, '#ee7700'),
]:
    ax.plot([xp, xp], [row_y('a'), ry], color=col, lw=2.8,
            solid_capstyle='round', zorder=2)

# ── Wires: Pico VSYS → 5V rail ───────────────────────────────────────────────
vsys_x = col_x(5)
ax.plot([vsys_x, vsys_x], [row_y('j'), PWR_5V_Y],
        color='#ee2222', lw=2.8, solid_capstyle='round', zorder=2)

# ── Wires: SD card → SPI pins + rails ────────────────────────────────────────
# SD 3V3 pin → 5V rail (SD adapter has onboard regulator, uses 5V in)
ax.plot([sd_pins['3V3'], sd_pins['3V3']], [row_y('b'), PWR_5V_Y],
        color='#ee2222', lw=2.5, solid_capstyle='round', zorder=2)
# SD GND → GND rail
ax.plot([sd_pins['GND'], sd_pins['GND']], [row_y('b'), PWR_GND_Y],
        color='#888888', lw=2.5, solid_capstyle='round', zorder=2)

# SD SPI pins: routed via angled paths to Pico pins on row a
spi_routes = [
    ('CS',   col_x(20), '#886600'),   # GP13
    ('CLK',  col_x(17), '#3366ff'),   # GP10
    ('MOSI', col_x(18), '#9933cc'),   # GP11
    ('MISO', col_x(19), '#009988'),   # GP12
]
for offset, (key, pico_x, col) in enumerate(spi_routes):
    sx = sd_pins[key]
    sy = row_y('b')
    route_y = row_y('a') + 0.55 + offset * 0.18  # stagger above board
    ax.plot([sx,  sx,  pico_x, pico_x],
            [sy, route_y, route_y, row_y('a')],
            color=col, lw=2, solid_capstyle='round', zorder=2)

# ── Legend ────────────────────────────────────────────────────────────────────
lx, ly = 0.18, 11.5
ax.text(lx, ly, 'Wire Legend', color='#222', fontsize=8.5, fontweight='bold')
legend_items = [
    ('3V3  Power',       '#ee2222'),
    ('5V   VSYS',        '#cc2222'),
    ('GND  Ground',      '#888888'),
    ('SCL  GP1',         '#ccbb00'),
    ('SDA  GP0',         '#ee7700'),
    ('SCK  GP10 (SPI)',  '#3366ff'),
    ('MOSI GP11 (SPI)',  '#9933cc'),
    ('MISO GP12 (SPI)',  '#009988'),
    ('CS   GP13 (SPI)',  '#886600'),
    ('GP14 RED LED',     '#cc2222'),
    ('GP15 WHT LED',     '#888888'),
]
for i, (lbl, col) in enumerate(legend_items):
    yy = ly - 0.48*(i+1)
    ax.plot([lx, lx+0.6], [yy, yy], color=col, lw=3, solid_capstyle='round')
    ax.text(lx+0.75, yy, lbl, color='#222', fontsize=7, va='center')

# ── Title ─────────────────────────────────────────────────────────────────────
ax.set_xlim(0, BB_X0 + BB_W + 1.5)
ax.set_ylim(0.3, BB_Y0 + BB_H + 1.7)
ax.set_aspect('equal')
ax.text((BB_X0 + BB_W/2), BB_Y0 + BB_H + 1.2,
        'Pico W Weather Station — Breadboard Wiring',
        ha='center', color='#111', fontsize=14, fontweight='bold')
ax.text((BB_X0 + BB_W/2), BB_Y0 + BB_H + 0.72,
        'SHT31 · TSL2591 · BMP390 (I2C)  ·  SD Card (SPI1)  ·  Status LEDs  GP14/GP15',
        ha='center', color='#555', fontsize=9)

plt.tight_layout(pad=0.3)
plt.savefig('assets/breadboard.png', dpi=200, bbox_inches='tight',
            facecolor=fig.get_facecolor())
print("Saved assets/breadboard.png")
