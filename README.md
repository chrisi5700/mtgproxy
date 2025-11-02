# MTG Proxy Printer

A **Python tool** that turns a deck into a crisp, print-ready PDF of Magic: The Gathering card proxies. Choose between a **powerful GUI** for interactive deck building, or a **fast CLI** for automation. Downloads card images from Scryfall, arranges them six per A4 page at true size, and writes a high-resolution PDF you can send straight to your printer.

---

## Features

### Both GUI & CLI Modes

* **GUI mode** (`--gui`) - Build decks interactively with live previews
* **CLI mode** - Automated PDF generation from deck files
* **Two deck input formats**
  * YAML (human-friendly, comment-friendly)
  * Classic `*.dec` / `*.txt` decklists (`12 Birds of Paradise`)
  * GUI: Type card names with smart autocomplete suggestions

### Core Features

* **Card name autocomplete** - Fuzzy search powered by rapidfuzz (handles typos, symbols, long names)
* **Live card preview** - See card images as you add them (GUI)
* **Async card downloading** - Download images in background as you build your deck (GUI)
* **Multi-face support** - Transforming-DFC, split, adventure, etc. Each face is downloaded and placed in the layout.
* **300 DPI true-scale layout** - Six cards on portrait A4 with crop-friendly spacing.
* **On-disk image cache** (`~/.cache/mtgproxy`) so repeat runs are instant and API-friendly.
* **Polite Scryfall usage** - Custom `User-Agent`, keep-alive `Session`, < 10 requests/sec.
* **Dark mode UI** - Eye-friendly GUI with modern dark theme (PyQt6)
* **PDF preview** - View generated PDFs directly in the GUI before saving
* **Configurable layout** - Adjust card dimensions, gaps, margins, and DPI in settings

---

## Requirements

* Python >= 3.9
* For GUI: `PyQt6`, `PyQt6-WebEngine`
* For card search: `rapidfuzz`
* Core: `requests`, `Pillow`, `PyYAML`, `tqdm`, `pydantic`

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## Quick Start

### GUI Mode (Recommended for deck building)

```bash
python main.py --gui
```

Features:
- Search for cards by name with fuzzy autocomplete
- Add cards and see thumbnails as you build
- Adjust quantity sliders
- Load existing deck files
- Preview the generated PDF before saving
- Customize layout settings (card size, margins, gaps)
- Save PDFs with one click

### CLI Mode (For automation & scripting)

```bash
python main.py -i deck.yaml -o proxies.pdf
```

Or with explicit arguments:

```bash
python main.py --input ramp.dec --output output.pdf --verbose
```

**CLI Arguments:**

```
--gui                  Launch the graphical user interface
-i, --input FILE       Input deck file (YAML or decklist format)
-o, --output FILE      Output PDF file path (default: deck_name.pdf)
--output-dir DIR       Directory to save the PDF (default: current directory)
--config FILE          Path to config file (searches ~/.config/mtgproxy/ and current dir)
--no-cache             Disable image caching (images will be re-downloaded each time)
-v, --verbose          Enable verbose output
--version              Show version number
```

---

## Deck Formats

### YAML (`*.yml`, `*.yaml`)

Scalar counts or full mappings are accepted - only `count` is mandatory; any other keys are ignored.

```yaml
# ramp_agro.yaml
burgeoning: 4
birds of paradise: 4
cultivate: 4
rampant growth: 4
ancient stirrings: 4
collected company: 4
craterhoof behemoth: 2
questing beast: 3
scavenging ooze: 2
steel leaf champion: 4

# Transforming DFC - full name works fine
brutal cathar // moonrage brute: 4

# Split card
wear // tear: 3

# Mapping style with extra metadata (ignored by loader)
primordial hydra:
  count: 2
  finish: foil
  set: m12

thrun, the last troll:
  count: 2
  finish: etched
  set: kald

# Lands
forest: 21
nykthos, shrine to nyx: 3
```

### Decklist / .dec (`*.txt`, `*.dec`, anything else)

```text
4 Burgeoning
4 Birds of Paradise
4 Cultivate
4 Rampant Growth
4 Ancient Stirrings
4 Collected Company
2 Craterhoof Behemoth
3 Questing Beast
2 Scavenging Ooze
4 Steel Leaf Champion
4 Brutal Cathar // Moonrage Brute
3 Wear // Tear
2 Primordial Hydra
4 Unholy Annex/Ritual Chamber
2 Thrun, the Last Troll
21 Forest
3 Nykthos, Shrine to Nyx

// Sideboard:

SB: 2 Ghost Vacuum
SB: 2 Obstinate Baloth
SB: 2 The Stone Brain
SB: 1 Aclazotz, Deepest Betrayal
SB: 1 Anoint with Affliction
```

Comments (starting with `#` or `//`) and blank lines are ignored by the parser.

---

## Output Layout

* Portrait A4 (2480 x 3508 px @ 300 DPI)
* Cards placed in two columns x three rows (6 per page)
* Card face PNGs are resized to 751 x 1051 px (official 63.5 x 88.9 mm)
* New pages are added automatically when the sheet is full
* Fully configurable: card size, gaps, margins

> Need crop marks, duplex backs or US-Letter? Open the Settings panel in the GUI or edit the config file!

---

## Configuration

Configuration is stored in `mtgproxy.yaml` in the project directory, `~/.config/mtgproxy/mtgproxy.yaml`, or `~/.mtgproxy.yaml`.

Example config:

```yaml
layout:
  dpi: 300
  card_width_mm: 63.5
  card_height_mm: 88.9
  gap_mm: 0.25
  top_margin_mm: 5

output:
  default_dir: ~/mtgproxy_pdfs
```

You can also edit these settings through the GUI's Settings tab!

---

## Building Standalone Executables

### On Linux/macOS:

```bash
bash build.sh
```

Executable will be in `dist/mtgproxy`

### On Windows:

```cmd
build.bat
```

Executable will be in `dist\mtgproxy.exe`

### Manual build:

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name mtgproxy \
    --hidden-import=PyQt6.QtCore \
    --hidden-import=PyQt6.QtGui \
    --hidden-import=PyQt6.QtWidgets \
    --hidden-import=PyQt6.QtWebEngineWidgets \
    --hidden-import=rapidfuzz \
    --hidden-import=yaml \
    main.py
```

---

## Architecture

```
mtgproxy/
├── main.py              # CLI/GUI router
├── mtg.py               # Scryfall downloader
├── config.py            # Configuration management
├── layout.py            # PDF layout engine
├── card_db.py           # Card database with fuzzy search
├── gui/
│   ├── main_window.py   # Main GUI window
│   ├── deck_builder.py  # Deck input panel
│   ├── pdf_viewer.py    # PDF preview panel
│   ├── config_panel.py  # Settings panel
│   └── styles.py        # Dark theme stylesheet
├── build.sh             # Linux/macOS build script
└── build.bat            # Windows build script
```

---

## Future Plans

* Card image caching improvements
* Printing directly from the GUI
* Custom back designs
* Batch operations
* Export to other formats

---

## License

MIT. Scryfall images are © Wizards of the Coast and are provided for personal use under Scryfall's [image policy](https://scryfall.com/docs/api/images).

---

Happy brewing and printing!
