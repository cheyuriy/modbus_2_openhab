import pprint
import os
import sys
import codecs
import re
from arpeggio import ParserPython, visit_parse_tree, ZeroOrMore, EOF, OneOrMore, PTNodeVisitor
from arpeggio import RegExMatch as _
import uuid

#Segnetics config grammar
def segnetics_file(): return ZeroOrMore([comment_entry, request_entry]), EOF
def comment_entry(): return _(r'^;.+')
def request_entry(): return _(r'^\[.+\]'), direction_param, type_param, baudrate_param, address_param, period_param, OneOrMore(var_param)
def direction_param(): return "Direction=", direction_value
def direction_value(): return _(r'read/write|read')
def type_param(): return "Type=", type_value
def type_value(): return _(r'bit|reg')
def baudrate_param(): return "Baudrate=", _(r'\d+')
def address_param(): return "Address=", _(r'\d+')
def period_param(): return "Period=", _(r'\d+')
def var_param(): return _(r'var\d+='), var_address_value, "#", var_type_value, "#", var_name_value
def var_address_value(): return _(r'[0-9a-f]+')
def var_type_value(): return _(r'bool|long|int|real')
def var_name_value(): return _(r'.+')

type_sizes = dict(bool=1, int=1, long=2, real=2)
type_conversions = dict(bool='bit',
                        int='uint16',
                        long='uint32_swap',
                        real='float32_swap')

class SegneticsVisitor(PTNodeVisitor):

    def visit_var_name_value(self, node, children):
        return re.sub("\r", "", node.value)

    def visit_var_type_value(self, node, children):
        return node.value

    def visit_var_address_value(self, node, children):
        return int(node.value, 16)

    def visit_var_param(self, node, children):
        return dict(name=children.var_name_value[0],
                    type=type_conversions[children.var_type_value[0]], 
                    size=type_sizes[children.var_type_value[0]],
                    addr=children.var_address_value[0],
                    id=uuid.uuid4())
    
    def visit_period_param(self, node, children):
        return None

    def visit_address_param(self, node, children):
        return None

    def visit_baudrate_param(self, node, children):
        return None

    def visit_type_value(self, node, children):
        return node.value

    def visit_type_param(self, node, children):
        return children.type_value[0]

    def visit_direction_value(self, node, children):
        return node.value

    def visit_direction_param(self, node, children):
        return children.direction_value[0]

    def visit_request_entry(self, node, children):
        request_type = None
        type_param = children.type_param[0]
        direction_param = children.direction_param[0]
        if (type_param == "bit" and direction_param == "read"):
            request_type = "discrete"
        if (type_param == "bit" and direction_param == "read/write"):
            request_type = "coil"
        if (type_param == "reg" and direction_param == "read"):
            request_type = "input"
        if (type_param == "reg" and direction_param == "read/write"):
            request_type = "holding"
        
        request_vars = sorted(children.var_param, key=lambda var: var['addr'])

        start = request_vars[0]['addr']
        size = request_vars[-1]['addr'] - start + request_vars[-1]['size']

        return (request_type, dict(vars=request_vars, start=start, size=size, id=uuid.uuid4()))

    def visit_comment_entry(self, node, children):
        return None

    def visit_segnetics_file(self, node, children):
        return dict(list(children))


def parse(file, enc):
    with codecs.open(file, "r", encoding=enc) as opened_file:
        opened_file_content = opened_file.read()
    parser = ParserPython(segnetics_file, reduce_tree=True)
    parse_tree = visit_parse_tree(parser.parse(opened_file_content), SegneticsVisitor())
    return parse_tree
