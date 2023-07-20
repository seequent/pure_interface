import types
import unittest

import pure_interface
from pure_interface import interface
from tests import test_function_sigs


def func1(*, a, b):  # kw only no defaults
    pass


def func2(*, a, b='b'):  # kw only with default
    pass


def func3(a, *, b, c):  # p_or_kw and kw_only
    pass


def func4(a='a', *, b):
    pass


def func5(a, *, b='b'):
    pass


def all_func(*args, **kwargs):
    pass


def no_kw_only(a, b):
    pass


def no_kw_only_rev(b, a):
    pass


def no_args():
    pass


def func_bad_name(*, a, z='z'):
    pass


def func1ex(*, a, b, c='c'):
    pass


def func1ex2(*, b, a):  # order doesn't matter
    pass


def func1ex3(*, b='b', a):
    pass


def func3ex(a, d='d', *, b, c):  # p_or_kw and kw_only
    pass


def func3ex2(a, *, b, c, d='d'):  # p_or_kw and kw_only
    pass


def func5ex(a, *, b='b', c='c'):
    pass


def _test_call(spec_func, spec_sig, impl_func, impl_sig, args, kwargs):
    spec_func(*args, **kwargs)
    num_po_args = len([p for p in spec_sig.parameters.values()
                       if p.kind == p.POSITIONAL_ONLY])
    try:
        impl_func(*args, **kwargs)
    except TypeError:
        return False
    try:
        ba = impl_sig.bind(*args, **kwargs)
    except TypeError:
        return False
    non_po_args = ba.args[num_po_args:]
    if not all(k == ba.arguments[k] for k in non_po_args
               if k not in ('args', 'kwargs')):
        return False
    kwargs = ba.arguments.get('kwargs', {})
    if not all(k == v for k, v in kwargs.items()):
        return False
    return True


def test_call(spec_func: types.FunctionType, impl_func: types.FunctionType) -> bool:
    """ call the function with parameters as indicated by the parameter list
    """
    spec_sig = pure_interface.interface.signature(spec_func)
    impl_sig = pure_interface.interface.signature(impl_func)

    pos_only = [p for p in spec_sig.parameters.values() if p.kind == p.POSITIONAL_ONLY]
    num_po = len(pos_only)
    po_args = [p.name for p in pos_only]
    po_req = [p.name for p in pos_only if p.default is p.empty]

    pos_or_kw = [p for p in spec_sig.parameters.values() if p.kind == p.POSITIONAL_OR_KEYWORD]
    pok_args = [p.name for p in pos_or_kw]
    pok_def = {p.name: p.name for p in pos_or_kw if p.default is not p.empty}
    pok_req = [p.name for p in pos_or_kw if p.default is p.empty]
    n_req = len(pok_req) + len(po_req)
    pos_args = po_args + pok_args
    for kwo_args in iter_kw_args(spec_sig):
        # test args can be positional or keyword
        for i in range(len(pos_or_kw)+1):
            args = po_args + pok_args[:i]
            kwargs = {x: x for x in pok_args[i:]}
            kwargs.update(kwo_args)
            if not _test_call(spec_func, spec_sig, impl_func, impl_sig, args, kwargs):
                return False
        # test defaults may be omitted
        for i in range(n_req, len(pos_args)):
            args = pos_args[:i]
            kwargs = kwo_args.copy()
            if not _test_call(spec_func, spec_sig, impl_func, impl_sig, args, kwargs):
                return False
            kwargs.update({x: x for x in args[num_po:]})
            if not _test_call(spec_func, spec_sig, impl_func, impl_sig, args[:num_po], kwargs):
                return False

    kw_only = [p for p in spec_sig.parameters.values() if p.kind == p.KEYWORD_ONLY]
    kwo_args = {p.name: p.name for p in kw_only}
    # test *args
    if any(p.kind == p.VAR_POSITIONAL for p in spec_sig.parameters.values()):
        if not _test_call(spec_func, spec_sig, impl_func, impl_sig, pok_args + ['more', 'random', 'arguments'], kwo_args):
            return False
    # test **kwargs
    if any(p.kind == p.VAR_KEYWORD for p in spec_sig.parameters.values()):
        kwargs = kwo_args.copy()
        kwargs.update({x: x for x in ('more', 'random', 'keywords')})
        if not _test_call(spec_func, spec_sig, impl_func, impl_sig, pok_args, kwargs):
            return False
        kwargs.update(pok_def)
        if not _test_call(spec_func, spec_sig, impl_func, impl_sig, pok_req, kwargs):
            return False
    return True


def iter_kw_args(spec_sig):
    kw_only = [p for p in spec_sig.parameters.values() if p.kind == p.KEYWORD_ONLY]
    kwo_args = [p.name for p in kw_only]
    kwo_req = [p.name for p in kw_only if p.default is p.empty]
    for i in range(len(kwo_req), len(kwo_args)+1):
        kwargs = {x: x for x in kwo_args[:i]}
        yield kwargs


class TestFunctionSigsPy3(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pure_interface.set_is_development(True)

    def check_signatures(self, int_func, impl_func, expected_result):
        interface_sig = pure_interface.interface.signature(int_func)
        concrete_sig = pure_interface.interface.signature(impl_func)
        reality = test_call(int_func, impl_func)
        self.assertEqual(expected_result, reality,
                         '{}, {}. Reality does not match expectations'.format(int_func.__name__, impl_func.__name__))
        result = pure_interface.interface._signatures_are_consistent(concrete_sig, interface_sig)
        self.assertEqual(expected_result, result,
                         '{}, {}. Signature test gave wrong answer'.format(int_func.__name__, impl_func.__name__))

    def test_kw_only(self):
        self.check_signatures(func1, func2, True)
        self.check_signatures(func1, func3, False)
        self.check_signatures(func1, func4, True)
        self.check_signatures(func1, func5, True)
        self.check_signatures(func1, all_func, True)
        self.check_signatures(func1, no_kw_only, True)
        self.check_signatures(func1, no_args, False)
        self.check_signatures(func1, func1ex, True)
        self.check_signatures(func1, func1ex2, True)
        self.check_signatures(func3, func3ex, True)
        self.check_signatures(func3, func3ex2, True)
        self.check_signatures(func5, func5ex, True)
