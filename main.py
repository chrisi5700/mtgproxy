import sys
import argparse
import logging
from pathlib import Path

from layout import Layout
from mtg import Downloader
from config import MTGProxyConfig
from deck_loader import load_deck
from logging_config import setup_logging, get_logger

__version__ = "0.1.0"

# Initialize logging
_logger = get_logger(__name__)


def parse_arguments():
    """Parse and return command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="mtgproxy",
        description="Generate Magic: The Gathering proxy PDFs from deck files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --gui                                  # Launch GUI
  python main.py -i deck.yaml -o proxies.pdf           # CLI mode
  python main.py -i deck.dec -o output.pdf --verbose   # CLI with verbose
  python main.py --input ramp.yaml --output-dir ./pdfs/ # Custom output dir
        """.strip()
    )

    parser.add_argument(
        "--gui",
        action="store_true",
        help="Launch the graphical user interface"
    )

    parser.add_argument(
        "-i", "--input",
        dest="deck_file",
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


def run_cli(args):
    """Execute CLI mode: generate PDF from deck file."""
    # Validate required argument for CLI
    if not args.deck_file:
        _print_error("CLI mode requires --input (deck file). Use --gui for GUI mode.")
        sys.exit(1)

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


def run_gui():
    """Launch the graphical user interface."""
    try:
        from gui.main_window import MTGProxyGUI
        from PyQt6.QtWidgets import QApplication

        app = QApplication(sys.argv)
        gui = MTGProxyGUI()
        gui.show()
        sys.exit(app.exec())
    except ImportError as e:
        _print_error(f"GUI dependencies not installed: {e}")
        print("Install PyQt6 to use GUI: pip install PyQt6 PyQt6-WebEngine rapidfuzz")
        sys.exit(1)
    except Exception as e:
        _print_error(f"Failed to launch GUI: {e}")
        sys.exit(1)


def main():
    """Main entry point for mtgproxy - routes to CLI or GUI."""
    args = parse_arguments()

    # Set up logging based on verbosity
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(log_level=log_level)

    _logger.info(f"mtgproxy v{__version__} started")
    _logger.debug(f"Verbose logging enabled")

    if args.gui:
        _logger.info("Launching GUI mode")
        run_gui()
    else:
        _logger.info("Running CLI mode")
        run_cli(args)


if __name__ == "__main__":
    main()