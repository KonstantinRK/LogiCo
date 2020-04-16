from web_apis import *

class PaperPDFMeta(PaperMeta):

    @staticmethod
    def __get_pdf_url_scholar(scholar_obj):
        urls = PaperPDFMeta.__get_field(scholar_obj, "eprint")
        if urls is not None:
            urls = [i[0] if type(i) is list else i for i in urls]
            for i in urls:
                if ".pdf" in i:
                    return i
            for i in urls:
                if "scholar.google.com" in i:
                    x = myscholarly._get_page(i)
                    soup = BeautifulSoup(x, "html.parser")
                    data = soup.findAll("script")[0]
                    return re.findall(r"'(.*?)'", data.text)[0]
            if len(urls) > 0:
                return urls[0]
        return None

    def __init__(self, mail_to=None, classifier=None, inp=True, scholar_break_length=30):
        super().__init__(mail_to, classifier, inp, scholar_break_length)
        self.default_pdf_name = "default.pdf"
        self.temp_path = "temp_api"

        self.pdf = None
        self.pdf_access = None

        self.reset()

    def __get_pdf_url_other(self, inp_doc, base_url, keyword=None):
        if not bool(BeautifulSoup(inp_doc, "html.parser").find()):
            return inp_doc
        soup = BeautifulSoup(inp_doc, "html.parser")
        pdf_links = []
        for i in soup.find_all("a"):
            if ".pdf" in i.get("href"):
                pdf_links.append(i.get("href"))
        if len(pdf_links) > 0:
            return self.__validate_url_results(pdf_links, keyword)
        else:
            return None

    def reset(self):
        super().reset()
        self.pdf = None
        self.pdf_access = None

        if os.path.exists(self.temp_path):
            if len(os.listdir(self.temp_path)) > 0:
                shutil.rmtree(self.temp_path)
                os.makedirs(self.temp_path)
        else:
            os.makedirs(self.temp_path)

    def load_bib(self, load_from_pdf=True, safe_meta=False, safe_pdf=True):
        bib = None
        if self.bib_access is None:
            if self.crossref_meta is not None:
                references = self.__get_field(self.crossref_meta, "reference")
                if references is not None:
                    bib = []
                    for i, ref in enumerate(references):
                        title = None
                        doi = None

                        if ref.get("unstructured", None) is not None:
                            title = self.anystyle("parse", ref["unstructured"])
                            try:
                                title = title[0]["title"][0]
                                if safe_meta and self.inp:
                                    title = self.__check_title(ref, title, i)
                            except KeyError:
                                if self.inp:
                                    title = self.__check_title(ref["unstructured"], title, i)
                                else:
                                    title = str(i)
                        if ref.get("DOI", None) is not None:
                            doi = ref["DOI"]
                        bib.append({"doi": doi, "title": title})

                elif self.pdf is not None and load_from_pdf:
                    pdf_extract = PDFScorer(self.pdf)
                    raw_text = pdf_extract.get_raw_text()
                    result_bib = self.anystyle("find", raw_text)

                    bib = []
                    if result_bib is not None:
                        for i, ref in enumerate(result_bib):
                            try:
                                title = ref["title"][0]
                                if safe_pdf and self.inp:
                                    title = self.__check_title(ref, title)
                            except KeyError:
                                if self.inp and safe_pdf:
                                    title = self.__check_title(ref, "??")
                                else:
                                    title = str(i)
                            bib.append({"doi": None, "title": title})
            self.bib = bib
        if self.bib is None:
            self.bib_access = False
        else:
            self.bib_access = True

    def check_pdf(self):
        if self.pdf is not None:
            with open(os.path.join(self.temp_path, self.default_pdf_name), "rb") as f:
                doc = f.read()
            check = self.__get_pdf_url_other(doc, self.title)
            if check is None:
                self.pdf = None
            elif doc != check:
                url = check
                session = requests.Session()
                with open(os.path.join(self.temp_path, self.default_pdf_name), "wb") as f:
                    file = session.get(url, headers=_HEADERS)
                    f.write(file.content)
                    self.pdf = os.path.join(self.temp_path, self.default_pdf_name)

    def load_pdf(self, name=None, doi=None, pdf=None):
        if self.pdf_access is None:
            if pdf is not None:
                shutil.copy(pdf, os.path.join(self.temp_path, self.default_pdf_name))
                self.pdf = os.path.join(self.temp_path, self.default_pdf_name)
            else:
                self.load_scholar_meta_from_query(name, doi)
                self.pdf = None
                if self.scholar_meta is not None:
                    url = self.__get_pdf_url_scholar(self.scholar_meta)

                    if url is not None:
                        session = requests.Session()
                        with open(os.path.join(self.temp_path, self.default_pdf_name), "wb") as f:
                            file = session.get(url, headers=_HEADERS)
                            doc = file.content
                            try:
                                dec_url = doc.decode("utf-8")
                                if not bool(BeautifulSoup(dec_url, "html.parser").find()):
                                    f.write(doc)
                                    self.pdf = os.path.join(self.temp_path, self.default_pdf_name)
                            except UnicodeDecodeError:
                                f.write(doc)
                                self.pdf = os.path.join(self.temp_path, self.default_pdf_name)
        if self.pdf is None:
            # print("False |", self.title)
            self.pdf_access = False
        else:
            # print("True |", self.title)
            self.pdf_access = True

    def load_paper_from_input(self, crossref_meta, scholar_meta=None, pdf=None, reset=True):
        super().load_paper_from_input(crossref_meta, scholar_meta,reset)
        self.pdf = os.path.join(self.temp_path, self.default_pdf_name)
        if os.path.exists(self.pdf):
            os.remove(self.pdf)
        if pdf is not None:
            shutil.copy(pdf, self.pdf)
        else:
            self.pdf = None
        self.load_meta()

