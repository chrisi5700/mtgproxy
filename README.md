# MTG Proxy Printer

A **command‑line Python tool** that turns a text decklist into a crisp, print‑ready PDF of Magic: The Gathering card proxies.  It downloads card images from Scryfall, arranges them six per A4 page at true size, and writes a high‑resolution PDF you can send straight to your printer.

---

## Features

* **Two deck formats** out‑of‑the‑box

  * YAML (human‑friendly, comment‑friendly)
  * Classic `*.dec` / `*.txt` decklists (`12 Birds of Paradise`)
* **Multi‑face support** – transforming‑DFC, split, adventure, etc. Each face is downloaded and placed in the layout.
* **300 DPI true‑scale layout** – six cards on portrait A4 with crop‑friendly spacing.
* **On‑disk image cache** (`~/.cache/mtgproxy`) so repeat runs are instant and API‑friendly.
* **Polite Scryfall usage** – custom `User‑Agent`, keep‑alive `Session`, < 10 requests/sec.

---

## Requirements

* Python ≥ 3.9
* `requests`, `Pillow`, `PyYAML`, `tqdm`

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## Usage

```bash
python make_proxies.py <input deck file> <output pdf>
```

Example:

```bash
python make_proxies.py ramp_agro.yaml proxies.pdf
```

* **First argument** – path to a deck file in YAML or decklist text format.
* **Second argument** – output PDF file name.

Under the hood the script:

1. **Loads** the deck file → `dict[str, int]` (`load_deck`).
2. **Downloads** all required images (with caching & rate‑limiting).
3. **Generates** page layouts (`Layout` class).
4. **Saves** a multi‑page PDF at 300 DPI.

---

## Deck formats

### YAML (`*.yml`, `*.yaml`)

Scalar counts or full mappings are accepted – only `count` is mandatory; any other keys are ignored.

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

# Transforming DFC – full name works fine
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
2 Thrun, the Last Troll
21 Forest
3 Nykthos, Shrine to Nyx
```

*Comments* (starting with `#` or `//`) and blank lines are ignored by the parser.

---

## Output layout

* Portrait A4 (2480 × 3508 px @ 300 DPI).
* Cards placed in two columns × three rows (6 per page).
* Card face PNGs are resized to 751 × 1051 px (official 63.5 × 88.9 mm).
* New pages are added automatically when the sheet is full.

> Need crop marks, duplex backs or US‑Letter?  Open an issue or send a PR – the `Layout` class is easy to tweak.

---

## Script entry‑point

```python
if __name__ == "__main__":
    print("Loading Deck…")
    deck = load_deck(sys.argv[1])

    print("Downloading Cards…")
    downloader = Downloader(deck)
    downloaded = downloader.download_all()

    print("Generating Layout…")
    layout = Layout(downloaded)
    layout.generate_pages()

    print("Writing PDF…")
    layout.save_pdf(sys.argv[2])
```

---

## Licence

MIT.  Scryfall images are © Wizards of the Coast and are provided for personal use under Scryfall’s [image policy](https://scryfall.com/docs/api/images).

---

Happy brewing and printing!
