from database import *
import os
from string_processing import StringClassifier
from web_apis import PaperMeta
import json
class DBManager:

    @staticmethod
    def __clean_string(string):
        if isinstance(string, str):
            string = string.strip().lower()
        return string

    def __init__(self, download_dir="/Users/krk/Downloads", name='sqlite:///PaperDB.db',
                 string_classifier=None, web_api=None):
        self.download_dir = download_dir
        engine = create_engine(name, echo=False)
        Base.metadata.create_all(engine)
        self.Session = sessionmaker(bind=engine)
        self.session = None
        self.archive_path = "archive"
        self.str_classifier = StringClassifier() if string_classifier is None else string_classifier
        self.web_api = web_api
        if not os.path.exists(self.archive_path):
            os.mkdir(self.archive_path)

    def execute(self, open_session, foo, *args, **kwargs):
        if open_session:
            if self.session is not None:
                raise Exception("Session is already open")
            self.session = self.Session()
        try:
            result = foo(*args, **kwargs)
            if open_session:
                self.session.commit()
            return result
        except Exception as e:
            print("#"*100)
            print(e)
            print("#" * 100)
            print("")
            self.session.rollback()
            return []
        finally:
            self.session.close()
            self.session = None

    def open_session(self, open_session=True):
        if open_session:
            if self.session is not None:
                raise Exception("Session is already open")
            self.session = self.Session()

    def close_session(self, open_session=True):
        if open_session:
            try:
                self.session.commit()
            except Exception as e:
                print("#"*100)
                print(e)
                print("#" * 100)
                print("")
                self.session.rollback()
            finally:
                self.session.close()
                self.session = None

    # ---------------------------------------------------------------
    # ---------------------------------------------- Author: Functions
    # ---------------------------------------------------------------

    def __add_author(self, name, surname, comment=None):
        name = DBManager.__clean_string(name)
        surname = DBManager.__clean_string(surname)
        author = Author(name=name, surname=surname, comment=comment)
        self.session.add(author)

    def __author_to_dict(self, author_key):
        author = self.__get_author(author_key=author_key)
        dic = author.transform_to_dict()
        return dic

    # ---------------------------------------------- Author: Get Functions

    def __get_author(self, name=None, surname=None, comment=None, author_key=None, as_dict=False):
        name = DBManager.__clean_string(name)
        surname = DBManager.__clean_string(surname)
        if author_key is not None:
            q = self.session.query(Author).filter(Author.key == author_key)
        else:
            q = self.session.query(Author).filter((Author.name == name) & (Author.surname == surname))
            if comment is not None:
                q = q.filter(Author.comment == comment)
        result = list(q)[-1]
        if as_dict:
            result.transform_to_dict()
        return result

    def __get_author_key(self, name,  surname, comment=None):
        name = DBManager.__clean_string(name)
        surname = DBManager.__clean_string(surname)
        result = self.__get_author(name, surname, comment)
        author_key = result.key
        return author_key

    # ---------------------------------------------- Author: Edit Functions

    def __edit_author(self, author_key, name=None, surname=None, comment=None):
        author = self.__get_author(author_key=author_key)
        if name is not None:
            author.name = DBManager.__clean_string(name)
        if surname is not None:
            author.surname = DBManager.__clean_string(surname)
        if comment is not None:
            author.comment = comment

    # ---------------------------------------------------------------
    # ---------------------------------------------- Paper: Functions
    # ---------------------------------------------------------------

    def __list_papers(self, tags=None, authors=None, not_tags=None, invert=False,
                      start_year=None, end_year=None, relevant=None, access=None, as_dict=False):
        q = self.session.query(Paper.key)
        if tags is not None or not_tags is not None:
            q = q.join(tag_table).join(Tag)
            if tags is not None:
                q = q.filter(Tag.key.in_(tags))
            if not_tags is not None:
                q2 = self.session.query(Paper.key).join(tag_table).join(Tag).filter(Tag.key.in_(not_tags))
                q = q.filter(~Paper.key.in_(q2))
        if authors is not None:
            q = q.join(authorship_table).join(Author).filter(Author.key.in_(tags))
        if relevant is not None:
            q = q.filter(Paper.relevant == relevant)
        if access is not None:
            q = q.filter(Paper.access == access)

        if start_year is not None:
            q = q.filter(Paper.year >= start_year)
        if end_year is not None:
            q = q.filter(Paper.year <= end_year)

        if invert:
            q = self.session.query(Paper).filter(~Paper.key.in_(q))
        else:
            q = self.session.query(Paper).filter(Paper.key.in_(q))
        papers = q.all()
        if as_dict:
            papers = [i.transform_to_dict() for i in papers]
        return papers

    def __add_paper(self, name, year=None, month=None, doi=None):
        name = DBManager.__clean_string(name)
        paper = Paper(name=name, doi=doi, year=year, month=month)
        self.session.add(paper)

    def __delete_paper(self, paper_key):
        paper = self.session.query(Paper).filter(Paper.key == paper_key).one()
        self.session.delete(paper)

    def __search_paper(self, name, author_name=None, model="default", print_values=False):
        name = DBManager.__clean_string(name)
        if author_name is not None:
            author_name = DBManager.__clean_string(author_name)
            authors = self.session.query(Author).all()
            result = []
            for i in authors:
                if i.name is None:
                    i_name = ""
                else:
                    i_name = i.name
                if i.surname is not None:
                    i_name = i_name + " " + i.surname

                if self.str_classifier.equal(i_name, author_name, model=model):
                    result.append(i.key)
            paper = self.session.query(Paper).join(authorship_table).join(Author).filter(Author.key.in_(result)).all()
        else:
            paper = self.session.query(Paper).all()
        result = []
        for i in paper:

            if self.str_classifier.equal(i.name, name, model=model):
                if not (" " in name and " " not in i.name):
                    if print_values:
                        print(i.name, self.str_classifier.equal_array(i.name, name))
                    result.append((i.key, i.name))
        return result

    def __paper_to_dict(self, paper_key):
        paper = self.__get_paper(paper_key=paper_key)
        dic = paper.transform_to_dict()
        return dic

    # ---------------------------------------------- Paper: Get Functions

    def __get_paper_key(self, name, doi=None):
        name = DBManager.__clean_string(name)
        result = self.__get_paper(name, doi)
        paper_key = result.key
        return paper_key

    def __get_paper(self, name=None, doi=None, paper_key=None, as_dict=False):
        name = DBManager.__clean_string(name)
        if paper_key is not None:
            result = self.session.query(Paper).filter(Paper.key == paper_key).one()
        elif doi is not None:
            result = self.session.query(Paper).filter(Paper.doi == doi).one()
        else:
            result = self.session.query(Paper).filter(Paper.name == name).one()
        if as_dict:
            result = result.transform_to_dict()
        return result

    def __get_paper_authors(self, paper_key):
        paper = self.__get_paper(paper_key=paper_key)
        authors = []
        for entry in paper.authors:
            authors.append(entry.transform_to_dict())
        return authors

    def __get_paper_bib(self, paper_key):
        paper = self.__get_paper(paper_key=paper_key)
        bib = []
        for entry in paper.cites:
            bib.append(entry.transform_to_dict())
        return bib

    def __get_paper_bibtex(self, paper_key):
        paper = self.__get_paper(paper_key=paper_key)
        return paper.bibtex

    def __get_paper_json(self, paper_key):
        paper = self.__get_paper(paper_key=paper_key)
        return paper.json

    def __get_paper_pdf(self, paper_key):
        paper = self.__get_paper(paper_key=paper_key)
        paper_pdf_path = paper.pdf_path
        path = os.path.abspath(paper_pdf_path)
        os.system("open {0}".format(path))

    def __get_paper_tags(self, paper_key):
        tags = self.session.query(Tag).join(tag_table).join(Paper).filter(Paper.key == paper_key).all()
        tags = [i.transform_to_dict() for i in tags]
        return tags

    def __get_paper_ref(self, paper_key):
        paper = self.__get_paper(paper_key=paper_key)
        bib = []
        for entry in paper.references:
            bib.append(entry.transform_to_dict())
        return bib

    # ---------------------------------------------- Paper: Edit Functions

    def __edit_paper(self, paper_key, name=None, doi=None, year=None, month=None,
                     relevant=None, accessible=None, comment=None, json_string=None, bibtex=None,
                     append_comment=True):
        paper = self.__get_paper(paper_key=paper_key)
        if name is not None:
            paper.name = DBManager.__clean_string(name)
        if doi is not None:
            paper.doi = doi
        if year is not None:
            paper.year = year
        if month is not None:
            paper.month = month
        if relevant is not None:
            paper.relevant = relevant
        if accessible is not None:
            paper.access = accessible
        if comment is not None:
            if append_comment and paper.comment is not None:
                paper.comment = paper.comment + "\n" + comment
            else:
                paper.comment = comment
        if json_string is not None:
            paper.json = json_string
        if bibtex is not None:
            paper.bibtex = bibtex

    # ---------------------------------------------- Paper: Relation Functions

    def __add_author_to_paper(self, paper_key, author_key):
        paper = self.__get_paper(paper_key=paper_key)
        author = self.__get_author(author_key=author_key)
        paper.authors.append(author)

    def __add_citation_to_paper(self, paper_key, citation_key):
        paper = self.__get_paper(paper_key=paper_key)
        citation = self.__get_paper(paper_key=citation_key)
        paper.cites.append(citation)

    def __add_pdf_to_paper(self, paper_key, pdf_path=None):
        paper = self.__get_paper(paper_key=paper_key)
        if paper.access is not True:
            if pdf_path is None:
                downloads = [os.path.join(self.download_dir, file) for file in os.listdir(self.download_dir)
                             if file[0] != "."]
                if len(downloads) > 0:
                    pdf_path = max(downloads, key=os.path.getatime)

                else:
                    print("Error: No file found.")
            path = os.path.join(self.archive_path, str(paper.key) + ".pdf")
            os.rename(pdf_path, path)
            paper.pdf_path = path
            paper.access = True


    def __add_tag_to_paper(self, paper_key, tag_key):
        paper = self.__get_paper(paper_key=paper_key)
        tag = self.__get_tag(tag_key=tag_key)
        paper.tags.append(tag)

    # ---------------------------------------------- Paper: Set Functions

    def __fill_paper_from_webapi(self, paper_key):
        if self.web_api is not None:
            paper = self.__get_paper(paper_key=paper_key)
            self.web_api.load_paper_from_query(paper.name, load_scholar=False)
            print("Load Bib")
            self.web_api.load_bib()
            meta_dic = self.web_api.get_meta_dic()
            meta_dic["title"] = meta_dic["title"].lower().strip()
            if meta_dic["venue"] is not None:
                try:
                    venue = self.__get_venue(meta_dic["venue"])
                except Exception:
                    self.__add_venue(meta_dic["venue"])
                    venue = self.__get_venue(meta_dic["venue"])
                venue.papers.append(paper)

            authors = []
            for i in meta_dic["authors"]:
                try:
                    author = self.__get_author(name=i["name"], surname=i["surname"])
                except Exception:
                    self.__add_author(name=i["name"], surname=i["surname"])
                    author = self.__get_author(name=i["name"], surname=i["surname"])
                authors.append(author)
            for i in authors:
                paper.authors.append(i)

            try:
                tag = self.__get_tag("auto_filled")
            except Exception:
                self.__add_tag("auto_filled")
                tag = self.__get_tag("auto_filled")
            paper.tags.append(tag)

            paper.doi = meta_dic["doi"]
            paper.year = meta_dic["year"]
            paper.month = meta_dic["month"]
            paper.json = json.dumps(meta_dic)

            if paper.name != meta_dic["title"]:
                print("Rename: '{0}' -> '{1}'".format(paper.name, meta_dic["title"]))
                inp = input("y / [n]: ")
                if inp.strip() == "y":
                    paper.name = meta_dic["title"]
            print("#"*100)
            print("")
            print("")
            return meta_dic

    # ---------------------------------------------------------------
    # ---------------------------------------------- Tag: Functions
    # ---------------------------------------------------------------

    def __list_tags(self):
        tags = [i.name for i in self.session.query(Tag)]
        return tags

    def __add_tag(self, name):
        name = DBManager.__clean_string(name)
        tag = Tag(name=name)
        self.session.add(tag)

    def __tag_to_dict(self, tag_key):
        tag = self.__get_tag(tag_key=tag_key)
        dic = tag.transform_to_dict()
        return dic

    # ---------------------------------------------- Venue: Get Functions

    def __get_tag(self, name=None, tag_key=None, as_dict=False):
        name = DBManager.__clean_string(name)
        if tag_key is not None:
            q = self.session.query(Tag).filter(Tag.key == tag_key)
        else:
            q = self.session.query(Tag).filter(Tag.name == name)
        result = list(q)[-1]
        if as_dict:
            result = result.transform_to_dict()
        return result

    def __get_tag_key(self, name):
        name = DBManager.__clean_string(name)
        result = self.__get_tag(name)
        tag_key = result.key
        return tag_key

    # ---------------------------------------------------------------
    # ---------------------------------------------- Venue: Functions
    # ---------------------------------------------------------------

    def __list_venues(self):
        tags = [i.name for i in self.session.query(Venue)]
        return tags

    def __add_venue(self, name):
        name = DBManager.__clean_string(name)
        venue = Venue(name=name)
        self.session.add(venue)

    def __venue_to_dict(self, venue_key):
        venue = self.__get_venue(venue_key=venue_key)
        dic = venue.transform_to_dict()
        return dic

    # ---------------------------------------------- Venue: Get Functions

    def __get_venue_key(self, name):
        name = DBManager.__clean_string(name)
        result = self.__get_venue(name)
        venue_key = result.key
        return venue_key

    def __get_venue(self, name=None, venue_key=None, as_dict=False):
        name = DBManager.__clean_string(name)
        if venue_key is not None:
            q = self.session.query(Venue).filter(Venue.key == venue_key)
        else:
            if name is not None:
                name = DBManager.__clean_string(name)
            q = self.session.query(Venue).filter(Venue.name == name)
        result = q.one()
        if as_dict:
            result = result.transform_to_dict()
        return result

    # ---------------------------------------------- Venue: Relation Functions

    def __add_paper_to_venue(self, venue_key, paper_key):
        paper = self.__get_paper(paper_key=paper_key)
        venue = self.__get_venue(venue_key=venue_key)
        venue.papers.append(paper)

    # ##########################################################################################
    # ------------------------------------------------------------------------------------------
    # ------------------------------------------------------------------------------------------
    # ------------------------------------------------------------------------------------------
    # ------------------------------------------------------------------------------------------
    # ##########################################################################################

    def add_author(self, name, surname, comment=None):
        self.execute(True, self.__add_author, name=name, surname=surname, comment=comment)
        return self.get_author_key(name, surname, comment)

    def author_to_dict(self, author_key):
        return self.execute(True, self.__author_to_dict, author_key=author_key)

    # ---------------------------------------------- Author: Get Functions

    def get_author(self, author_key):
        return self.execute(True, self.__get_author, author_key=author_key, as_dict=True).transform_to_dict()

    def get_author_key(self, name, surname, comment=None):
        return self.execute(True, self.__get_author_key, name=name, surname=surname, comment=comment)

    # ---------------------------------------------- Author: Edit Functions

    def edit_author(self, paper_key, author_key, name=None, surname=None, comment=None):
        return self.execute(True, self.__edit_author, paper_key=paper_key, author_key=author_key,
                            name=name, surname=surname, comment=comment)

    # ---------------------------------------------------------------
    # ---------------------------------------------- Paper: Functions
    # ---------------------------------------------------------------

    def list_papers(self, tags=None, authors=None, not_tags=None, invert=False,
                    start_year=None, end_year=None, relevant=None, access=None,names=True):
        if tags is not None:
            if not isinstance(tags, list):
                tags = [tags]
            tags = [i if isinstance(i, int) else self.get_tag_key(i) for i in tags]
        if not_tags is not None:
            if not isinstance(not_tags, list) and not_tags is not None:
                not_tags = [not_tags]
            not_tags = [i if isinstance(i, int) else self.get_tag_key(i) for i in not_tags]

        if not isinstance(authors, list) and authors is not None:
            authors = [authors]
        result = self.execute(True, self.__list_papers, tags=tags, authors=authors, not_tags=not_tags,
                              invert=invert, start_year=start_year, end_year=end_year,
                              relevant=relevant, access=access, as_dict=True)
        if names:
            result = [i["name"] for i in result]
        return result

    def add_paper(self, name, year=None, month=None, doi=None, check=True):
        if check:
            result = self.search_paper(name, model="strong")
            if len(result) == 1:
                print("!!!", result[0])
                return result[0][0]
            if len(result) > 0:
                for i in result:
                    print("!!!", i)
                return None
        self.execute(True, self.__add_paper, name=name, year=year, month=month, doi=doi)
        return self.get_paper_key(name, doi)

    def delete_paper(self, paper_key):
        return self.execute(True, self.__delete_paper, paper_key=paper_key)

    def search_paper(self, name, author_name=None, model="default", print_values=False):
        return self.execute(True, self.__search_paper, name=name, author_name=author_name, model=model,
                            print_values=print_values)

    def paper_to_dict(self, paper_key):
        return self.execute(True, self.__paper_to_dict, paper_key=paper_key)

    # ---------------------------------------------- Paper: Get Functions

    def get_paper(self, paper_key):
        return self.execute(True, self.__get_paper, paper_key=paper_key, as_dict=True)

    def get_paper_key(self, name, doi=None):
        return self.execute(True, self.__get_paper_key, name=name, doi=doi)

    def get_paper_authors(self, paper_key):
        return self.execute(True, self.__get_paper_authors, paper_key=paper_key)

    def get_paper_bib(self, paper_key):
        return self.execute(True, self.__get_paper_bib, paper_key=paper_key)

    def get_paper_bibtex(self, paper_key):
        return self.execute(True, self.__get_paper_bibtex, paper_key=paper_key)

    def get_paper_json(self, paper_key):
        return self.execute(True, self.__get_paper_json, paper_key=paper_key)

    def get_paper_pdf(self, paper_key):
        return self.execute(True, self.__get_paper_pdf, paper_key=paper_key)

    def get_paper_tags(self, paper_key):
        return self.execute(True, self.__get_paper_tags, paper_key=paper_key)

    def get_paper_ref(self, paper_key):
        return self.execute(True, self.__get_paper_ref, paper_key=paper_key)

    # ---------------------------------------------- Paper: Set Functions

    def edit_paper(self, paper_key, name=None, doi=None, year=None, month=None):
        return self.execute(True, self.__edit_paper, paper_key=paper_key, name=name, doi=doi, year=year, month=month)

    def set_paper_accessible(self, paper_key, accessible):
        return self.execute(True, self.__edit_paper, paper_key=paper_key, accessible=accessible)

    def set_paper_bibtex(self, paper_key, bibtex):
        return self.execute(True, self.__edit_paper, paper_key=paper_key, bibtex=bibtex)

    def set_paper_comment(self, paper_key, comment, append_comment=True):
        return self.execute(True, self.__edit_paper, paper_key=paper_key, comment=comment,
                            append_comment=append_comment)

    def set_paper_json(self, paper_key, json_string):
        return self.execute(True, self.__edit_paper, paper_key=paper_key, json_string=json_string)

    def set_paper_relevance(self, paper_key, relevant):
        return self.execute(True, self.__edit_paper, paper_key=paper_key, relevant=relevant)

    # ---------------------------------------------- Paper: Add Functions

    def add_author_to_paper(self, paper_key, author_key):
        return self.execute(True, self.__add_author_to_paper, paper_key=paper_key, author_key=author_key)

    def add_citation_to_paper(self, paper_key, citation_key):
        return self.execute(True, self.__add_citation_to_paper, paper_key=paper_key, citation_key=citation_key)

    def add_tag_to_paper(self, paper_key, tag_key):
        if isinstance(tag_key, str):
            tag_key = self.get_tag_key(tag_key)
        return self.execute(True, self.__add_tag_to_paper, paper_key=paper_key, tag_key=tag_key)

    def add_pdf_to_paper(self, paper_key, pdf_path=None):
        return self.execute(True, self.__add_pdf_to_paper, paper_key=paper_key, pdf_path=pdf_path)

    # ---------------------------------------------- Paper: Set Functions

    def fill_paper_from_webapi(self, paper_key):
        return self.execute(True, self.__fill_paper_from_webapi, paper_key=paper_key)

    # ---------------------------------------------------------------
    # ---------------------------------------------- Tag: Functions
    # ---------------------------------------------------------------

    def list_tags(self):
        return self.execute(True, self.__list_tags)

    def add_tag(self, name):
        self.execute(True, self.__add_tag, name=name)
        return self.get_tag_key(name)

    def tag_to_dict(self, tag_key):
        parameter = DBManager.clean_parameter(locals())
        return self.execute(True, self.__tag_to_dict, tag_key=tag_key)

    # ---------------------------------------------- Venue: Get Functions

    def get_tag(self, tag_key):
        return self.execute(True, self.__get_tag, tag_key=tag_key, as_dict=True)

    def get_tag_key(self, name):
        return self.execute(True, self.__get_tag_key, name=name)

    # ---------------------------------------------------------------
    # ---------------------------------------------- Venue: Functions
    # ---------------------------------------------------------------

    def list_venues(self):
        return self.execute(True, self.__list_venues)

    def add_venue(self, name):
        self.execute(True, self.__add_venue, name=name)
        return self.get_venue_key(name)

    def venue_to_dict(self, venue_key):
        return self.execute(True, self.__venue_to_dict, venue_key=venue_key)

    # ---------------------------------------------- Venue: Get Functions

    def get_venue(self, venue_key):
        return self.execute(True, self.__get_venue, venue_key=venue_key, as_dict=True)

    def get_venue_key(self, name):
        return self.execute(True, self.__get_venue_key, name=name)

    # ---------------------------------------------- Venue: Relation Functions

    def add_paper_to_venue(self, venue_key, paper_key):
        return self.execute(True, self.__add_paper_to_venue, venue_key=venue_key, paper_key=paper_key)




