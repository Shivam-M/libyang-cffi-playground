import os
import _test
from _test import ffi as ffi


def str2c(py_string, encode=True):
    if py_string is None:
        return ffi.NULL 
    if encode:
        py_string = py_string.encode("utf-8")
    return ffi.new("char []", py_string)


def c2str(c_string, decode=True):
    if c_string == ffi.NULL:
        return None
    c_string = ffi.string(c_string)
    if decode:
        c_string = c_string.decode("utf-8")
    return c_string


class Module:
    def __init__(self, data, context) -> None:
        self._data = data
        self._context = context

    def print(self, output=os.sys.stdout):
        ly_out = ffi.new("struct ly_out**")
        _test.lib.ly_out_new_fd(output.fileno(), ly_out)
        _test.lib.lys_print_module(ly_out[0], self._data, _test.lib.LYS_OUT_TREE, 0, 0)


class Context:
    def __init__(self) -> None:
        context_pointer = ffi.new("struct ly_ctx**")
        _test.lib.ly_ctx_new(ffi.NULL, _test.lib.LY_CTX_NO_YANGLIBRARY, context_pointer)
        self._data = context_pointer[0]
    
    def add_search_path(self, search_path: str):
        _test.lib.ly_ctx_set_searchdir(self._data, str2c(search_path))
    
    def load_module(self, module_path: str):
        return Module(_test.lib.ly_ctx_load_module(self._data, str2c(module_path), ffi.NULL, ffi.NULL), self)
    
    def load_data(self, data_path: str):
        top_node = ffi.new("struct lyd_node**")
        ly_in = ffi.new("struct ly_in**")
        data_format = _test.lib.LYD_JSON if data_path.endswith("json") else _test.lib.LYD_XML

        _test.lib.ly_in_new_filepath(str2c(data_path), 0, ly_in)
        _test.lib.lyd_parse_data(self._data, ffi.NULL, ly_in[0], data_format, 0, 0, top_node)

        return Node(top_node[0], self)

    def resolve_type(self):
        pass

    def get_differences(self, first_node, second_node):
        return Node(_test.lib.get_differences(first_node._data, second_node._data), self)

    def evaluate_differences(self, first_node, second_node, diff_node):
        changes = {}
        for node in diff_node.get_following_nodes():
            xpath = node._xpath
            value_first = first_node.get_value_at_xpath(xpath)
            value_second = second_node.get_value_at_xpath(xpath)
            changes[xpath] = {}

            if value_first:
                changes[xpath]["action"] = "removed"
                changes[xpath]["old_value"] = value_first

            if value_second:
                changes[xpath]["action"] = "created"
                changes[xpath]["new_value"] = value_second

            if value_first and value_second:
                changes[xpath]["action"] = "changed"

            if value_first == value_second:
                del changes[xpath]
        return changes
    
    ## move create/add methods to leaflistnode
    def create_list_node(self, parent, name, values):
        list_node = ffi.new("struct lyd_node**")
        _test.lib.lyd_new_list(parent._data, ffi.NULL, str2c(name), 0, list_node, *[str2c(value) for value in values])
        return Node(list_node[0], self)

    def create_inner_node(self, parent, name):
        inner_node = ffi.new("struct lyd_node**")
        _test.lib.lyd_new_inner(parent._data, ffi.NULL, str2c(name), 0, inner_node)
        return Node(inner_node[0], self)

    def create_terminal_node(self, parent, name, value):
        terminal_node = ffi.new("struct lyd_node**")
        _test.lib.lyd_new_term(parent._data, ffi.NULL, str2c(name), str2c(value), 0, terminal_node)
        return Node(terminal_node[0], self)


class Node:
    def __init__(self, data, context: Context) -> None:
        self._data = data
        self._context = context
    
    def __getattr__(self, name: str):
        match name:
            case "_name":
                return c2str(_test.lib.lyd_node_name(self._data))
            case "_xpath":
                return c2str(_test.lib.lyd_path(self._data, 0, ffi.NULL, 0))  # store instead?
            case "_value":
                return c2str(_test.lib.lyd_get_value(self._data))
            case "_parent":
                return None

    def print(self):
        _test.lib.print_node(self._data)

    def get_following_nodes(self):
        next_node = self._data
        while (next_node):
            if next_node := _test.lib.get_next_node(next_node):
                yield Node(next_node, self._context)

    def get_node_at_xpath(self, xpath):
        return Node(_test.lib.get_node_at_xpath(self._data, str2c(xpath)), self._context)

    def get_value_at_xpath(self, xpath):
        node = self.get_node_at_xpath(xpath)
        return node._value if node else None

    def get_children(self):
        child = _test.lib.lyd_child(self._data)
        while child:
            yield Node(child, self._context)
            child = _test.lib.get_sibling(child)

    def __eq__(self, other):
        return self._data == other._data

    def __del__(self):
        pass


class LeafNode(Node):
    def __init__(self, data, context: Context) -> None:
        super(data, context)
    
    def set_value(self, value: str):
        pass


class LeafListNode(Node):
    def __init__(self, data, context: Context) -> None:
        super(data, context)

    def __iter__(self):
        yield None


class ContainerNode(Node):
    def __init__(self, data, context: Context) -> None:
        super(data, context)

    def __iter__(self):
        yield None


class Test:
    def print_nodes_recursively(node: Node):
        _test.lib.print_nodes_recursively(node._data)
