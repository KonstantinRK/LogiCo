from database import *
import os
from pprint import pprint
from fuzzywuzzy import fuzz

class DBManager:

    def __init__(self, download_dir="/Users/krk/Downloads", name='sqlite:///PaperDB.db'):
        self.download_dir = download_dir
        engine = create_engine(name, echo=False)
        Base.metadata.create_all(engine)
        self.Session = sessionmaker(bind=engine)
        self.session = None
        self.archive_path = "archive"
        if not os.path.exists(self.archive_path):
            os.mkdir(self.archive_path)

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

    def __add_author(self, name, surname, comment=None, session=True):
        self.open_session(session)
        author = Author(name=name, surname=surname, comment=comment)
        self.session.add(author)
        self.close_session(session)

    def add_author(self, name, surname, comment=None):
        self.__add_author(name.lower().strip(),  surname.lower().strip(), comment)
        return self.get_author_key(name, surname, comment)

    def __add_paper(self, name, year=None, month=None, doi=None, session=True):
        self.open_session(session)
        paper = Paper(name=name, doi=doi, year=year, month=month)
        self.session.add(paper)
        self.close_session(session)

    def add_paper(self, name, year=None, month=None, doi=None, check=True):
        if check:
            result = self.search_paper(name)
            if len(result) == 1:
                print("!!!", result[0])
                return result[0][0]
            if len(result) > 0:
                for i in result:
                    print("!!!", i)
                return None

        self.__add_paper(name.lower().strip(), year, month, doi)
        return self.get_paper_key(name, doi)

    def __add_tag(self, name, session=True):
        self.open_session(session)
        tag = Tag(name=name)
        self.session.add(tag)
        self.close_session(session)

    def add_tag(self, name):
        self.__add_tag(name.lower().strip())
        return self.get_tag_key(name)

    def __add_venue(self, name, session=True):
        self.open_session(session)
        venue = Venue(name=name)
        self.session.add(venue)
        self.close_session(session)

    def add_venue(self, name):
        self.__add_venue(name.lower().strip())
        return self.get_venue_key(name)

    def __get_paper(self, name=None, doi=None, key=None):
        if key is not None:
            result = self.session.query(Paper).filter(Paper.key == key).one()
        elif doi is not None:
            result = self.session.query(Paper).filter(Paper.doi == doi).one()
        else:
            if name is not None:
                name = name.lower().strip()
            result = self.session.query(Paper).filter(Paper.name == name).one()
        return result

    def __get_paper_key(self, name, doi=None, session=True):
        self.open_session(session)
        result = self.__get_paper(name, doi)
        key = result.key
        self.close_session(session)
        return key

    def get_paper_key(self, name, doi=None):
        return self.__get_paper_key(name, doi)

    def get_paper(self, key):
        self.open_session()
        paper = self.__paper_to_dic(self.__get_paper(key=key))
        self.close_session()
        return paper

    def __get_author(self, name=None, surname=None, comment=None, key=None):
        if key is not None:
            q = self.session.query(Author).filter(Author.key == key)
        else:
            if name is not None:
                name = name.lower().strip()
            if surname is not None:
                surname = surname.lower().strip()
            q = self.session.query(Author).filter((Author.name == name) & (Author.surname == surname))
            if comment is not None:
                q = q.filter(Author.comment == comment)
        result = list(q)[-1]
        return result

    def __get_author_key(self, name,  surname, comment=None, session=True):
        self.open_session(session)
        result = self.__get_author(name, surname, comment)
        key = result.key
        self.close_session(session)
        return key

    def get_author_key(self, name,  surname, comment=None):
        return self.__get_author_key(name, surname, comment)

    def get_author(self, key):
        self.open_session()
        author = self.__author_to_dic(self.__get_author(key=key))
        self.close_session()
        return author

    def __get_tag(self, name=None, key=None):
        if key is not None:
            q = self.session.query(Tag).filter(Tag.key == key)
        else:
            if name is not None:
                name = name.lower().strip()
            q = self.session.query(Tag).filter(Tag.name == name)
        result = list(q)[-1]
        return result

    def __get_tag_key(self, name, session=True):
        self.open_session(session)
        result = self.__get_tag(name)
        key = result.key
        self.close_session(session)
        return key

    def get_tag_key(self, name):
        return self.__get_tag_key(name)

    def get_tag(self, key):
        self.open_session()
        tag = self.__tag_to_dic(self.__get_tag(key=key))
        self.close_session()
        return tag

    def __get_venue(self, name=None, key=None):
        if key is not None:
            q = self.session.query(Venue).filter(Venue.key == key)
        else:
            if name is not None:
                name = name.lower().strip()
            q = self.session.query(Venue).filter(Venue.name == name)
        result = q.one()
        return result

    def __get_venue_key(self, name, session=True):
        self.open_session(session)
        result = self.__get_venue(name)
        key = result.key
        self.close_session(session)
        return key

    def get_venue_key(self, name):
        return self.__get_venue_key(name)

    def get_venue(self, key):
        self.open_session()
        venue = self.__venue_to_dic(self.__get_venue(key=key))
        self.close_session()
        return venue

    def __edit_paper(self, paper_key, name=None, doi=None, year=None, month=None,
                     relevant=None, accessible=None, comment=None, append_comment=True, session=True):
        self.open_session(session)
        paper = self.__get_paper(key=paper_key)
        if name is not None:
            paper.name = name
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
        self.close_session(session)

    def edit_paper(self, paper_key, name=None, doi=None, year=None, month=None):
        self.__edit_paper(paper_key, name, doi, year, month)

    def paper_relevance(self, paper_key, status):
        self.__edit_paper(paper_key, relevant=status)

    def paper_accessible(self, paper_key, status):
        self.__edit_paper(paper_key, accessible=status)

    def paper_comment(self, paper_key, comment, append=True):
        self.__edit_paper(paper_key, comment=comment, append_comment=append)

    def __edit_author(self, author_key, name=None, surname=None, comment=None, session=True):
        self.open_session(session)
        author = self.__get_author(key=author_key)
        if name is not None:
            author.name = name
        if surname is not None:
            author.surname = surname
        if comment is not None:
            author.comment = comment
        self.close_session(session)

    def edit_author(self, paper_key, author_key, name=None, surname=None, comment=None):
        self.__edit_paper(paper_key, author_key, name, surname, comment)

    def __add_author_to_paper(self, paper_key, author_key, session=True):
        self.open_session(session)
        paper = self.__get_paper(key=paper_key)
        author = self.__get_author(key=author_key)
        paper.authors.append(author)
        self.close_session(session)

    def add_author_to_paper(self, paper_key, author_key):
        self.__add_author_to_paper(paper_key, author_key)

    def __add_tag_to_paper(self, paper_key, tag_key, session=True):
        self.open_session(session)
        paper = self.__get_paper(key=paper_key)
        tag = self.__get_tag(key=tag_key)
        paper.tags.append(tag)
        self.close_session(session)

    def add_tag_to_paper(self, paper_key, tag_key):
        if isinstance(tag_key, str):
            tag_key = self.get_tag_key(tag_key)
        self.__add_tag_to_paper(paper_key, tag_key)

    def __add_paper_to_venue(self, venue_key, paper_key, session=True):
        self.open_session(session)
        paper = self.__get_paper(key=paper_key)
        venue = self.__get_venue(key=venue_key)
        venue.papers.append(paper)
        self.close_session(session)

    def add_paper_to_venue(self, venue_key, paper_key):
        self.__add_paper_to_venue(venue_key, paper_key)

    def __add_citation_to_paper(self, paper_key, citation_key, session=True):
        self.open_session(session)
        paper = self.__get_paper(key=paper_key)
        citation = self.__get_paper(key=citation_key)
        paper.cites.append(citation)
        self.close_session(session)

    def add_citation_to_paper(self, paper_key, citation_key):
        self.__add_citation_to_paper(paper_key, citation_key)

    def __add_model_reference_to_paper(self, paper_key, citation_key, session=True):
        self.open_session(session)
        paper = self.__get_paper(key=paper_key)
        citation = self.__get_paper(key=citation_key)
        paper.references.append(citation)
        self.close_session(session)

    def add_model_reference_to_paper(self, paper_key, citation_key):
        self.__add_model_reference_to_paper(paper_key, citation_key)

    def __add_pdf_to_paper(self, paper_key, pdf_path=None, session=True):
        self.open_session(session)
        paper = self.__get_paper(key=paper_key)
        if paper.access is not True:
            if pdf_path is None:
                downloads = [os.path.join(self.download_dir, file) for file in os.listdir(self.download_dir)
                             if file[0] != "."]
                if len(downloads) > 0:
                    pdf_path = max(downloads, key=os.path.getatime)
                    path = os.path.join(self.archive_path, str(paper.key) + ".pdf")
                    os.rename(pdf_path, path)
                    paper.pdf_path = path
                    paper.accessible = True
                else:
                    print("Error: No file found.")
        self.close_session(session)

    def add_pdf_to_paper(self, paper_key, pdf_path=None):
        self.__add_pdf_to_paper(paper_key, pdf_path)

    @staticmethod
    def __paper_to_dic(paper):
        dic = {}
        dic["key"] = paper.key
        dic["name"] = paper.name
        dic["doi"] = paper.doi
        dic["year"] = paper.year
        dic["month"] = paper.month
        dic["relevant"] = paper.relevant
        dic["access"] = paper.access
        dic["comment"] = paper.comment
        dic["pdf_path"] = paper.pdf_path
        return dic

    def paper_to_dic(self, paper_key, session=True):
        self.open_session(session)
        paper = self.__get_paper(key=paper_key)
        dic = self.__paper_to_dic(paper)
        self.close_session(session)
        return dic

    def __paper_bib(self, paper_key, session=True):
        self.open_session(session)
        paper = self.__get_paper(key=paper_key)
        bib = []
        for entry in paper.cites:
            bib.append(self.__paper_to_dic(entry))
        self.close_session(session)
        return bib

    def paper_bib(self, paper_key):
        return self.__paper_bib(paper_key)

    def __paper_ref(self, paper_key, session=True):
        self.open_session(session)
        paper = self.__get_paper(key=paper_key)
        bib = []
        for entry in paper.references:
            bib.append(self.__paper_to_dic(entry))
        self.close_session(session)
        return bib

    def paper_ref(self, paper_key):
        return self.__paper_ref(paper_key)

    def __paper_authors(self, paper_key, session=True):
        self.open_session(session)
        paper = self.__get_paper(key=paper_key)
        authors = []
        for entry in paper.authors:
            authors.append(self.__author_to_dic(entry))
        self.close_session(session)
        return authors

    def paper_authors(self, paper_key):
        return self.__paper_authors(paper_key)

    @staticmethod
    def __author_to_dic(author):
        dic = {}
        dic["key"] = author.key
        dic["name"] = author.name
        dic["surname"] = author.surname
        dic["comment"] = author.comment
        return dic

    def author_to_dic(self, author_key, session=True):
        self.open_session(session)
        author = self.__get_author(key=author_key)
        dic = self.__author_to_dic(author)
        self.close_session(session)
        return dic

    @staticmethod
    def __venue_to_dic(venue):
        dic = {}
        dic["key"] = venue.key
        dic["name"] = venue.name
        return dic

    def venue_to_dic(self, venue_key, session=True):
        self.open_session(session)
        venue = self.__get_venue(key=venue_key)
        dic = self.__venue_to_dic(venue)
        self.close_session(session)
        return dic

    @staticmethod
    def __tag_to_dic(tag):
        dic = {}
        dic["key"] = tag.key
        dic["name"] = tag.name
        return dic

    def tag_to_dic(self, tag_key, session=True):
        self.open_session(session)
        tag = self.__get_tag(key=tag_key)
        dic = self.__tag_to_dic(tag)
        self.close_session(session)
        return dic

    def __open_pdf(self, paper_key, session=True):
        self.open_session(session)
        paper = self.__get_paper(key=paper_key)
        paper_pdf_path = paper.pdf_path
        self.close_session(session)
        path = os.path.abspath(paper_pdf_path)
        os.system("open {0}".format(path))

    def open_pdf(self, paper_key):
        self.__open_pdf(paper_key)

    def __list_papers(self, tags=None, authors=None, not_tags=None, invert=False, as_dict=True, session=True):
        self.open_session(session)
        if invert:
            q = self.session.query(Paper.key)
        else:
            q = self.session.query(Paper)
        if tags is not None or not_tags is not None:
            q = q.join(tag_table).join(Tag)
            if tags is not None:
                q = q.filter(Tag.key.in_(tags))
            if not_tags is not None:
                q = q.filter(~ Tag.key.in_(not_tags))
        if authors is not None:
            q = q.join(authorship_table).join(Author).filter(Author.key.in_(tags))
        if invert:
            q = self.session.query(Paper).filter(~Paper.key.in_(q))
        papers = q.all()
        if as_dict:
            papers = [self.__paper_to_dic(i) for i in papers]
        self.close_session(session)
        return papers

    def list_papers(self, tags=None, authors=None, not_tags=None, invert=False, names=True):
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
        result = self.__list_papers(tags, authors, not_tags, invert)
        if names:
            result = [i["name"] for i in result]
        return result

    def __list_tags(self, session=True):
        self.open_session(session)
        tags = [i.name for i in self.session.query(Tag)]
        self.close_session(session)
        return tags

    def list_tags(self):
        return self.__list_tags()

    def __list_venues(self, session=True):
        self.open_session(session)
        tags = [i.name for i in self.session.query(Venue)]
        self.close_session(session)
        return tags

    def list_venues(self):
        return self.__list_tags()

    def __delete_paper(self, key, session=True):
        self.open_session(session)
        paper = self.session.query(Paper).filter(Paper.key == key).one()
        self.session.delete(paper)
        self.close_session(session)

    def delete_paper(self, key):
        self.__delete_paper(key)

    def __search_paper(self, name, session=True):
        self.open_session(session)
        paper = self.session.query(Paper).all()
        result = []
        for i in paper:
            if fuzz.token_set_ratio(i.name, name) > 90:
                result.append((i.key, i.name))
        self.close_session(session)
        return result

    def search_paper(self, name):
        return self.__search_paper(name)

    def __paper_list_tag(self, paper_key, session=True):
        self.open_session(session)
        tags = self.session.query(Tag).join(tag_table).join(Paper).filter(Paper.key == paper_key).all()
        tags = [self.__tag_to_dic(i) for i in tags]
        self.close_session(session)
        return tags

    def paper_lits_tag(self, paper_key):
        return self.__paper_list_tag(paper_key)
    #
    # def add_paper(self, name, year=None, month=None, doi=None, session=True):
    #     self.open_session(session)
    #     paper = Paper(name=name, doi=doi, year=year, month=month)
    #     self.session.add(paper)
    #     self.close_session(session)
    #     return self.get_paper_key(name)
    #
    # def edit_paper(self, paper_key, name=None, doi=None, year=None, month=None, session=True):
    #     self.open_session(session)
    #     paper = self.session.query(Paper).filter(Paper.key == paper_key)
    #     if name is not None:
    #         paper.name = name
    #     if doi is not None:
    #         paper.doi = doi
    #     if year is not None:
    #         paper.year = year
    #     if month is not None:
    #         paper.month = month
    #     self.close_session(session)
    #
    # def get_paper(self, paper, doi=None, session=True):
    #     self.open_session(session)
    #     if isinstance(paper, Paper):
    #         result = paper
    #     elif isinstance(paper, int):
    #         result = self.get_paper_by_key(paper, False)
    #     else:
    #         result = self.get_paper_by_name(paper, doi, False)
    #     self.close_session(session)
    #     return result
    #
    # def get_paper_by_name(self, name, doi=None, session=True):
    #     self.open_session(session)
    #     if doi is None:
    #         q = self.session.query(Paper).filter(Paper.name == name)
    #     else:
    #         q = self.session.query(Paper).filter(Paper.doi == doi)
    #     result = q.one()
    #     if session:
    #         result = result.__dict__
    #     self.close_session(session)
    #     return result
    #
    # def get_paper_key(self, name, doi=None, session=True):
    #     result = self.get_paper(name, doi, session)
    #     try:
    #         return result.key
    #     except AttributeError:
    #         return result["key"]
    #
    # def get_paper_by_key(self, key, session=True):
    #     self.open_session(session)
    #     q = self.session.query(Paper).filter((Paper.key == key))
    #     result = q.one()
    #     if session:
    #         result = result.__dict__
    #     self.close_session(session)
    #     return result
    #
    # def add_author(self, name, surname, comment=None, session=True):
    #     self.open_session(session)
    #     author = Author(name=name, surname=surname, comment=comment)
    #     self.session.add(author)
    #     self.close_session(session)
    #     return self.get_author_key(name, surname, comment)
    #
    # def edit_author(self, author_key, name=None, surname=None, comment=None, session=True):
    #     self.open_session(session)
    #     author = self.session.query(Author).filter(Author.key == author_key)
    #     if name is not None:
    #         author.name = name
    #     if surname is not None:
    #         author.surname = surname
    #     if comment is not None:
    #         author.comment = comment
    #     self.close_session(session)
    #
    # def get_author(self, name, surname, comment=None, session=True):
    #     self.open_session(session)
    #     q = self.session.query(Author).filter((Author.name == name) & (Author.surname == surname))
    #     if comment is not None:
    #         q = q.filter(Author.comment == comment)
    #     result = q.one()
    #     if session:
    #         result = result.__dict__
    #     self.close_session(session)
    #     return result
    #
    # def get_author_key(self, name, surname, comment=None, session=True):
    #     result = self.get_author(name, surname, comment, session)
    #     try:
    #         return result.key
    #     except AttributeError:
    #         return result["key"]
    #
    # def get_author_by_key(self, key, session=True):
    #     self.open_session(session)
    #     q = self.session.query(Author).filter((Author.key == key))
    #     result = q.one()
    #     if session:
    #         result = result.__dict__
    #     self.close_session(session)
    #     return result
    #
    # def add_venue(self, name, session=True):
    #     self.open_session(session)
    #     venue = Venue(name=name)
    #     self.session.add(venue)
    #     self.close_session(session)
    #     return self.get_venue_key(name)
    #
    # def get_venue(self, name, session=True):
    #     self.open_session(session)
    #     q = self.session.query(Venue).filter((Venue.name == name))
    #     result = q.one()
    #     if session:
    #         result = result.__dict__
    #     self.close_session(session)
    #     return result
    #
    # def get_venue_key(self, name, session=True):
    #     result = self.get_venue(name, session)
    #     try:
    #         return result.key
    #     except AttributeError:
    #         return result["key"]
    #
    # def get_venue_by_key(self, key, session=True):
    #     self.open_session(session)
    #     q = self.session.query(Venue).filter((Venue.key == key))
    #     result = q.one()
    #     if session:
    #         result = result.__dict__
    #     self.close_session(session)
    #     return result
    #
    # def add_author_to_paper(self, paper, author, session=True):
    #     self.open_session(session)
    #     if not isinstance(paper, Paper):
    #         paper = self.get_paper_by_key(paper, False)
    #     if not isinstance(author, Author):
    #         paper = self.get_author_by_key(author, False)
    #     paper.authors.append(author)
    #     self.close_session(session)
    #
    # def add_paper_to_venue(self, venue, paper, session=True):
    #     self.open_session(session)
    #     if not isinstance(paper, Paper):
    #         paper = self.get_paper_by_key(paper, False)
    #     if not isinstance(venue, Venue):
    #         paper = self.get_venue_by_key(venue, False)
    #     venue.papers.append(paper)
    #     self.close_session(session)
    #
    # def add_pdf_to_paper(self, paper, pdf_path=None, session=True):
    #     if pdf_path is None:
    #         downloads = [os.path.join(self.download_dir, file) for file in os.listdir(self.download_dir)
    #                      if file[0] != "."]
    #         if len(downloads) > 0:
    #             pdf_path = max(downloads, key=os.path.getatime)
    #         else:
    #             raise FileNotFoundError
    #     self.open_session(session)
    #     if not isinstance(paper, Paper):
    #         paper = self.get_paper_by_key(paper, False)
    #     path = os.path.join(self.archive_path, str(paper.key) + ".pdf")
    #     os.rename(pdf_path, path)
    #     paper.pdf_path = path
    #     self.close_session(session)
    #
    # def add_citation_to_paper(self, paper, citation, session=True):
    #     self.open_session(session)
    #     if not isinstance(paper, Paper):
    #         paper = self.get_paper_by_key(paper, False)
    #     if not isinstance(citation, Paper):
    #         citation = self.get_paper_by_key(citation, False)
    #     paper.cites.append(citation)
    #     self.close_session(session)
    #
    # def get_paper_bibliography(self, paper, session=True):
    #     self.open_session(session)
    #     paper = self.get_paper(paper, session=False)
    #
    #
    #     self.close_session()
    #
    # def print_paper(self, key):
    #     self.sprint(self.get_paper_by_key(key))
    #
    # def print_author(self, key):
    #     self.sprint(self.get_author_by_key(key))
    #
    # def print_venue(self, key):
    #     self.sprint(self.get_venue_by_key(key))
    #
    # @staticmethod
    # def sprint(result, non_values=False):
    #     if not isinstance(result, list):
    #         result = [result]
    #     for i in result:
    #         if not isinstance(i, dict):
    #             entry = i.__dict__
    #         else:
    #             entry = i
    #         if not non_values:
    #             data = {k: v for k, v in entry.items() if v is not None}
    #         else:
    #             data = entry
    #         pprint(data)
    #
    # @staticmethod
    # def open_comment(paper):
    #     path = os.path.abspath(paper.comment_path)
    #     os.system("open {0}".format(path))
    #
    # @staticmethod
    # def open_pdf(paper):
    #     path = os.path.abspath(paper.pdf_path)
    #     os.system("open {0}".format(path))