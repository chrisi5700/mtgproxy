import sys
from pathlib import Path
import re, yaml

from layout import Layout
from mtg import Downloader

# ──────────────────────────────────────────────────────────── REGEX FOR LINES
# matches:  3 Birds of Paradise
#           4x Brutal Cathar
# (ignores leading/trailing spaces and accepts a literal "x")
DECKLINE_RE = re.compile(r'^\s*(\d+)[xX]?\s+(.+?)\s*$')

def _front_name(card_name: str) -> str:
    """Return the front-face name for any multi-face card.

    Splits on:
      • ' // '  (modal DFC, split cards)
      • '/'     (mtgdecks.net export e.g. Unholy Annex/Ritual Chamber)
    """
    for delim in ("//", "/"):
        if delim in card_name:
            return card_name.split(delim, 1)[0].strip()
    return card_name.strip()

# ────────────────────────────────────────────── YAML  → {card: count, …}
def load_yaml_deck(path: str | Path) -> dict[str, int]:
    """Read a YAML deck into {card name: count}.

    Examples of valid YAML:
      # simplest
      burgeoning: 12

      # with extra metadata the loader quietly ignores
      brutal cathar:
        count: 4
        finish: foil
    """
    data = yaml.safe_load(Path(path).read_text())
    if not isinstance(data, dict):
        raise ValueError("Top-level YAML must be a mapping of card → value.")

    deck: dict[str, int] = {}
    for card, value in data.items():
        card = _front_name(card)
        if isinstance(value, int):
            deck[card] = value
        elif isinstance(value, dict) and "count" in value:
            deck[card] = int(value["count"])
        else:
            raise ValueError(f"Can't deduce count for card '{card}'.")
    return deck


# ────────────────────────────────────────── TEXT list  → {card: count, …}
def load_decklist(path: str | Path) -> dict[str, int]:
    """Parse classic decklists or mtgdecks.net export format."""
    deck: dict[str, int] = {}
    for raw in Path(path).read_text().splitlines():
        line = raw.strip()

        # 1. Ignore comment or header lines
        if not line or line.startswith("//"):
            continue

        # 2. Handle sideboard lines (strip `SB:` prefix)
        if line.startswith("SB:"):
            line = line[3:].strip()

        # 3. Try matching a card line: e.g., `4 Birds of Paradise`
        m = DECKLINE_RE.match(line)
        if not m:
            raise ValueError(f"Unrecognised deck line: {raw!r}")

        count = int(m.group(1))
        name = m.group(2).strip()

        # Optional: drop the `//` in names (e.g., `Unholy Annex/Ritual Chamber`)
        name = _front_name(name)

        deck[name] = deck.get(name, 0) + count

    return deck


# ────────────────────────────────────────── Dispatch by file extension
def load_deck(path: str | Path) -> dict[str, int]:
    """Smart loader: YAML if suffix is .yml/.yaml, else decklist text."""
    path = Path(path)
    if path.suffix.lower() in {".yml", ".yaml"}:
        return load_yaml_deck(path)
    return load_decklist(path)


if __name__ == "__main__":
    print("Loading Deck...")
    deck = load_deck(sys.argv[1])
    print("Downloading Cards...")
    downloader = Downloader(deck)
    downloaded = downloader.download_all()
    print("Generating Layout...")
    layout = Layout(downloaded)
    layout._generate_pages()
    layout._save_pdf(sys.argv[2])