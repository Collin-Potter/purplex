import functools
import logging

from ply import yacc

logger = logging.getLogger(__name__)


def attach(production):
    def wrapper(func):
        if not hasattr(func, '_productions'):
            func._productions = []
        func._productions.append(production)
        return func
    return wrapper


class Node(object):
    def __init__(self, parser, *args):
        self.parser = parser
        self.children = args

    def __repr__(self):
        return '{}{}'.format(self.__class__.__name__, repr(self.children))


class MagicParser(object):
    def add(self, parser, production, node_cls):
        def p_something(t):
            nargs = len(t.slice)
            t[0] = node_cls(parser, *[t[i] for i in range(1, nargs)])
        func_name = 'p_{}_{}{}'.format(production.split()[0],
                                        node_cls.__name__,
                                        abs(hash(production)))
        p_something.__name__ = func_name
        setattr(self, func_name, p_something)
        getattr(self, func_name).__doc__ = production


class ParserBase(type):
    def __new__(cls, name, bases, dct):
        productions = {}

        for name, attr in dct.items():
            if hasattr(attr, '_productions'):
                for production in attr._productions:
                    productions[production] = attr

        dct['_productions'] = productions
        return type.__new__(cls, name, bases, dct)


class Parser(metaclass=ParserBase):
    LEXER = None

    @classmethod
    def attach(cls, production):
        def wrapper(node_cls):
            cls._productions[production] = node_cls
            return node_cls
        return wrapper

    def __init__(self, start=None, debug=False):
        self._parser = self._build(start, debug)

    def _build(self, start, debug):
        magic = MagicParser()
        magic.tokens = list(self.LEXER.tokens.keys())

        for production, node_cls in self._productions.items():
            magic.add(self, production, node_cls)
        setattr(magic, 'p_error', self.on_error)

        yacc_logger = logger if debug else yacc.NullLogger()

        return yacc.yacc(module=magic, start=start,
                         write_tables=False, debug=False,
                         debuglog=yacc_logger, errorlog=yacc_logger)

    def parse(self, input_stream):
        lexer = self.LEXER(input_stream)

        def tokens():
            for token in lexer:
                yield token
            yield None

        tokens_gen = tokens()

        return self._parser.parse(lexer=lexer,
                                  tokenfunc=functools.partial(next, tokens_gen))

    # Implement these if you want:

    def on_error(self, p):
        '''
        Is called when PLY's yacc encounters a parsing error.
        '''
        pass