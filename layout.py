from PIL import Image
from PIL.Image import Resampling
from tqdm import tqdm
from config import LayoutConfig
import logging

from logging_config import get_logger

logger = get_logger(__name__)

"""
A4 Size: 210 mm x 297 mm
MTG Size: 63.5 mm x 88.9 mm
210 / 63.5 = 3.3
297 / 88.9 = 3.3



MTG Original Pixels: 745 x 1040


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

        # Calculate dimensions from config (using percentage-based card size)
        self.dpi = config.dpi
        self.card_w_mm = config.get_card_width_mm()
        self.card_h_mm = config.get_card_height_mm()
        self.gap_mm = config.gap_mm
        self.top_margin_mm = config.top_margin_mm
        self.side_margin_mm = config.side_margin_mm

        # Convert mm to pixels based on DPI
        self.mtg_w = int(self.card_w_mm / self.MM_PER_INCH * self.dpi)
        self.mtg_h = int(self.card_h_mm / self.MM_PER_INCH * self.dpi)
        self.gap_px = int(self.gap_mm / self.MM_PER_INCH * self.dpi)
        self.top_margin_px = int(self.top_margin_mm / self.MM_PER_INCH * self.dpi)
        self.side_margin_px = int(self.side_margin_mm / self.MM_PER_INCH * self.dpi)
        self.page_w = int(self.A4_W_MM / self.MM_PER_INCH * self.dpi)
        self.page_h = int(self.A4_H_MM / self.MM_PER_INCH * self.dpi)

        self.a4_dimensions = (self.page_w, self.page_h)
        self.mtg_dimensions = (self.mtg_w, self.mtg_h)

        self.pages = [self._create_a4()]

        logger.info(f"Layout initialized: {len(images)} images, card size {self.card_w_mm:.1f}x{self.card_h_mm:.1f}mm, {self.dpi} DPI")

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
        """Generate A4 pages by arranging card images in grid layout.

        Places cards in rows and columns, respecting margins and gaps.
        Creates new pages as needed.
        """
        logger.info(f"Generating pages for {self._count_total_cards()} cards")
        pos = [self.side_margin_px, self.top_margin_px]
        card_count = 0

        for img in tqdm(self._get_images(), desc="Laying out cards on pages", unit="card"):
            card_count += 1

            if pos[0] + self.mtg_w > self.page_w - self.side_margin_px:  # No more space horizontally
                pos[0] = self.side_margin_px                # Move to the beginning with side margin
                pos[1] += self.mtg_h + self.gap_px          # Add another row
            if pos[1] + self.mtg_h > self.page_h:          # No more space vertically
                self.pages.append(self._create_a4())        # Create a new page
                logger.debug(f"Created page {len(self.pages)}")
                pos = [self.side_margin_px, self.top_margin_px]  # Draw on that page with margins

            self.pages[-1].paste(img, (pos[0], pos[1]))
            pos[0] += self.mtg_w + self.gap_px

        logger.info(f"Generated {len(self.pages)} page(s) with {card_count} card(s)")
        return self

    def _count_total_cards(self) -> int:
        """Count total number of card instances (including duplicates)."""
        return sum(count for _, count in self.images)

    def _save_pdf(self, path="output/cards.pdf"):
        """Save all pages to a PDF file.

        Args:
            path: Output PDF file path
        """
        logger.info(f"Saving PDF to {path}")
        self.pages[0].save(
            path, "PDF", resolution=self.dpi, save_all=True, append_images=self.pages[1:]
        )
        logger.info(f"PDF saved successfully: {path}")

    def generate_pdf(self, path="output/cards.pdf"):
        """Generate and save complete PDF in one operation.

        Args:
            path: Output PDF file path
        """
        logger.info(f"Starting PDF generation: {path}")
        self._generate_pages()._save_pdf(path)
        logger.info(f"PDF generation complete")
