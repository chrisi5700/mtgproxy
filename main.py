from time import sleep

from mtg import Downloader
from layout import Layout


def load_cards(file_name: str):
    with open(file_name, mode='r') as file:
        return {line.split()[0]: int(line.split()[1]) for line in file}


def main():
    cards = load_cards("cards.txt")
    downloader = Downloader(cards)
    images = downloader.download_all()
    layout_generator = Layout(images)
    layout_generator.generate_pages()
    layout_generator.save_pdf()


if __name__ == "__main__":
    main()
