from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Table, Float, Boolean
from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship, backref
from sqlalchemy.orm import sessionmaker


Base = declarative_base()


authorship_table = Table("authorship_table", Base.metadata,
                         Column("author_key", Integer, ForeignKey("author.key")),
                         Column("paper_key", Integer, ForeignKey("paper.key")))

tag_table = Table("tag_table", Base.metadata,
                         Column("tag_key", Integer, ForeignKey("tag.key")),
                         Column("paper_key", Integer, ForeignKey("paper.key")))

citation_table = Table("citation_table", Base.metadata,
                       Column("paper_citation_key", Integer, primary_key=True),
                       Column("paper_key", Integer, ForeignKey("paper.key")),
                       Column("citation_key", Integer, ForeignKey("paper.key")))


class Paper(Base):
    __tablename__ = "paper"
    key = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    doi = Column(String, unique=True)
    year = Column(Integer)
    month = Column(Integer)
    relevant = Column(Boolean)
    access = Column(Boolean)
    comment = Column(String)
    pdf_path = Column(String)
    bibtex = Column(String)
    json = Column(String)

    venue_key = Column(Integer, ForeignKey("venue.key"))
    venue = relationship("Venue", back_populates="papers")

    authors = relationship("Author", secondary=authorship_table, back_populates="papers")
    tags = relationship("Tag", secondary=tag_table, back_populates="papers")

    cites = relationship(
        "Paper",
        secondary=citation_table,
        primaryjoin=key == citation_table.c.citation_key,
        secondaryjoin=key == citation_table.c.paper_key,
        backref=backref("cited_by"))

    def transform_to_dict(self, recursive=False):
        dic = {}
        dic["key"] = self.key
        dic["name"] = self.name
        dic["doi"] = self.doi
        dic["year"] = self.year
        dic["month"] = self.month
        dic["relevant"] = self.relevant
        dic["access"] = self.access
        dic["comment"] = self.comment
        dic["bibtex"] = self.bibtex
        dic["json"] = self.json
        dic["pdf_path"] = self.pdf_path
        if recursive:
            dic["tags"] = [i.transform_to_dict() for i in self.tags]
            dic["authors"] = [i.transform_to_dict() for i in self.authors]
            dic["cites"] = [i.transform_to_dict() for i in self.cites]
            dic["venue"] = self.venue.transform_to_dict()
        else:
            dic["tags"] = [i.name for i in self.tags]
            dic["authors"] = [i.name for i in self.authors]
            dic["cites"] = [i.name for i in self.cites]
            dic["venue"] = None if self.venue is None else self.venue.name
        return dic


class Author(Base):
    __tablename__ = "author"
    key = Column(Integer, primary_key=True)
    name = Column(String)
    surname = Column(String)
    comment = Column(String)
    json = Column(String)
    papers = relationship("Paper", secondary=authorship_table, back_populates="authors")

    def transform_to_dict(self, recursive=False):
        dic = {}
        dic["key"] = self.key
        dic["name"] = self.name
        dic["surname"] = self.surname
        dic["comment"] = self.comment
        dic["json"] = self.json
        if recursive:
            dic["papers"] = [i.transform_to_dict() for i in self.papers]
        else:
            dic["papers"] = [i.name for i in self.papers]
        return dic


class Tag(Base):
    __tablename__ = "tag"
    key = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    json = Column(String)

    papers = relationship("Paper", secondary=tag_table, back_populates="tags")

    def transform_to_dict(self, recursive=False):
        dic = {}
        dic["key"] = self.key
        dic["name"] = self.name
        dic["json"] = self.json
        if recursive:
            dic["papers"] = [i.transform_to_dict() for i in self.papers]
        else:
            dic["papers"] = [i.name for i in self.papers]
        return dic


class Venue(Base):
    __tablename__ = "venue"
    key = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    json = Column(String)
    papers = relationship("Paper", back_populates="venue")

    def transform_to_dict(self, recursive=False):
        dic = {}
        dic["key"] = self.key
        dic["name"] = self.name
        dic["json"] = self.json
        if recursive:
            dic["papers"] = [i.transform_to_dict() for i in self.papers]
        else:
            dic["papers"] = [i.name for i in self.papers]
        return dic

