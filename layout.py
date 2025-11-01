from PIL import Image
from PIL.Image import Resampling
from tqdm import tqdm

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
    DPI = 300
    CARD_W_MM, CARD_H_MM = 63.5, 88.9  # official MTG dimensions
    A4_W_MM, A4_H_MM = 210, 297
    GAP_MM = 0.25  # tiny gap between cards for cutting
    TOP_MARGIN_MM = 5  # 0.5cm top margin for printer

    MTG_W = int(CARD_W_MM / MM_PER_INCH * DPI)  # ≈ 751 px
    MTG_H = int(CARD_H_MM / MM_PER_INCH * DPI)  # ≈ 1051 px
    GAP_PX = int(GAP_MM / MM_PER_INCH * DPI)  # ≈ 6 px
    TOP_MARGIN_PX = int(TOP_MARGIN_MM / MM_PER_INCH * DPI)  # ≈ 59 px
    PAGE_W = int(A4_W_MM / MM_PER_INCH * DPI)  # ≈ 2480 px
    PAGE_H = int(A4_H_MM / MM_PER_INCH * DPI)  # ≈ 3508 px

    A4_DIMENSIONS = (PAGE_W, PAGE_H)
    MTG_DIMENSIONS = (MTG_W, MTG_H)

    def __init__(self, images: list[tuple[Image.Image, int]]):
        self.images = images
        self.pages = [self._create_a4()]

    @staticmethod
    def _create_a4():
        return Image.new('RGB',
                  Layout.A4_DIMENSIONS,
                  (255, 255, 255))  # White

    @staticmethod
    def _resize_image(img: Image.Image):
        return img.resize(Layout.MTG_DIMENSIONS, Resampling.LANCZOS)



    def _get_images(self):
        for img, count in self.images:
            img = self._resize_image(img)
            for _ in range(count):
                yield img


    def _generate_pages(self):
        pos = [0, Layout.TOP_MARGIN_PX]
        for img in tqdm(self._get_images()):
            if pos[0] + Layout.MTG_W > Layout.PAGE_W: # No more space to the horizontally
                pos[0] = 0                          # Move to the beginning
                pos[1] += Layout.MTG_H + Layout.GAP_PX # Add another row
            if pos[1] + Layout.MTG_H > Layout.PAGE_H:    # No more space vertically
                self.pages.append(self._create_a4()) # Create a new page
                pos = [0, Layout.TOP_MARGIN_PX]     # Draw on that page with top margin
            self.pages[-1].paste(img, (pos[0], pos[1]))
            pos[0] += Layout.MTG_W + Layout.GAP_PX
        return self

    def _save_pdf(self, path="output/cards.pdf"):
        self.pages[0].save(
            path, "PDF", resolution=Layout.DPI, save_all=True, append_images=self.pages[1:]
        )

    def generate_pdf(self, path="output/cards.pdf"):
        self._generate_pages()._save_pdf(path)
