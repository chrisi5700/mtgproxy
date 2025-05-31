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
        card = card.split("//", 1)[0].strip() # get only first card name
        if isinstance(value, int):
            deck[card] = value
        elif isinstance(value, dict) and "count" in value:
            deck[card] = int(value["count"])
        else:
            raise ValueError(f"Can't deduce count for card '{card}'.")
    return deck


# ────────────────────────────────────────── TEXT list  → {card: count, …}
def load_decklist(path: str | Path) -> dict[str, int]:
    """Parse classic '.dec' / '.txt' decklists ( '12 Burgeoning' )."""
    deck: dict[str, int] = {}
    for raw in Path(path).read_text().splitlines():
        # strip line-end comments starting with '#' or '//'
        line = raw.split('#', 1)[0].split('//', 1)[0]
        if not line.strip():
            continue
        m = DECKLINE_RE.match(line)
        if not m:
            raise ValueError(f"Unrecognised deck line: {raw!r}")
        cnt, name = int(m.group(1)), m.group(2).split("//", 1)[0].strip() # get only first card name
        deck[name] = deck.get(name, 0) + cnt
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