import contextlib
import logging
import re

from sqlalchemy import exc
from sqlalchemy.engine import create_engine
from sqlalchemy.event.api import listen
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.ext.declarative.api import declarative_base, declared_attr
from sqlalchemy.orm.scoping import scoped_session
from sqlalchemy.orm.session import sessionmaker
from sqlalchemy.sql import expression
from sqlalchemy.sql.expression import select
from sqlalchemy.sql.schema import Column
from sqlalchemy.sql.sqltypes import Integer, DateTime

import config


def initialize():
    global Session
    Session = None
    if not config.DATABASE_URI:
        logging.error("Cannot initialize the database service: "
                      "DATABASE_URI not configured")
        return
    logging.info("Initializing database connection to " + config.DATABASE_URI)
    try:
        engine = create_engine(config.DATABASE_URI, pool_size=10)
        FlipperBase.metadata.create_all(engine)
    except SQLAlchemyError:
        logging.exception("Failed to initialize database:")
        return
    Session = scoped_session(sessionmaker(bind=engine))
    listen(engine, "engine_connect", ping_engine)


def ping_engine(connection, branch):
    if branch:
        return
    # Save should_close_with_result
    save_should_close_with_result = connection.should_close_with_result
    connection.should_close_with_result = False
    try:
        # Attempt to execute a dummy query
        connection.scalar(select([1]))
    except exc.DBAPIError as err:
        logging.warn('SQL engine disconnection detected')
        if err.connection_invalidated:
            logging.info('Attempting to restart SQL engine')
            connection.scalar(select([1]))
        else:
            raise
    finally:
        # Restore should_close_with_result
        connection.should_close_with_result = save_should_close_with_result


@contextlib.contextmanager
def get_session():
    if not Session:
        raise ValueError("Tried to get a database session "
                         "but database is not initialized")
    try:
        session = Session()
        yield session
    finally:
        # Rollback uncommitted transactions if any:
        if len(session.transaction._iterate_self_and_parents()) > 0:
            session.rollback()


class utcnow(expression.FunctionElement):
    type = DateTime()


@compiles(utcnow, 'postgresql')
def pg_utcnow(element, compiler, **kw):
    return "TIMEZONE('utc', CURRENT_TIMESTAMP)"


Base = declarative_base()


class FlipperBase(Base):
    __abstract__ = True

    _tablename = None

    @declared_attr
    def __tablename__(self):
        if self._tablename is None:
            s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', self.__name__)
            self._tablename = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
        return self._tablename

    id = Column(Integer, primary_key=True)
    created_on = Column(DateTime, nullable=False,
                        default=utcnow())
    updated_on = Column(DateTime, nullable=False,
                        default=utcnow(), onupdate=utcnow())
