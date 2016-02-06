import logging
import networkx
import collections

l = logging.getLogger(name="angr.artifacts.function_manager")

class FunctionDict(dict):
    def __init__(self, backref, *args, **kwargs):
        self._backref = backref
        super(FunctionDict, self).__init__(*args, **kwargs)

    def __missing__(self, key):
        t = Function(self._backref, key)
        t._add_block(key)
        self[key] = t
        return t

class FunctionManager(collections.Mapping):
    '''
    This is a function boundaries management tool. It takes in intermediate
    results during CFG generation, and manages a function map of the binary.
    '''
    def __init__(self, artifact):
        self._artifact = artifact
        # A map that uses function starting address as the key, and maps
        # to a function class
        self._function_map = FunctionDict(self)
        self.callgraph = networkx.DiGraph()

        # Registers used for passing arguments around
        self._arg_registers = artifact._project.arch.argument_registers

    def _genenare_callmap_sif(self, filepath):
        '''
        Generate a sif file from the call map

        :param filepath: Path of the sif file
        :return: None
        '''
        with open(filepath, "wb") as f:
            for src, dst in self.callgraph.edges():
                f.write("%#x\tDirectEdge\t%#x\n" % (src, dst))

    def _add_call_to(self, function_addr, from_addr, to_addr, retn_addr, syscall=False):
        self._function_map[function_addr]._call_to(from_addr, to_addr, retn_addr, syscall=syscall)
        self._function_map[function_addr]._add_call_site(from_addr, to_addr, retn_addr)
        self.callgraph.add_edge(function_addr, to_addr)

    def _add_return_from(self, function_addr, from_addr, to_addr=None): #pylint:disable=unused-argument
        self._function_map[function_addr]._add_return_site(from_addr)

    def _add_transition_to(self, function_addr, from_addr, to_addr):
        self._function_map[function_addr]._transit_to(from_addr, to_addr)

    def _add_return_from_call(self, function_addr, src_function_addr, to_addr):
        self._function_map[function_addr]._return_from_call(src_function_addr, to_addr)

    #
    # Dict methods
    #

    def __getitem__(self, k):
        f = self.function(name=k) if isinstance(k, str) else self.function(addr=k)
        if f is None:
            raise KeyError(k)
        return f

    def __setitem__(self, k, v):
        if not isinstance(k, int):
            raise ValueError("FunctionManager.__setitem__ keys should be addresses")
        self._function_map[k] = v

    def __delitem__(self, k):
        del self._function_map[k]

    def __len__(self):
        return len(tuple(self.__iter__()))

    def __iter__(self):
        for i in sorted(self._function_map.keys()):
            yield i

    def function(self, addr=None, name=None, create_if_not_exist=False):
        '''
        Get a function object from the function manager
        Pass one of the kwargs addr or name, with the appropriate values.
        '''
        if addr:
            if addr in self._function_map or create_if_not_exist:
                return self._function_map[addr]
        elif name:
            for func in self._function_map.itervalues():
                if func.name == name:
                    return func

        return None

    def dbg_draw(self, prefix='dbg_function_'):
        for func_addr, func in self._function_map.iteritems():
            filename = "%s%#08x.png" % (prefix, func_addr)
            func.dbg_draw(filename)

from .function import Function
