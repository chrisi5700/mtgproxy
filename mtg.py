from pathlib import Path
from io import BytesIO
from time import perf_counter, sleep
import json, requests, urllib.parse as up
from PIL import Image
from tqdm import tqdm
from abc import ABC, abstractmethod
import logging

from logging_config import get_logger

logger = get_logger(__name__)



HEADERS = {
    "User-Agent": "MTGProxyPrinter/0.1 (+https://github.com/chrisi5700/mtgproxy)",
    "Accept": "application/json;q=0.9,*/*;q=0.8",
}

CACHE_DIR = Path.home() / ".cache" / "mtgproxy"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


class BaseScryfallFetcher(ABC):
    """Abstract base class for Scryfall API interaction with rate limiting and caching.

    Handles:
    - Rate limiting (10 requests/second max)
    - HTTP session management
    - Scryfall API headers

    Subclasses must implement:
    - _cache_path(): Return cache file path for a card ID
    """

    RATE = 10                 # max requests / second
    MIN_DELAY = 1 / RATE
    _last_call = 0.0

    def __init__(self):
        """Initialize Scryfall fetcher with rate-limited session."""
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    @staticmethod
    def _throttle():
        """Rate limiting to respect Scryfall API limits."""
        dt = BaseScryfallFetcher.MIN_DELAY - (perf_counter() - BaseScryfallFetcher._last_call)
        if dt > 0:
            sleep(dt)

    @staticmethod
    def _update_last_call():
        """Update the last call timestamp for rate limiting."""
        BaseScryfallFetcher._last_call = perf_counter()

    @abstractmethod
    def _cache_path(self, scry_id: str) -> Path:
        """Return the cache path for a card image. Must be implemented by subclass."""
        pass


class Downloader(BaseScryfallFetcher):
    """Download card images in high-quality PNG format for PDF generation.

    Features:
    - Handles multi-face cards (DFC, split, etc.)
    - PNG format (high quality)
    - Bulk collection queries for efficiency
    """

    def __init__(self, cards: dict[str, int]):
        """Initialize downloader with deck cards.

        Args:
            cards: Dictionary of {card_name: quantity}
        """
        super().__init__()
        self.cards = cards

    def _cache_path(self, scry_id: str) -> Path:
        """Return PNG cache path."""
        return CACHE_DIR / f"{scry_id}.png"

    # --------------------------------------------------------- public interface
    def download_all(self) -> list[tuple[Image.Image, int]]:
        """Download all card images from Scryfall with progress tracking.

        Returns:
            List of (Image, count) tuples for each card face
        """
        logger.info(f"Starting download of {len(self.cards)} unique cards")
        imgs: list[tuple[Image.Image, int]] = []

        card_list = list(self.cards.items())
        chunks_list = list(chunks(card_list, 75))

        for chunk_idx, chunk in enumerate(tqdm(chunks_list, desc="Downloading card chunks", unit="chunk"), 1):
            chunk_names = [name for name, _ in chunk]
            logger.debug(f"Downloading chunk {chunk_idx}/{len(chunks_list)}: {len(chunk)} cards")

            try:
                data = self._post_collection(chunk_names)
                for card_json, (card_name, count) in zip(data, chunk):
                    faces = self._get_card_images(card_json)
                    for face_img in faces:
                        imgs.append((face_img, count))
                    logger.debug(f"Downloaded {card_name} ({len(faces)} face(s))")
            except Exception as e:
                logger.error(f"Failed to download chunk {chunk_idx}: {e}")
                raise

        logger.info(f"Successfully downloaded {len(imgs)} card images")
        return imgs

    # ----------------------------------------------------------- implementation
    def _post_collection(self, names):
        """Query Scryfall API for multiple cards.

        Args:
            names: List of card names to query

        Returns:
            List of card JSON objects from Scryfall
        """
        identifiers = [{"name": n} for n in names]
        self._throttle()

        logger.debug(f"Querying Scryfall for {len(names)} cards")
        r = self.session.post(
            "https://api.scryfall.com/cards/collection",
            json={"identifiers": identifiers},
            timeout=15,
        )
        self._update_last_call()
        r.raise_for_status()

        data = r.json()
        if data['not_found']:
            not_found_names = [card['name'] for card in data['not_found']]
            logger.warning(f"Scryfall could not find {len(not_found_names)} cards: {not_found_names}")
            raise RuntimeError(f"Could not find these cards: {not_found_names}")

        logger.debug(f"Successfully queried {len(data['data'])} cards from Scryfall")
        return data["data"]

    def _get_card_images(self, card_json) -> list[Image.Image]:
        """Return every printable face (front & back) as PIL images.

        Handles multi-face cards (DFC, split, MDFC, etc.) by extracting
        images for each printable face.

        Args:
            card_json: Card JSON from Scryfall API

        Returns:
            List of PIL Image objects (one per printable face)
        """
        card_name = card_json.get("name", "Unknown")

        def _download(url: str, cache_id: str) -> Image.Image:
            """Download image from URL or use cached version."""
            cached = self._cache_path(cache_id)
            if cached.exists():
                logger.debug(f"Using cached image for {card_name}")
                return Image.open(cached).convert("RGB")

            logger.debug(f"Downloading image for {card_name}")
            self._throttle()
            r = self.session.get(url, timeout=20)
            self._update_last_call()
            r.raise_for_status()

            img = Image.open(BytesIO(r.content)).convert("RGB")
            img.save(cached, "PNG", optimize=True)
            logger.debug(f"Cached image for {card_name}")
            return img

        images: list[Image.Image] = []

        # 1️⃣ Prefer explicit faces if present (covers transform, MDFC, split, etc.)
        if faces := card_json.get("card_faces"):
            logger.debug(f"{card_name} has {len(faces)} faces")
            for idx, face in enumerate(faces):
                if "image_uris" not in face:
                    logger.debug(f"Skipping face {idx} of {card_name} (no image available)")
                    continue  # meld-backs, art cards …
                url = face["image_uris"]["png"]
                face_id = face.get("id", f"{card_json['id']}-{idx}")
                images.append(_download(url, face_id))

        # 2️⃣ Fallback to single-face object
        elif "image_uris" in card_json:
            logger.debug(f"{card_name} is single-faced")
            url = card_json["image_uris"]["png"]
            images.append(_download(url, card_json["id"]))

        # 3️⃣ Last-resort redirect (extremely rare)
        if not images:
            logger.warning(f"No image found for {card_name}, using fallback redirect")
            url = f"https://api.scryfall.com/cards/{card_json['id']}?format=image"
            images.append(_download(url, card_json["id"]))

        return images
# ------------------- utility --------------------------------------------------
def chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i : i + n]


class GUIImageFetcher(BaseScryfallFetcher):
    """Fetches card images in multiple formats for GUI display.

    Features:
    - Uses JPEG format (smaller than PNG for GUI preview)
    - Falls back: normal (488x680) → small (146x204) → border_crop
    - Separate cache from PDF images to avoid duplication
    """

    GUI_CACHE_DIR = Path.home() / ".cache" / "mtgproxy" / "gui_images"

    def __init__(self):
        """Initialize GUI image fetcher."""
        super().__init__()
        self.gui_cache_dir = self.GUI_CACHE_DIR
        self.gui_cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, scry_id: str) -> Path:
        """Get cache path for a card's JPEG image."""
        return self.gui_cache_dir / f"{scry_id}.jpg"

    def fetch_card_image(self, card_name: str) -> Image.Image | None:
        """Fetch a single card image for display in GUI (front face for DFCs).

        Handles multi-face cards (DFC, split, etc.) by using the front face.
        Attempts to fetch in this order:
        1. normal format (488x680)
        2. small format (146x204)
        3. border_crop format (as fallback)

        Args:
            card_name: Name of the card to fetch (preferably front face only for DFCs)

        Returns:
            PIL Image of the card, or None if not found or image unavailable
        """
        try:
            self._throttle()
            logger.debug(f"Fetching image for {card_name}")

            # Query Scryfall for the card
            response = self.session.get(
                "https://api.scryfall.com/cards/named",
                params={"exact": card_name},
                timeout=10
            )
            self._update_last_call()
            response.raise_for_status()

            card_json = response.json()

            # Determine which image_uris to use
            # 1️⃣ Prefer explicit faces if present (DFC, split, etc.) - use front face only
            image_uris = None
            if card_faces := card_json.get("card_faces"):
                # For GUI, only show front face
                if card_faces and "image_uris" in card_faces[0]:
                    image_uris = card_faces[0]["image_uris"]
                    card_id = card_faces[0].get("id", card_json.get("id", card_name))
                    logger.debug(f"{card_name} is multi-faced, using front face")
                # else: meld-backs, art cards, etc. - fall through to below

            # 2️⃣ Fallback to single-face object
            if not image_uris:
                image_uris = card_json.get("image_uris", {})
                card_id = card_json.get("id", card_name)

            # Try multiple formats in order of preference
            image_url = None
            for format_name in ["normal", "small", "border_crop"]:
                if image_uris.get(format_name):
                    image_url = image_uris[format_name]
                    logger.debug(f"Using {format_name} format for {card_name}")
                    break

            if not image_url:
                # No image available for this card
                logger.warning(f"No image available for {card_name}")
                return None

            # Check cache first
            cached = self._cache_path(card_id)
            if cached.exists():
                logger.debug(f"Using cached image for {card_name}")
                return Image.open(cached).convert("RGB")

            # Download the image
            logger.debug(f"Downloading image for {card_name}")
            self._throttle()
            img_response = self.session.get(image_url, timeout=20)
            self._update_last_call()
            img_response.raise_for_status()

            img = Image.open(BytesIO(img_response.content)).convert("RGB")
            img.save(cached, "JPEG", quality=85, optimize=True)
            logger.debug(f"Cached image for {card_name}")
            return img

        except Exception as e:
            logger.error(f"Failed to fetch image for {card_name}: {e}")
            return None

