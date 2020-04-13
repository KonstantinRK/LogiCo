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

model_table = Table("model_table", Base.metadata,
                       Column("model_citation_key", Integer, primary_key=True),
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

    references = relationship(
        "Paper",
        secondary=model_table,
        primaryjoin=key == model_table.c.citation_key,
        secondaryjoin=key == model_table.c.paper_key,
        backref=backref("referenced_by"))



class Author(Base):
    __tablename__ = "author"
    key = Column(Integer, primary_key=True)
    name = Column(String)
    surname = Column(String)
    comment = Column(String)
    papers = relationship("Paper", secondary=authorship_table, back_populates="authors")


class Tag(Base):
    __tablename__ = "tag"
    key = Column(Integer, primary_key=True)
    name = Column(String, unique=True)

    papers = relationship("Paper", secondary=tag_table, back_populates="tags")


class Venue(Base):
    __tablename__ = "venue"
    key = Column(Integer, primary_key=True)
    name = Column(String, unique=True)

    papers = relationship("Paper", back_populates="venue")

