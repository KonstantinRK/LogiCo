import myscholarly
import json
import requests
import os
import shutil
from string_processing import StringClassifier
from pdf_processing import PDFScorer
from subprocess import run, PIPE
from bs4 import BeautifulSoup
import re
import time
import itertools
from pprint import pprint

# _COOKIES = {'GSP': 'ID={0}:CF=4'.format(_GOOGLEID)}
_HEADERS = {
    'accept-language': 'en-US,en',
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/41.0.2272.76 Chrome/41.0.2272.76 Safari/537.36',
    'accept': 'text/html,application/xhtml+xml,application/xml'
}


class PaperMeta:

    @staticmethod
    def __get_field(input_dict, field_name):
        if input_dict is None:
            return None
        try:
            return input_dict[field_name]
        except IndexError as e:
            return None
        except KeyError as e:
            return None

    @staticmethod
    def __get_title_scholar(scholar_obj):
        title = PaperMeta.__get_field(scholar_obj, "title")
        if type(title) is list:
            return title[0]
        else:
            return title

    @staticmethod
    def __get_author_scholar(scholar_obj):
        author = PaperMeta.__get_field(scholar_obj, "author")
        if type(author) is list:
            return author[0]
        else:
            return author

    @staticmethod
    def __get_authors_crossref(crossref_obj):
        authors_meta = PaperMeta.__get_field(crossref_obj, "author")
        authors = []
        if authors_meta is not None:
            for i in authors_meta:
                try:
                    authors.append({"name": i["family"], "surname": i["given"]})
                except KeyError:
                    pass
        return authors

    @staticmethod
    def __get_doi_crossref(crossref_obj):
        return PaperMeta.__get_field(crossref_obj, "DOI")

    @staticmethod
    def __get_title_crossref(crossref_obj):
        title = PaperMeta.__get_field(crossref_obj, "title")
        if type(title) is list:
            return title[0]
        else:
            return title

    @staticmethod
    def __get_year_crossref(crossref_obj):
        result = PaperMeta.__get_field(crossref_obj, "published-print")
        try:
            result = result["date-parts"][0][0]
        except (IndexError, KeyError, TypeError):
            result = None
        return result

    @staticmethod
    def __get_month_crossref(crossref_obj):
        result = PaperMeta.__get_field(crossref_obj,  "published-print")
        try:
            result = result["date-parts"][0][1]
        except (IndexError, KeyError, TypeError):
            result = None
        return result

    @staticmethod
    def __get_paper_type_crossref(crossref_obj):
        return PaperMeta.__get_field(crossref_obj, "type")

    @staticmethod
    def __get_venue_crossref(crossref_obj):
        result = PaperMeta.__get_field(crossref_obj, "container-title")
        if isinstance(result, list):
            return result[0]
        else:
            return result


    @staticmethod
    def peek(iterable):
        try:
            first = next(iterable)
        except StopIteration:
            return None
        return first, itertools.chain([first], iterable)

    def __init__(self, mail_to=None, classifier=None, inp=True, scholar_break_length=30):
        self.inp = inp
        self.mail_to = mail_to
        self.break_length = scholar_break_length

        self.classifier = classifier
        if self.classifier is None:
            self.classifier = StringClassifier()

        self.crossref_meta = None
        self.scholar_meta = None

        self.doi = None
        self.title = None
        self.year = None
        self.month = None
        self.authors = None
        self.paper_type = None
        self.venue = None
        self.bib = None

        self.bib_access = None
        self.crossref_meta_access = None
        self.scholar_meta_access = None

        self.reset()

    def __check_title(self, ref, title, count=None):
        if not self.inp:
            return None
        print("")
        if count is not None:
            print("-" * 55)
            print("[{0}]".format(count))
        print("-" * 55)
        pprint(ref)
        print("----->>>>")
        pprint(title)
        inp = input("Correct Title / y / n:")
        print("-" * 55)
        print("")
        if inp.strip().lower() == "y" or inp.strip() == "":
            return title
        elif inp.strip().lower() == "n":
            return None
        else:
            return inp.strip()

    def __validate_crossref_results(self, result, keyword=None):
        if not self.inp:
            return None
        print("")
        if keyword is not None:
            print('For the crossref query "{0}":'.format(keyword))
        print("Which of the following is the correct result?")
        for i, val in enumerate(result):
            authors = PaperMeta.__get_authors_crossref(val)
            venue = PaperMeta.__get_venue_crossref(val)
            if len(authors) > 0:
                authors = ", ".join([" ".join(i.values()) for i in authors])
                print(i, ":   {0} | ({1} | {2})".format(PaperMeta.__get_title_crossref(val), authors, venue))
            else:
                print(i, ":   ", PaperMeta.__get_title_crossref(val), " | ", venue)
        inp = input("Nr. / [n]:")
        print("")
        if inp.isnumeric() and int(inp) < len(result):
            return result[int(inp)]
        else:
            return None

    def __validate_url_results(self, result, keyword=None):
        if not self.inp:
            return None
        print("")
        if keyword is not None:
            print('For the page "{0}":'.format(keyword))
        print("Which of the following is the correct result?")
        for i, val in enumerate(result):
            print(i, ":   {0}".format(val))
        inp = input("Nr. / [n]:")
        print("")
        if inp.isnumeric() and int(inp) < len(result):
            return result[int(inp)]
        else:
            return None

    def __validate_scholar_results(self, result, keyword=None):
        if not self.inp:
            return None
        print("")
        if keyword is not None:
            print('For the scholar query "{0}":'.format(keyword))
        print("Which of the following is the correct result?")
        for i, val in enumerate(result):
            authors = PaperMeta.__get_author_scholar(val)
            if len(authors) > 0:
                print(i, ":   {0} | ({1})".format(PaperMeta.__get_title_scholar(val), authors))
            else:
                print(i, ":   ", PaperMeta.__get_title_scholar(val))
        inp = input("Nr. / [n]:")
        print("")
        if inp.isnumeric() and int(inp) < len(result):
            return result[int(inp)]
        else:
            return None

    def reset(self):
        self.crossref_meta = None
        self.scholar_meta = None

        self.doi = None
        self.title = None
        self.year = None
        self.month = None
        self.authors = None
        self.paper_type = None
        self.venue = None
        self.bib = None

        self.bib_access = None
        self.crossref_meta_access = None
        self.scholar_meta_access = None

    def get_meta_dic(self):
        meta_dic = {
            "doi": self.doi,
            "title": self.title,
            "year": self.year,
            "month": self.month,
            "authors": self.authors,
            "paper_type": self.paper_type,
            "venue": self.venue,
            "bib": self.bib
        }
        return meta_dic

    def query_crossref(self, keyword, author=None, validate=True):
        kind = ".bibliographic"
        request = keyword
        if isinstance(author, str):
            request = request + " " + author
        print("Crossref Load: " + request)
        if self.mail_to is None:
            url = "https://api.crossref.org/works?query{kind}={keyword}".format(keyword=request, kind=kind)
        else:
            url = "https://api.crossref.org/works?query{kind}={keyword}&mailto={mail_to}"\
                .format(keyword=request, kind=kind, mail_to=self.mail_to)
        query = json.loads(requests.get(url).text)
        try:

            result = query["message"]["items"]
        except TypeError:
            self.crossref_meta = None
            return None
        count = 0
        for i in result:
            title = self.__get_title_crossref(i)
            if title is not None and self.classifier.equal(keyword, title):
                self.crossref_meta = i
                count += 1
        if count == 0:
            self.crossref_meta = None
        elif count != 1:
            if validate and self.inp:
                self.crossref_meta = self.__validate_crossref_results(result, request)
            else:
                self.crossref_meta = None
        return self.crossref_meta

    def query_google(self, request):
        result = self.peek(myscholarly.search_pubs_query(request))
        if result is None:
            print("DETECTED")
            result = self.peek(myscholarly.search_pubs_query(request))
            if result is None:
                return None
        return result[1]

    def query_scholar(self, keyword, author=None):
        result = []
        request = keyword
        if isinstance(author, str):
            request = request + " " + author
        print("Scholar Load: " + request)
        res = self.query_google(request)
        count = 0
        for i in res:
            entry = i.bib
            if self.__get_title_scholar(entry) is not None and\
                    self.classifier.equal(self.__get_title_scholar(entry), keyword):
                self.scholar_meta = entry
                count += 1
            result.append(entry)
            if len(result) > self.break_length:
                break
        if count != 1:
            if self.inp:
                self.scholar_meta = self.__validate_scholar_results(result, request)
            else:
                self.scholar_meta = None
        return self.scholar_meta

    def query_scholar_doi(self, doi):
        result = list(self.query_google(doi))[0].bib
        # if isinstance(result, list) and len(result) > 0:
        #     self.scholar_meta = list(myscholarly.search_pubs_query(doi))[0].bib
        # else:
        #     print(result)
        #     self.scholar_meta = None
        self.scholar_meta = result
        return self.scholar_meta

    def load_doi(self):
        if self.doi is None and self.crossref_meta is not None:
            self.doi = self.__get_doi_crossref(self.crossref_meta)

    def load_title(self):
        if self.title is None and self.crossref_meta is not None:
            self.title = self.__get_title_crossref(self.crossref_meta)
        if self.title is None and self.scholar_meta is not None:
            self.title = self.__get_title_scholar(self.scholar_meta)

    def load_year(self):
        if self.year is None and self.crossref_meta is not None:
            self.year = self.__get_year_crossref(self.crossref_meta)

    def load_month(self):
        if self.month is None and self.crossref_meta is not None:
            self.month = self.__get_month_crossref(self.crossref_meta)

    def load_authors(self):
        if self.authors is None and self.crossref_meta is not None:
            self.authors = self.__get_authors_crossref(self.crossref_meta)

    def load_paper_type(self):
        if self.paper_type is None and self.crossref_meta is not None:
            self.paper_type = self.__get_paper_type_crossref(self.crossref_meta)

    def load_venue(self):
        if self.venue is None and self.crossref_meta is not None:
            self.venue = self.__get_venue_crossref(self.crossref_meta)

    def load_bib(self, safe_meta=False):
        bib = None
        if self.bib_access is None and self.crossref_meta is not None:
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

            self.bib = bib
        if self.bib is None:
            self.bib_access = False
        else:
            self.bib_access = True


    def load_meta(self):
        self.load_doi()
        self.load_title()
        self.load_year()
        self.load_month()
        self.load_authors()
        self.load_paper_type()
        self.load_venue()

    def load_paper_from_query(self, name, doi=None, author=None, load_scholar=True, request_doi=True, reset=True):
        # print("#"*100)
        if reset:
            self.reset()
        if doi is not None:
            self.query_crossref(doi)
        else:
            self.query_crossref(name)
            if self.crossref_meta is None and load_scholar:
                self.load_scholar_meta_from_query(name, author)
                if self.scholar_meta is not None:
                    author = self.__get_author_scholar(self.scholar_meta)
                    name = self.__get_title_crossref(self.scholar_meta)
                    self.query_crossref(name, author)

        if self.crossref_meta is None and self.inp and request_doi:
            print('Enter DOI of Paper "{0}"'.format(name))
            inp = input("DOI / n")
            if inp.strip().lower() != "n" and load_scholar:
                load_scholar = self.scholar_meta
                self.load_paper_from_query(name, inp, author, load_scholar=load_scholar, reset=False)

        if self.crossref_meta is None and self.scholar_meta is None:
            self.title = name
        else:
            self.load_meta()

        if self.crossref_meta is not None and load_scholar and self.scholar_meta is None:
            self.load_scholar_meta_from_query()

    def load_scholar_meta_from_query(self, name=None, doi=None, author=None):
        if self.scholar_meta is None:
            if self.doi is not None:
                self.query_scholar_doi(self.doi)
            elif doi is not None:
                self.query_scholar_doi(doi)
            elif self.title is not None:
                try:
                    self.query_scholar(self.title, self.authors[0]["surname"])
                except (IndexError, KeyError, TypeError, ValueError):
                    self.query_scholar(self.title, author)
            elif name is not None:
                self.query_scholar(name, author)

    def load_paper_from_input(self, crossref_meta, scholar_meta=None, reset=True):
        if reset:
            self.reset()
        self.crossref_meta = crossref_meta
        self.scholar_meta = scholar_meta
        self.load_meta()

    def anystyle(self, command, inp):
        path = os.path.join("anystyle.txt")
        path = os.path.abspath(path)
        with open(path, "w") as f:
            f.write(inp)
        try:
            result = run("anystyle {0} {1}".format(command, path),
                         shell=True, stdout=PIPE, stderr=PIPE, universal_newlines=True)
            result = json.loads(result.stdout)
        except Exception:
            result = None
        finally:
            os.remove(path)
        return result


