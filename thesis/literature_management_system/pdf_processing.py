import pdftotext
from wand.image import Image
from PIL import Image as PI
import pyocr
import pyocr.builders
import io
import re

class PDFScorer:

    def __init__(self, pdf_path=None, ocr_threshold=1000, use_ocr=True):
        self.path = None
        self.ocr_threshold = ocr_threshold
        self.raw_pages = None
        self.clean_pages = None
        self.ocr = False
        self.use_ocr = use_ocr

        if pdf_path is not None:
            self.load_pdf(pdf_path)

    def load_pdf(self, path):
        self.path = path

    def get_pages(self):
        if self.raw_pages is None:
            self.compute_pdf_text()
        return len(self.raw_pages)

    def get_raw_text(self, pages=None):
        if self.raw_pages is None:
            self.compute_pdf_text()
        if pages is None:
            pages = range(len(self.raw_pages))
        return "\n".join([self.raw_pages[i] for i in pages])

    def get_clean_text(self, pages=None):
        if self.clean_pages is None:
            self.compute_clean_pages()
        if pages is None:
            pages = range(len(self.clean_pages))
        return "".join([self.clean_pages[i] for i in pages])

    def compute_clean_pages(self, lower=True):
        if self.raw_pages is None:
            self.compute_pdf_text()
        if lower:
            clean_pages = [re.sub(r"[\W_]+", "", i) for i in self.raw_pages]
        else:
            clean_pages = [re.sub(r"[\W_]+", "", i).lower() for i in self.raw_pages]
        self.clean_pages = clean_pages

    def compute_pdf_text(self):
        self.compute_pdf_text_normal()
        if len("".join(self.raw_pages)) < self.ocr_threshold:
            self.ocr = True
            if self.use_ocr:
                self.compute_pdf_text_ocr()

    def compute_pdf_text_normal(self):
        with open(self.path, "rb") as f:
            pages = pdftotext.PDF(f)
            self.raw_pages = pages

    def compute_pdf_text_ocr(self):
        tool = pyocr.get_available_tools()[0]
        lang = tool.get_available_languages()[1]

        req_image = []
        final_text = []

        image_pdf = Image(filename=self.path, resolution=300)
        image_jpeg = image_pdf.convert('jpeg')
        for img in image_jpeg.sequence:
            img_page = Image(image=img)
            req_image.append(img_page.make_blob('jpeg'))

        for img in req_image:
            txt = tool.image_to_string(
                PI.open(io.BytesIO(img)),
                lang=lang,
                builder=pyocr.builders.TextBuilder()
            )
            final_text.append(txt)
        self.raw_pages = final_text

    def count_keywords(self, keywords, pages=None):
        return self.count_text_keywords(self.get_clean_text(pages), keywords)

    @staticmethod
    def count_text_keywords(text, keywords):
        count = {}
        for k in keywords:
            count[k] = text.count(k)
        return count