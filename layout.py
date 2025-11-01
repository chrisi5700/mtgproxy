from PIL import Image
from PIL.Image import Resampling
from tqdm import tqdm
from config import LayoutConfig

"""
A4 Size: 210 mm x 297 mm
MTG Size: 63.5 mm x 88.9 mm
210 / 63.5 = 3.3
297 / 88.9 = 3.3



MTG Original Pixels: 745 × 1040


A4 Pixels: 595 x 842
MTG Correct Pixels: 179.91 x 252.03
"""

class Layout:
    MM_PER_INCH = 25.4
    A4_W_MM, A4_H_MM = 210, 297  # Standard A4 dimensions

    def __init__(self, images: list[tuple[Image.Image, int]], config: LayoutConfig = None):
        """Initialize Layout with images and optional configuration.

        Args:
            images: List of (Image, count) tuples
            config: LayoutConfig instance (uses defaults if not provided)
        """
        if config is None:
            config = LayoutConfig()

        self.images = images
        self.config = config

        # Calculate dimensions from config
        self.dpi = config.dpi
        self.card_w_mm = config.card_width_mm
        self.card_h_mm = config.card_height_mm
        self.gap_mm = config.gap_mm
        self.top_margin_mm = config.top_margin_mm

        # Convert mm to pixels based on DPI
        self.mtg_w = int(self.card_w_mm / self.MM_PER_INCH * self.dpi)
        self.mtg_h = int(self.card_h_mm / self.MM_PER_INCH * self.dpi)
        self.gap_px = int(self.gap_mm / self.MM_PER_INCH * self.dpi)
        self.top_margin_px = int(self.top_margin_mm / self.MM_PER_INCH * self.dpi)
        self.page_w = int(self.A4_W_MM / self.MM_PER_INCH * self.dpi)
        self.page_h = int(self.A4_H_MM / self.MM_PER_INCH * self.dpi)

        self.a4_dimensions = (self.page_w, self.page_h)
        self.mtg_dimensions = (self.mtg_w, self.mtg_h)

        self.pages = [self._create_a4()]

    def _create_a4(self):
        return Image.new('RGB',
                  self.a4_dimensions,
                  (255, 255, 255))  # White

    def _resize_image(self, img: Image.Image):
        return img.resize(self.mtg_dimensions, Resampling.LANCZOS)



    def _get_images(self):
        for img, count in self.images:
            img = self._resize_image(img)
            for _ in range(count):
                yield img


    def _generate_pages(self):
        pos = [0, self.top_margin_px]
        for img in tqdm(self._get_images()):
            if pos[0] + self.mtg_w > self.page_w:  # No more space horizontally
                pos[0] = 0                          # Move to the beginning
                pos[1] += self.mtg_h + self.gap_px  # Add another row
            if pos[1] + self.mtg_h > self.page_h:  # No more space vertically
                self.pages.append(self._create_a4())  # Create a new page
                pos = [0, self.top_margin_px]       # Draw on that page with top margin
            self.pages[-1].paste(img, (pos[0], pos[1]))
            pos[0] += self.mtg_w + self.gap_px
        return self

    def _save_pdf(self, path="output/cards.pdf"):
        self.pages[0].save(
            path, "PDF", resolution=self.dpi, save_all=True, append_images=self.pages[1:]
        )

    def generate_pdf(self, path="output/cards.pdf"):
        self._generate_pages()._save_pdf(path)
