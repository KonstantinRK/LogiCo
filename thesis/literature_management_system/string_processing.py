from fuzzywuzzy import fuzz
import numpy as np
from sklearn.linear_model import LogisticRegression
import csv
import pickle
import pdftotext
from wand.image import Image
from PIL import Image as PI
import pyocr
import pyocr.builders
import io
import re
import os


class StringClassifier:

    def __init__(self, model_path=None, data_path=None, learn=False, learn_from_weak=True):
        self.model_path = model_path
        self.data_path = data_path
        self.learn_from_weak = learn_from_weak
        self.learn = learn if self.data_path is None else False
        self.classifier = None
        self.model = self.default_model

        if model_path is not None and os.path.exists(model_path):
            with open(model_path, "rb") as f:
                self.classifier = pickle.load(f)
        else:
            self.classifier = None

        if self.classifier is None:
            self.model = self.strong_trivial_model
        else:
            self.model = self.learned_model

    def set_classifier(self):
        if self.classifier is None:
            if self.model_path is not None and self.data_path is not None and os.path.exists(self.model_path):
                self.learn_classifier()

    def set_model(self, model):
        if model == "very-strong":
            self.model = self.very_strong_trivial_model
        elif model == "strong":
            self.model = self.strong_trivial_model
        elif model == "learn" and self.model_path is not None:
            self.model = self.learned_model
        else:
            self.model = self.weak_trivial_model

    def equal(self, s1, s2, learn=False):
        if learn:
            values = np.array(self.equal_array(s1, s2)).reshape(1, -1)
            if self.learn_from_weak:
                decision = self.weak_trivial_model(values)
            else:
                decision = self.model(values)
            self.learn_decision(s1, s2, values, decision)
        else:
            return self.model(self.equal_array(s1, s2))

    def equal_array(self, s1, s2):
        s1 = self.preprocess_string(s1)
        s2 = self.preprocess_string(s2)
        return [fuzz.ratio(s1, s2) / 100, fuzz.partial_ratio(s1, s2) / 100,
                fuzz.token_sort_ratio(s1, s2) / 100, fuzz.token_set_ratio(s1, s2) / 100]

    def learn_decision(self, s1, s2, values, decision):
        if self.data_path is not None:
            with open(self.data_path, "a") as f:
                writer = csv.writer(f)
                if decision and not (values[0] == 1 and values[1] == 1 and values[2] == 1 and values[3] == 1):
                    print("{2} |  {0}   ==   {1}".format(s1, s2, repr(values)))
                    equal = input("y / [n]:").strip()
                    if "y" == equal:
                        decision = True
                    else:
                        decision = False
                writer.writerow(values + [int(decision)])

    def learn_classifier(self):
        if self.data_path is not None:
            if not os.path.exists(self.data_path):
                with open(self.data_path, "w") as f:
                    f.write("")
            with open(self.data_path, "r") as f:
                # [ratio, partial_ratio, token_sort, token_set]
                data = list(csv.reader(f))
            x = np.array([i[:-1] for i in data])
            y = np.array([i[-1] for i in data])
            model = LogisticRegression().fit(x, y)
            with open(self.data_path, "wb") as f:
                pickle.dump(model, f)
            self.classifier = model

    def learned_model(self, x):
        if self.classifier is not None:
            if self.classifier.predict(x)[0] == '0':
                return False
            else:
                return True
        else:
            return None

    def contains_duplicates(self, input_list, learn=True, index=False):
        check_list = [True]*len(input_list)
        duplicates = []
        for i in range(len(input_list)):
            if check_list[i]:
                s1 = input_list[i]
                if index:
                    s1_duplicates = [(i, s1)]
                else:
                    s1_duplicates = [s1]
                for j in range(i+1, len(input_list)):
                    s2 = input_list[j]
                    if self.equal(s1, s2, learn):
                        if index:
                            s1_duplicates.append((i, s1))
                        else:
                            s1_duplicates.append(s2)
                        check_list[j] = False
                duplicates.append(s1_duplicates)

    @staticmethod
    def preprocess_string(s):
        s = s.lower()
        s = s.strip()
        return s

    @staticmethod
    def strong_trivial_model(values):
        if values[0] > 0.95 and values[0] > 0.99 and values[0] > 0.99 and values[0] > 0.9:
            return True
        else:
            return False

    @staticmethod
    def default_model(values):
        if values[0] > 0.92 or values[0] > 0.98 or values[0] > 0.95 or values[0] > 0.92:
            return True
        else:
            return False

    @staticmethod
    def very_strong_trivial_model(values):
        if values[0] > 0.97 and values[0] > 0.98 and values[0] > 0.98 and values[0] > 0.96:
            return True
        else:
            return False

    @staticmethod
    def weak_trivial_model(values):
        val = False
        if values[0] > 0.8 or values[1] > 0.98 or values[2] > 0.9 or values[3] > 0.98:
            val = True
        return val


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