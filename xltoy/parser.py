# inspired to: excelExpr by Paul McGuire
from openpyxl.utils.cell import coordinate_to_tuple
from . import log
from .utils import de_dollar
from pyparsing import (
    CaselessKeyword, Word, alphas, alphanums, nums, Optional, Group, oneOf, Forward,
    infixNotation, opAssoc, dblQuotedString, delimitedList, Combine, Literal, QuotedString, ParserElement,
    LineEnd, pyparsing_common as ppc, nestedExpr)
ParserElement.enablePackrat()



class Parser:
    def __init__(self, collector=None):
        self.current_sheet = None
        self.collector = collector
        EQ, LPAR, RPAR, COLON, COMMA, EXCL, DOLLAR = map(Literal, "=():,!$")
        COMPARISON_OP = oneOf("= < > >= <= != <>")('op')
        multOp = oneOf("* /")
        addOp = oneOf("+ -")
        words = Word(alphas, alphanums + '_')
        sheetRef = words | QuotedString("'", escQuote="''")
        colRef = Optional(DOLLAR) + Word(alphas, max=2)
        rowRef = Optional(DOLLAR) + Word(nums)

        # Atomic element for cell
        cellAtom = Group(
            Optional(sheetRef("sheet") + EXCL) + \
            Combine(colRef + rowRef)("pos")
        )

        #Range
        cellRange = Group(
            cellAtom("start") + COLON + cellAtom("end")
        )("range")

        # Single cell with action
        cellRef = cellAtom("cell")\
                  .setParseAction(self.cell_action)

        expr = Forward()

        # Conditions
        condExpr = expr + Optional(COMPARISON_OP.setParseAction(self.equal_as_comparison_action) + expr)

        # If function
        ifFunc = (
                CaselessKeyword("if")
                + LPAR
                + Group(condExpr)("condition")
                + COMMA
                + Group(expr)("if_true")
                + COMMA
                + Group(expr)("if_false")
                + RPAR)

        # Functions
        def stat_function(name, obj=expr, empty=False):
            if empty:
                x = Group(LPAR + RPAR)
            else:
                x = Group(LPAR + delimitedList(obj, combine=True)('elem_list') + RPAR)
            return CaselessKeyword(name)('function_name') + x

        sumFunc = stat_function("sum")
        minFunc = stat_function("min")
        maxFunc = stat_function("max")
        aveFunc = stat_function("ave")
        sqrFunc = stat_function("sqrt")
        lenFunc = stat_function("sqrt")
        andFunc = stat_function("and", obj=condExpr).setParseAction(self.logic_operation)
        orFunc  = stat_function("or", obj=condExpr).setParseAction(self.logic_operation)
        randFunc= stat_function("rand",empty=True)
        unknowFunc = words + Group(LPAR + (delimitedList(expr|cellRange) | cellRange | expr) + RPAR)

        functions = ifFunc | sumFunc | minFunc | maxFunc | aveFunc | sqrFunc | lenFunc | randFunc | \
                    andFunc| orFunc | unknowFunc

        numericLiteral = ppc.number

        # Numeric Expressions
        operand = numericLiteral | functions | cellRange | cellRef | words
        arithExpr = infixNotation(
            operand, [
                (addOp, 1, opAssoc.RIGHT),
                (multOp, 2, opAssoc.LEFT),
                (addOp, 2, opAssoc.LEFT),
                ('^', 2, opAssoc.LEFT)],
            lpar=LPAR, rpar=RPAR
        )

        # Text Expressions
        textOperand = dblQuotedString | cellRef
        textExpr = infixNotation(textOperand, [("&", 2, opAssoc.LEFT), ])

        # Final syntax
        atom = arithExpr | textExpr | nestedExpr('(', ')')
        expr << atom
        bnf = Optional(EQ|addOp) + expr + LineEnd()
        self.bnf = bnf
        # self.bnf.setDebug(True)

    def transform(self, *args, **kwargs):
        """
        a simple hook to transformString function from pyparsing

        :param args: delegated to child function
        :param kwargs: delegated to child function
        :return: delegated to child function
        """
        return self.bnf.transformString(*args, **kwargs)

    def parse(self, *args, **kwargs):
        ret = self.bnf.parseString(*args, **kwargs)
        # print(ret.dump(full=True))
        return ret

    def set_current(self, sheet, position):
        self.current_sheet = sheet
        self.current_cell = position
        self.current_row, self.current_col = coordinate_to_tuple(position)
        self.current_pos_to_label = self.collector.pos_to_label[sheet]
        self.current_sheet_is_vertical = self.collector.sheet_is_vertical[sheet]

    def logic_operation(self, tok):
        if tok[0] == 'and':
            py_func = 'all'
        elif tok[0] == 'or':
            py_func = 'any'
        else:
            raise('GGG')

        py_values = ''.join(tok[1].elem_list)
        return f"{py_func}([{py_values}])"

    def equal_as_comparison_action(self,tok):
        """
        Comparison = must be pythonic comparison ==

        :param tok: one of = > < >= <= comparision operators
        :return:
        """
        if tok.op == '=':
            return '=='

    def cell_action(self, tok):
        """
        over all token occurrence we do transliteration action!

        tok is a cell reference, in these cases we can transliterate syntax in a
        python way.
        Depending on flag self.current_sheet_is_vertical we choose the right
        direction for the time stepper

        :param tok: exel token like E5, $AA$12
        :return: transliterated syntax
        """
        if self.collector is not None:
            if not self.current_sheet:
                raise ValueError("ggg")

            sheet = tok.cell.sheet
            position = tok.cell.pos
            if sheet:
                # maybe from other sheet!
                if sheet != self.current_sheet:
                    log.warning(f"In sheet {self.current_sheet} cell {self.current_cell} token {tok} read input from external sheet. Treated as exogenous value")
                    val = self.collector.wb_data[sheet][position].value
                    return val

            row, col = coordinate_to_tuple(de_dollar(position))
            offset = col if self.current_sheet_is_vertical else row
            if offset in self.current_pos_to_label:
                label = self.current_pos_to_label[offset]
            else:
                val = self.collector.wb_data[self.current_sheet][position].value
                log.info("Found params sheet {} cell {}:{}".format(self.current_sheet,tok.cell.pos,val))
                return val

            delta_time = row-self.current_row if self.current_sheet_is_vertical else col-self.current_col
            if delta_time:
                return("{}[T{}]".format(label,delta_time))
            else:
                return("{}[T]".format(label))
