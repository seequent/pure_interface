from collections.abc import Callable
from typing import Dict, Final, List, Optional, TypeAlias, cast

from mypy import nodes, types, plugin as mypy_plugin
from mypy.plugins import common

INTERFACE_FN: Final = 'pure_interface.interface.Interface'
DELEGATE_FN: Final = 'pure_interface.delegation.Delegate'
METADATA_KEY: Final = 'pure-interface'
IS_INTERFACE_KEY: Final = 'is-interface'

NOT_ANNOTATED = types.AnyType(types.TypeOfAny.unannotated)

InterfaceInfo: TypeAlias = Dict[str, nodes.SymbolTableNode]


def type_info_is_interface(type_info) -> bool:
    if not isinstance(type_info, nodes.TypeInfo):
        return False
    pi_data = type_info.metadata.get(METADATA_KEY)
    if pi_data is None:
        return False
    return pi_data.get(IS_INTERFACE_KEY, False)


def get_type_interfaces(class_def: nodes.ClassDef) -> List[nodes.ClassDef]:
    interfaces: List[nodes.ClassDef] = []
    for base_info in class_def.info.mro:
        if base_info.fullname == INTERFACE_FN:
            break
        if type_info_is_interface(base_info):
            interfaces.append(base_info.defn)
    return interfaces


def get_interface_bases(class_def: nodes.ClassDef) -> List[nodes.TypeInfo]:
    interface_list = [getattr(expr, 'node') for expr in class_def.base_type_exprs
                      if type_info_is_interface(getattr(expr, 'node', None))]
    return interface_list


def get_interface_info(class_def: nodes.ClassDef, recurse=True) -> InterfaceInfo:
    names: Dict[str, nodes.SymbolTableNode] = {}
    if recurse:
        for base_info in get_interface_bases(class_def):
            names.update(base_info.names)
    names.update(class_def.info.names)
    return names


def get_all_interface_info(interfaces: List[nodes.ClassDef]) -> InterfaceInfo:
    names: InterfaceInfo = {}
    for interface in interfaces:
        names.update(interface.info.names)
    return names


def get_return_type(func_type):
    r_type = getattr(func_type, 'ret_type', None)
    return r_type or NOT_ANNOTATED


def ensure_names(context: mypy_plugin.ClassDefContext, delegate: nodes.ClassDef, interface_info: InterfaceInfo) -> bool:
    """Adds names to the delegate class """
    info = delegate.info
    changed = False
    for name, s_node in interface_info.items():
        if name in info.names:
            continue
        changed = True
        value = s_node.node
        if isinstance(value, nodes.Var):
            node_type = NOT_ANNOTATED if s_node.type is None else s_node.type
            common.add_attribute_to_class(context.api, delegate, name, node_type)
        elif isinstance(value, nodes.FuncDef):
            args = ensure_type_annotations(value.arguments[1:])  # omit self
            common.add_method_to_class(context.api, delegate, name, args, get_return_type(value.type))
        elif type(value) is nodes.Decorator:
            decorators = value.original_decorators
            is_property = any(d for d in decorators if getattr(d, 'fullname', None) in ('builtins.property', 'abc.abstractproperty'))
            is_classmethod = any(d for d in decorators
                                 if getattr(d, 'fullname', None) in ('builtins.classmethod', 'abc.abstractclassmethod'))
            is_staticmethod = any(d for d in decorators
                                  if getattr(d, 'fullname', None) in ('builtins.staticmethod', 'abc.abstractstaticmethod'))
            r_type = get_return_type(value.func.type)
            if is_property:
                common.add_attribute_to_class(context.api, delegate, value.name, r_type)
            else:
                args = ensure_type_annotations(value.func.arguments)
                if not is_staticmethod:
                    args = args[1:]
                common.add_method_to_class(context.api, delegate, name, args, r_type,
                                           is_classmethod=is_classmethod, is_staticmethod=is_staticmethod)
    return changed


def ensure_type_annotations(arguments):
    """common.add_method_to_class requries a type_annotation on all arguments"""
    args = []
    arg: nodes.Argument
    for arg in arguments:
        type_annotation = arg.type_annotation or NOT_ANNOTATED
        new_arg = nodes.Argument(arg.variable, type_annotation, arg.initializer, arg.kind, arg.pos_only)
        args.append(new_arg)
    return args


def _handle_pi_attr_fallback(context, class_def):
    interface_list = get_type_interfaces(class_def)
    if len(interface_list) == 0:
        context.api.fail('pi_attr_fallback requires an Interface.', class_def)
        return
    interface_info = get_all_interface_info(interface_list)
    ensure_names(context, class_def, interface_info)


def _handle_pi_attr_delegates(context, delegate, rvalue):
    if not isinstance(rvalue, nodes.DictExpr):
        context.api.fail('pi_attr_delegates must be a dictionary.', delegate)
        return
    for _, expr in rvalue.items:
        if type(expr) is nodes.ListExpr:
            # list of delegated attribute names
            names = [e.value for e in expr.items if isinstance(e, nodes.StrExpr)]
            for name in names:
                common.add_attribute_to_class(context.api, delegate, name, NOT_ANNOTATED)
        elif type(expr) is nodes.NameExpr:
            # interface class
            type_info = expr.node
            if not type_info_is_interface(type_info):
                context.api.fail('pi_attr_delegates values must be interface type')
                return
            type_info = cast(nodes.TypeInfo, type_info)
            interface_info = get_interface_info(type_info.defn)
            ensure_names(context, delegate, interface_info)


def _handle_pi_attr_mapping(context, delegate, rvalue):
    if not isinstance(rvalue, nodes.DictExpr):
        context.api.fail('pi_attr_mapping must be a dictionary.', delegate)
        return
    for expr, _ in rvalue.items:
        if not isinstance(expr, nodes.StrExpr):
            context.api.fail('pi_attr_mapping keys must be strings.', delegate)
            return
        common.add_attribute_to_class(context.api, delegate, expr.value, NOT_ANNOTATED)


class PureInterfacePlugin(mypy_plugin.Plugin):

    def get_base_class_hook(self, fullname: str) -> Optional[Callable[[mypy_plugin.ClassDefContext], None]]:
        if fullname == INTERFACE_FN:
            return self._mark_class_as_interface
        if fullname == DELEGATE_FN:
            return self._create_delegate_attributes
        return None

    def get_class_decorator_hook(
        self, fullname: str
    ) -> Optional[Callable[[mypy_plugin.ClassDefContext], None]]:
        if fullname == 'dataclasses.dataclass':
            return self._create_dataclass_attributes
        return None

    @staticmethod
    def _mark_class_as_interface(context: mypy_plugin.ClassDefContext):
        context.cls.info.metadata[METADATA_KEY] = {IS_INTERFACE_KEY: True}
        context.cls.info.is_abstract = True
        for item in context.cls.defs.body:
            if isinstance(item, nodes.FuncDef):
                item.abstract_status = nodes.IMPLICITLY_ABSTRACT
            elif isinstance(item, nodes.Decorator):
                item.func.abstract_status = nodes.IMPLICITLY_ABSTRACT

    @staticmethod
    def _create_delegate_attributes(context: mypy_plugin.ClassDefContext):
        class_def = context.cls
        for item in class_def.defs.body:
            if not isinstance(item, nodes.AssignmentStmt):
                continue
            if not (len(item.lvalues) == 1 and isinstance(item.lvalues[0], nodes.NameExpr)):
                continue
            name = item.lvalues[0].fullname
            if name == 'pi_attr_fallback':
                _handle_pi_attr_fallback(context, class_def)
            elif name == 'pi_attr_delegates':
                _handle_pi_attr_delegates(context, class_def, item.rvalue)
            elif name == 'pi_attr_mapping':
                _handle_pi_attr_mapping(context, class_def, item.rvalue)

    @staticmethod
    def _create_dataclass_attributes(context: mypy_plugin.ClassDefContext):
        # this still does not create the appropriate __init__ function signature
        class_def = context.cls
        if not isinstance(class_def, nodes.ClassDef):
            return
        interfaces = get_type_interfaces(class_def)
        if not interfaces:
            return
        interface_info = get_all_interface_info(interfaces)
        changed = ensure_names(context, class_def, interface_info)
        if changed:
            context.api.defer()


def plugin(version: str):
    return PureInterfacePlugin
