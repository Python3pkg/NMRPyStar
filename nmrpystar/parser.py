'''
@author: matt
'''
from .parse.standard import Parser
from . import concrete



def _literal(c):
    return Parser.satisfy(lambda t: t.char == c)

def _string(cs):
    return Parser.all(map(_literal, cs))

def extract(cs):
    '''
    Returns a string, containing all of the characters
      (without their meta information)
    '''
    return ''.join([x.char for x in cs])

def posFirst(cs):
    return cs[0].meta

def oneOf(cs):
    return Parser.satisfy(lambda x: x.char in cs)

NEWLINES, BLANKS = set('\n\r\f'), set(' \t')
SPACES = NEWLINES.union(BLANKS)
SPECIALS = SPACES.union(set('"#\'_')) # double-quote, pound, single-quote, underscore

newline, blank, space, special = map(oneOf, [NEWLINES, BLANKS, SPACES, SPECIALS])

_identifier  =  Parser.app(concrete.Key, _literal('_').fmap(lambda c: c.meta), space.not1().many1().fmap(extract))


sc, sq, dq = map(_literal, ';\'"')
endsc = newline.seq2R(sc)
def scAction(op, body, _):
    return concrete.Value(op.meta, extract(body))

scstring = Parser.app(scAction, sc, endsc.not1().many0(), endsc)

end = Parser.item.not0()
nonEndingSq = sq.seq2L(space.plus(end).not0())
nonEndingDq = dq.seq2L(space.plus(end).not0())
#def sqAction(op, body, _):
#    return concrete.Value(op.meta, extract(body))
#
#sqstring = Parser.app(sqAction, sq, nonEndingSq.plus(sq.not1()).many0(), sq)

def sqRest(o):
    def action(b, _):
        return concrete.Value(o.meta, extract(b))
    newlineErr = newline.seq2L(Parser.error(('no newlines in single-quoted strings', o.meta)))
    return Parser.app(action,
                      nonEndingSq.plus(sq.plus(newlineErr).not1()).many0(),
                      sq).commit(('missing end single-quote', o.meta))

sqstring = sq.bind(sqRest)

def dqRest(o):
    def action(b, _):
        return concrete.Value(o.meta, extract(b))
    newlineErr = newline.seq2L(Parser.error(('no newlines in double-quoted strings', o.meta)))
    return Parser.app(action, 
                      nonEndingDq.plus(dq.plus(newlineErr).not1()).many0(),
                      dq).commit(('missing end double-quote', o.meta))

dqstring = dq.bind(dqRest)

_value = Parser.any([sqstring, dqstring, scstring]) # unquoted taken care of by uq_or_keyword rule


comment = Parser.app(lambda o, b: concrete.Comment(o.meta, extract(b)), _literal('#'), newline.not1().many0())
whitespace = blank.plus(newline).many1().fmap(lambda b: concrete.Whitespace(b[0].meta, extract(b)))


def uqOrKey(c, cs):
    return (c.meta, extract([c] + cs))

def classify(v):
    '''
    Classifications:
     - reserved: /stop_/, /loop_/, /save_/, /save_.+/, /data_.+/
     - illegal:  /stop_.+/, /loop_.+/, /data_/
     - value:  everything else
    '''
    meta, string = v
    err, pure, Reserved = Parser.error, Parser.pure, concrete.Reserved
    if string[:5] == "stop_":
        if len(string) != 5:
            return err(('invalid keyword', meta))
        return pure(Reserved(meta, "stop", ''))
    elif string[:5] == "save_":
        if len(string) != 5:
            return pure(Reserved(meta, "saveopen", string[5:]))
        return pure(Reserved(meta, "saveclose", ''))
    elif string[:5] == "loop_":
        if len(string) != 5:
            return err(('invalid keyword', meta))
        return pure(Reserved(meta, "loop", ''))
    elif string[:5] == "data_":
        if len(string) == 5:
            return err(('invalid keyword', meta))
        return pure(Reserved(meta, "dataopen", string[5:]))
    return pure(concrete.Value(meta, string))
        
_uqvalue_or_keyword = Parser.app(uqOrKey, special.not1(), space.not1().many0()).bind(classify)


def munch(p):
    return whitespace.plus(comment).many0().seq2R(p)

uqvalue_or_keyword = munch(_uqvalue_or_keyword)

identifier  =  munch(_identifier)
value       =  munch(_value).plus(uqvalue_or_keyword.check(lambda val: isinstance(val, concrete.Value)))


def keyword(rtype):
    return uqvalue_or_keyword.check(lambda val: isinstance(val, concrete.Reserved) and val.rtype == rtype)


def loopRest(op):
    def action(ids, vals, cls):
        return concrete.Loop(op.start, ids, vals, cls.start)
    return Parser.app(action, 
                      identifier.many0(), 
                      value.many0(), 
                      keyword('stop')).commit(('loop: unable to parse', op.start))
                      
loop = keyword('loop').bind(loopRest) 

def datumRest(i):
    return value.fmap(lambda v: concrete.Datum(i, v)).commit(('datum: missing value', i.start))

datum = identifier.bind(datumRest)

def saveRest(op):
    def action(its, c):
        return concrete.Save(op.start, op.string, its, c.start)
    return Parser.app(action,
                      loop.plus(datum).many0(), 
                      keyword('saveclose')).commit(('save: unable to parse', op.start))

save = keyword('saveopen').bind(saveRest)

data = Parser.app(lambda o, ss: concrete.Data(o.start, o.string, ss), keyword('dataopen'), save.many0())

def endCheck(xs):
    if xs.isEmpty():
        return Parser.pure(None)
    return Parser.error(('unparsed input remaining', xs.first().meta))

nmrstar = data.seq2L(munch(Parser.get.bind(endCheck)))
