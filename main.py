import sys
import argparse
from pathlib import Path
import re, yaml

from layout import Layout
from mtg import Downloader
from config import MTGProxyConfig

__version__ = "0.1.0"

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
        if not line or line.startswith("//") or line.startswith('#'):
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


def parse_arguments():
    """Parse and return command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="mtgproxy",
        description="Generate Magic: The Gathering proxy PDFs from deck files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py deck.yaml proxies.pdf
  python main.py -i deck.dec -o output.pdf --verbose
  python main.py --input ramp.yaml --output-dir ./pdfs/
        """.strip()
    )

    parser.add_argument(
        "-i", "--input",
        dest="deck_file",
        required=True,
        metavar="FILE",
        help="Input deck file (YAML or decklist format)"
    )

    parser.add_argument(
        "-o", "--output",
        dest="output_file",
        metavar="FILE",
        help="Output PDF file path (default: deck_name.pdf)"
    )

    parser.add_argument(
        "--output-dir",
        dest="output_dir",
        type=Path,
        default=Path.cwd(),
        metavar="DIR",
        help="Directory to save the PDF (default: current directory)"
    )

    parser.add_argument(
        "--config",
        dest="config_file",
        type=Path,
        metavar="FILE",
        help="Path to config file (searches ~/.config/mtgproxy/ and current dir if not specified)"
    )

    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable image caching (images will be re-downloaded each time)"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}"
    )

    return parser.parse_args()


def _print_header():
    """Print a friendly header."""
    print("\n" + "=" * 60)
    print("  mtgproxy - Magic: The Gathering Proxy Generator")
    print("=" * 60 + "\n")


def _print_step(step_num: int, total_steps: int, message: str):
    """Print a formatted step message."""
    print(f"[{step_num}/{total_steps}] {message}")


def _print_success(message: str):
    """Print a success message."""
    print(f"\n✓ {message}")


def _print_error(message: str):
    """Print an error message to stderr."""
    print(f"\n✗ Error: {message}", file=sys.stderr)


def main():
    """Main entry point for mtgproxy."""
    args = parse_arguments()

    _print_header()

    # Load configuration
    try:
        config = MTGProxyConfig.load(args.config_file)
        if args.config_file and args.verbose:
            print(f"📋 Config: {args.config_file}\n")
    except Exception as e:
        _print_error(f"Failed to load config: {e}")
        sys.exit(1)

    # Validate input file exists
    input_path = Path(args.deck_file)
    if not input_path.exists():
        _print_error(f"Deck file not found: {input_path}")
        sys.exit(1)

    # Determine output file
    # CLI --output-dir overrides config, otherwise use config's default_dir
    output_dir = args.output_dir if args.output_dir != Path.cwd() else config.output.default_dir

    if args.output_file:
        output_path = Path(args.output_file)
    else:
        # Default: use deck filename with .pdf extension in the output directory
        output_path = output_dir / input_path.stem
        output_path = output_path.with_suffix(".pdf")

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Show file info if verbose
    if args.verbose:
        print(f"📁 Input:  {input_path}")
        print(f"📄 Output: {output_path}\n")

    # Pipeline (4 steps total)
    TOTAL_STEPS = 4

    _print_step(1, TOTAL_STEPS, "Loading deck...")
    try:
        deck = load_deck(input_path)
    except Exception as e:
        _print_error(f"Failed to load deck: {e}")
        sys.exit(1)

    if args.verbose:
        print(f"   └─ {len(deck)} unique cards loaded\n")
    else:
        print()

    _print_step(2, TOTAL_STEPS, "Downloading card images...")
    try:
        downloader = Downloader(deck)
        downloaded = downloader.download_all()
    except Exception as e:
        _print_error(f"Failed to download cards: {e}")
        sys.exit(1)

    print()

    _print_step(3, TOTAL_STEPS, "Generating layout...")
    try:
        layout = Layout(downloaded, config=config.layout)
        layout._generate_pages()
    except Exception as e:
        _print_error(f"Failed to generate layout: {e}")
        sys.exit(1)

    print()

    _print_step(4, TOTAL_STEPS, "Saving PDF...")
    try:
        layout._save_pdf(output_path)
    except Exception as e:
        _print_error(f"Failed to save PDF: {e}")
        sys.exit(1)

    _print_success(f"PDF saved to {output_path}")


if __name__ == "__main__":
    main()