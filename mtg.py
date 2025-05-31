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
        imgs: list[tuple[Image.Image, int]] = []
        for chunk in tqdm(chunks(list(self.cards.items()), 75)):
            data = self._post_collection([name for name, _ in chunk])
            for card_json, (_, count) in zip(data, chunk):
                for face_img in self._get_card_images(card_json):
                    imgs.append((face_img, count))
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
        if r.json()['not_found']:
            raise RuntimeError(f"Could not find these cards: {[card['name'] for card in r.json()['not_found']]}")
        return r.json()["data"]

    def _get_card_images(self, card_json) -> list[Image.Image]:
        """Return every printable face (front & back) as PIL images."""
        def _download(url: str, cache_id: str) -> Image.Image:
            cached = self._cache_path(cache_id)
            if cached.exists():
                return Image.open(cached).convert("RGB")

            self._throttle()
            r = self.session.get(url, timeout=20)
            Downloader._last_call = perf_counter()
            r.raise_for_status()

            img = Image.open(BytesIO(r.content)).convert("RGB")
            img.save(cached, "PNG", optimize=True)
            return img

        images: list[Image.Image] = []

        # 1️⃣ Prefer explicit faces if present (covers transform, MDFC, split, etc.)
        if faces := card_json.get("card_faces"):
            for idx, face in enumerate(faces):
                if "image_uris" not in face:
                    continue  # meld-backs, art cards …
                url = face["image_uris"]["png"]
                face_id = face.get("id", f"{card_json['id']}-{idx}")
                images.append(_download(url, face_id))

        # 2️⃣ Fallback to single-face object
        elif "image_uris" in card_json:
            url = card_json["image_uris"]["png"]
            images.append(_download(url, card_json["id"]))

        # 3️⃣ Last-resort redirect (extremely rare)
        if not images:
            url = f"https://api.scryfall.com/cards/{card_json['id']}?format=image"
            images.append(_download(url, card_json["id"]))

        return images
# ------------------- utility --------------------------------------------------
def chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i : i + n]

