from pathlib import Path
from io import BytesIO
from time import perf_counter, sleep
import json, requests, urllib.parse as up
from PIL import Image
from tqdm import tqdm



HEADERS = {
    "User-Agent": "MTGProxyPrinter/0.1 (+https://github.com/chrisi5700/mtgproxy)",
    "Accept": "application/json;q=0.9,*/*;q=0.8",
}

CACHE_DIR = Path.home() / ".cache" / "mtgproxy"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

class Downloader:
    RATE = 10                 # max requests / second
    MIN_DELAY = 1 / RATE
    _last_call = 0.0

    def __init__(self, cards: dict[str, int]):
        self.cards = cards
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _throttle():
        dt = Downloader.MIN_DELAY - (perf_counter() - Downloader._last_call)
        if dt > 0:
            sleep(dt)

    @staticmethod
    def _cache_path(scry_id: str) -> Path:
        return CACHE_DIR / f"{scry_id}.png"

    # --------------------------------------------------------- public interface
    def download_all(self) -> list[tuple[Image.Image, int]]:
        """Returns [(PIL.Image, copies), …] ready for the Layout class."""
        # Try the /collection endpoint first (≤75 distinct cards)
        imgs: list[tuple[Image.Image, int]] = []
        for chunk in tqdm(_chunks(list(self.cards.items()), 75)):
            data = self._post_collection([name for name, _ in chunk])
            for card, (_, count) in zip(data, chunk):
                img = self._get_card_image(card)
                imgs.append((img, count))
        return imgs

    # ----------------------------------------------------------- implementation
    def _post_collection(self, names):
        identifiers = [{"name": n} for n in names]
        self._throttle()
        r = self.session.post(
            "https://api.scryfall.com/cards/collection",
            json={"identifiers": identifiers},
            timeout=15,
        )
        Downloader._last_call = perf_counter()
        r.raise_for_status()
        return r.json()["data"]

    def _get_card_image(self, card_json) -> Image.Image:
        sid = card_json["id"]
        cached = self._cache_path(sid)
        if cached.exists():
            return Image.open(cached).convert("RGB")

        # Locate an image URL (works for single- & multi-faced cards)
        try:
            url = card_json["image_uris"]["png"]
        except KeyError:
            url = card_json["card_faces"][0]["image_uris"]["png"]

        self._throttle()
        resp = self.session.get(url, timeout=20)
        Downloader._last_call = perf_counter()
        resp.raise_for_status()

        img = Image.open(BytesIO(resp.content)).convert("RGB")
        img.save(cached, "PNG", optimize=True)
        return img

# ------------------- utility --------------------------------------------------
def _chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i : i + n]

