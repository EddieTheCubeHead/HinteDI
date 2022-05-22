__version__ = "0.2.0"
__author__ = "Eetu Asikainen"

from inspect import signature, Parameter
from typing import Any, Callable


def _is_injectable_argument(arg):
    return arg.kind in (Parameter.POSITIONAL_OR_KEYWORD, Parameter.POSITIONAL_ONLY) and arg.default is Parameter.empty


def _is_method_target_argument(arg):
    return arg.name in ("self", "cls")


class InstanceSentinel:
    """A sentinel class used for differentiating instance dependencies from singleton dependencies in dependency dict.

    This is exposed to enable typechecking against this class.
    """
    pass


class InjectionException(Exception):
    """An exception thrown by dependency injector.

    :param message: The error message
    :type message: str
    """

    def __init__(self, message: str):
        full_message = f"An error occurred during HinteDI dependency injection: {message}\n If you think this is a " \
                       f"bug, please file a bug report in the HinteDI repository in GitHub according to the " \
                       f"guidelines of a good bug report."
        super().__init__(full_message)


class HinteDI:
    """The dependency injector class.

    This class is meant to be used through the class method decorators
    :py:meth:`hintedi.HinteDI.singleton`, :py:meth:`hintedi.HinteDI.instance` and :py:meth:`hintedi.HinteDI.inject`.
    This is provided as a class instead of as a collection of methods to enable subclassing. By subclassing this class
    you can have multiple independent injector implementations in your program.

    :cvar dependencies: A dict mapping dependency types into the dependency.
    :type dependencies: dict[type, Any]
    """

    dependencies: dict[type, Any] = {}

    @classmethod
    def singleton(cls, dependency_class: type):
        """A class method meant to be used as a class decorator to mark the class as a singleton dependency (reuse the
        same instance for all injections).

        :param dependency_class: The class to be decorated
        :type dependency_class: type
        """
        cls._add_dependency(dependency_class, None)
        return dependency_class

    @classmethod
    def instance(cls, dependency_class: type):
        """A class method meant to be used as a class decorator to mark the class as an instance dependency (create a
        new instance for all injections).

        :param dependency_class: The class to be decorated
        :type dependency_class: type
        """
        cls._add_dependency(dependency_class, InstanceSentinel())
        return dependency_class

    @classmethod
    def _add_dependency(cls, dependency_class: type, default_value: None | InstanceSentinel):
        if dependency_class in cls.dependencies:
            raise InjectionException(f"Could not register dependency {dependency_class.__name__} as a dependency with"
                                     f" identical name already exists.")
        cls.dependencies[dependency_class] = default_value

    @classmethod
    def inject(cls, func: Callable):
        """A class method meant to be used as a function decorator to mark the method as requiring injection. Only
        positional or positional + keyword arguments will be injected, keyword-only arguments will not be injected.
        Arguments already provided including default values will be ignored, as will all arguments named self or cls.

        :param func: The function requiring dependency injection
        :type func: Callable
        """
        def injection_wrapper(*args, **kwargs):
            return cls._inject_needed(func, *args, **kwargs)

        return injection_wrapper

    @classmethod
    def _inject_needed(cls, func: Callable, *args, **kwargs):
        func_args = signature(func)
        injected = []
        for arg in list(func_args.parameters.values())[len(args):]:
            if _is_injectable_argument(arg) and not _is_method_target_argument(arg):
                injected += [cls._inject_arg(arg)]
        return func(*args, *injected, **kwargs)

    @classmethod
    def _inject_arg(cls, arg: Parameter):
        if arg.annotation == Parameter.empty:
            raise (InjectionException(f"Could not inject argument {arg} because it doesn't have a type annotation."))
        real_key = cls._is_dependency_present(arg.annotation)
        if real_key:
            return cls._get_dependency(real_key)
        raise (InjectionException(f"Could not inject argument {arg.name} because type '{arg.annotation}' is not "
                                  f"registered as a dependency."))

    @classmethod
    def _is_dependency_present(cls, annotation: type | str):
        if annotation in cls.dependencies:
            return annotation
        for dependency in cls.dependencies:
            # If inner class shenanigans are happening annotation might arrive as a string, this should be parsed to
            # preserve the functionality of the injector for inner classes as well
            if annotation == str(dependency).split(".")[-1][:-2] or annotation == str(dependency):
                return dependency
        return None

    @classmethod
    def _get_dependency(cls, annotation: type):
        if type(cls.dependencies[annotation]) is InstanceSentinel:
            return annotation()
        if not cls.dependencies[annotation]:
            cls.dependencies[annotation] = annotation()
        return cls.dependencies[annotation]
