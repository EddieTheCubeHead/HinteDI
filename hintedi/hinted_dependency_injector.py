__version__ = "0.3.1"
__author__ = "Eetu Asikainen"

from inspect import signature, Parameter
from typing import Any, Callable, Union, Dict, Hashable


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

    This is exposed to enable catching it explicitly if needed. It is not advisable to use this class to construct your
    own exceptions.

    :param message: The error message
    :type message: str
    """

    def __init__(self, message: str):
        full_message = f"An error occurred during HinteDI dependency injection: {message}\n If you think this is a " \
                       f"bug, please file a bug report in the HinteDI repository issue tracker in GitHub " \
                       f"(https://github.com/EddieTheCubeHead/HinteDI/issues) using the \"Bug report\" issue template."
        super().__init__(full_message)


class ImplementationFactory:
    """A class returned when resolving an abstract base class with no default implementations. Contains the
    ''ImplementationFactory.resolve_from_key'' -method for resolving a concrete implementation from a given key."""

    def __init__(self, resolver: Callable[[Hashable], Any], base: type):
        self._resolver = resolver
        self._base = base

    def resolve_from_key(self, key: Hashable) -> Any:
        """A method for resolving a concrete implementation for the abstract base class an implementation factory
        represents.

        :param key: The key used for resolving the implementation
        :type key: typing.Hashable"""
        return self._resolver(key)


class DefaultImplementationSentinel:
    """A sentinel class used for identifying default implementations in dependency dict.

    This is exposed to enable typechecking against this class.
    """
    pass


_implementation_dict = Dict[Union[str, DefaultImplementationSentinel], Union[type, ImplementationFactory]]


class HinteDI:
    """The dependency injector class.

    This class is meant to be used through the class method decorators ``HinteDI.singleton``, ``HinteDI.instance``
    and ``HinteDI.inject`` for normal dependency injection and the class method decorators ``HinteDI.abstract_base``,
    ``HinteDI.singleton_implementation`` and ``HinteDI.instance_implementation`` for factory-type abstract base class
    based injection.

    This is provided as a class instead of as a collection of methods to enable subclassing. By subclassing this class
    you can have multiple independent injector implementations in your program. The class also exposes the dependencies
    dict that stores all registered dependencies. This can be manipulated for example for testing purposes. For
    instance dependencies, the dependency type is mapped into an ``InstanceSentinel`` instance, for uninitialized
    singletons into ``None``, for initialized singletons, the singleton instance and for Abstract base classes, a
    dict storing the key-implementation mappings. In the key-implementation mapping the default implementation is stored
    with a special key ``HinteDI.default_implementation``.

    :cvar dependencies: A dict mapping dependency types into the dependency.
    :type dependencies: dict[type, Any]
    :cvar default_implementation: A sentinel object marking default implementations for abstract dependencies
    :type default_implementation: DefaultImplementationSentinel
    """

    dependencies: dict[type, Any] = {}
    default_implementation: DefaultImplementationSentinel = DefaultImplementationSentinel()

    @classmethod
    def singleton(cls, dependency_class: type) -> type:
        """A class method meant to be used as a class decorator to mark the class as a singleton dependency (reuse the
        same instance for all injections).

        Usage::

            @HinteDI.singleton
            class SingletonDependency:
                ...

        :param dependency_class: The class to be decorated
        :type dependency_class: type
        """
        cls._add_dependency(dependency_class, None)
        return dependency_class

    @classmethod
    def instance(cls, dependency_class: type) -> type:
        """A class method meant to be used as a class decorator to mark the class as an instance dependency (create a
        new instance for all injections).

        Usage::

            @HinteDI.instance
            class InstanceDependency:
                ...

        :param dependency_class: The class to be decorated
        :type dependency_class: type
        """
        cls._add_dependency(dependency_class, InstanceSentinel())
        return dependency_class

    @classmethod
    def abstract_base(cls, dependency_class: type) -> type:
        """A class method meant to be used as a class decorator to mark the class as an abstract dependency.

        Use class decorators ``HinteDI.singleton_implementation`` and ``HinteDI.instance_implementation`` to register
        key-based implementations for the class.

        Usage::

            @HinteDI.abstract_base
            class AbstractDependency:
                ...

        :param dependency_class: The class to be decorated
        :type dependency_class: type
        """
        base_dict = {
            cls.default_implementation: ImplementationFactory(cls._resolve_from_key(dependency_class), dependency_class)
        }
        cls._add_dependency(dependency_class, base_dict)
        return dependency_class

    @classmethod
    def singleton_implementation(cls, *, base: type, key: Hashable, is_default: bool = False) -> Callable[[type], type]:
        """A class method meant to be used as a class decorator to mark the class as a concrete singleton-based
        implementation of an abstract dependency.

        See ``HinteDI.abstract_base`` for registering the abstract base class and ``HinteDI.singleton`` for a more
        thorough explanation of the singleton patter in HinteDI

        Usage::

            # Create the abstract dependency first
            @HinteDI.abstract_base
            class AbstractDependency:
                ...

            # Note that actually inheriting the abstract base is not required for HinteDI to work
            # The key can be any hashable value, but most use cases should probably use enums or strings
            @HinteDI.singleton_implementation(base = AbstractDependency, key = "concrete")
            class ConcreteDependency(AbstractDependency):
                ...

        The abstract class injection pattern in HinteDI will return a ``HinteDI.ImplementationFactory`` instance that
        has the ``HinteDI.ImplementationFactory.resolve_from_key`` method that can be used to resolve the concrete instance
        based on a given key. You can also specify a default implementation with the optional ''is_default'' argument for
        the implementation decorators. If a default implementation is present, HinteDI will inject the default
        implementation when asked to inject the abstract base class and add the ''FromKey'' method to the returned
        object enabling you to resolve the dependency to some other implementation if needed.

        Creating a default implementation::

            # Even though the key here is 'default', any key works for this
            @HinteDI.singleton_implementation(base = AbstractDependency, key = "default", is_default = True)
            class DefaultImplementation(AbstractDependency):
                ...

        :param base: The abstract base class the created concrete class will implement
        :type base: type
        :param key: The key that can be used to resolve the abstract base class into the created implementation
        :type key: typing.Hashable
        :param is_default: An optional flag that marks the implementation as the default implementation, default=False
        :type is_default: bool
        """
        def wrapper(dependency_class: type):
            return cls._create_implementation(base, key, is_default, dependency_class, None)

        return wrapper

    @classmethod
    def instance_implementation(cls, *, base: type, key: str, is_default: bool = False) -> Callable[[type], type]:
        """A class method meant to be used as a class decorator to mark the class as a concrete instance-based
        implementation of an abstract dependency.

        See ``HinteDI.abstract_base`` for registering the abstract base class

        Usage::

            # Create the abstract dependency first
            @HinteDI.abstract_base
            class AbstractDependency:
                ...

            # Note that actually inheriting the abstract base is not required for HinteDI to work
            # The key can be any hashable value, but most use cases should probably use enums or strings
            @HinteDI.instance_implementation(base = AbstractDependency, key = "concrete")
            class ConcreteDependency(AbstractDependency):
                ...

        The abstract class injection pattern in HinteDI will return a ``HinteDI.ImplementationFactory`` instance that
        has the ``HinteDI.ImplementationFactory.resolve_from_key`` method that can be used to resolve the concrete instance
        based on a given key. You can also specify a default implementation with the optional ''is_default'' argument for
        the implementation decorators. If a default implementation is present, HinteDI will inject the default
        implementation when asked to inject the abstract base class and add the ''FromKey'' method to the returned
        object enabling you to resolve the dependency to some other implementation if needed.

        Creating a default implementation::

            # Even though the key here is 'default', any key works for this
            @HinteDI.instance_implementation(base = AbstractDependency, key = "default", is_default = True)
            class DefaultImplementation(AbstractDependency):
                ...

        :param base: The abstract base class the created concrete class will implement
        :type base: type
        :param key: The key that can be used to resolve the abstract base class into the created implementation
        :type key: typing.Hashable
        :param is_default: An optional flag that marks the implementation as the default implementation, default=False
        :type is_default: bool
        """
        def wrapper(dependency_class: type):
            return cls._create_implementation(base, key, is_default, dependency_class, InstanceSentinel())

        return wrapper

    @classmethod
    def _create_implementation(cls, base: type, key: Hashable, is_default: bool, dependency_class: type,
                               default_value: None | InstanceSentinel) -> type:
        cls._assert_base_present(base, dependency_class)
        cls._create_key(base, key, dependency_class, is_default)
        cls._add_dependency(dependency_class, default_value)
        return dependency_class

    @classmethod
    def _assert_base_present(cls, base: type, implementation: type):
        if base not in cls.dependencies:
            raise InjectionException(f"Could not register a complete implementation {implementation.__name__} for "
                                     f"class {base.__name__} because {base.__name__} is not registered as abstract "
                                     f"base dependency.")

    @classmethod
    def _create_key(cls, base: type, key: Hashable, dependency_class: type, is_default: bool = True):
        if is_default and type(cls.dependencies[base][cls.default_implementation]) != ImplementationFactory:
            raise InjectionException(f"Could not create default implementation {dependency_class.__name__} for base "
                                     f"{base.__name__} because default implementation already exists as class "
                                     f"{cls.dependencies[base][cls.default_implementation].__name__}.")
        if key in cls.dependencies[base]:
            raise InjectionException(f"Could not create implementation {dependency_class.__name__} for base "
                                     f"{base.__name__} because implementation with the key '{key}' already exists as "
                                     f"class {cls.dependencies[base][key].__name__}.")
        if is_default and hasattr(dependency_class, "resolve_from_key"):
            raise InjectionException(f"Could not create default implementation {dependency_class.__name__} for base "
                                     f"{base.__name__} because default implementations cannot have an attribute named "
                                     f"'resolve_from_key'.")
        cls.dependencies[base][key] = dependency_class
        if is_default:
            cls.dependencies[base][cls.default_implementation] = dependency_class

    @classmethod
    def _add_dependency(cls, dependency_class: type, default_value: Union[None, InstanceSentinel, _implementation_dict]):
        if dependency_class in cls.dependencies:
            raise InjectionException(f"Could not register dependency {dependency_class.__name__} as a dependency with"
                                     f" identical name already exists.")
        cls.dependencies[dependency_class] = default_value

    @classmethod
    def inject(cls, func: Callable):
        """A class method meant to be used as a function decorator to mark the method as requiring injection. Only
        positional or positional + keyword arguments will be injected, keyword-only arguments will not be injected.
        Arguments already provided including default values will be ignored, as will all arguments named self or cls.

        Usage in an instance method::

            class DependentClass:

                @HinteDI.inject
                def __init__(self, dependency: Dependency)  # self is ignored automatically
                    ...

        Usage in a class method::

            class DependentClass:

                @classmethod  # Ensure the classmethod decorator comes first
                @HinteDI.inject
                def perform_class_method(cls, dependency: Dependency)  # cls is ignored automatically
                    ...

        Usage in a function::

            @HinteDI.inject
            def perform_function(dependency: Dependency)
                ...

        If HinteDI is asked to inject an abstract dependency it will return either an ``HinteDI.ImplementationFactory``
        if the dependency has no default implementation, or the default implementation if the dependency has one. If
        a default implementation is returned, HinteDI will add the ''resolve_from_key'' method to the object enabling
        you to resolve it to another implementation if needed.

        Usage with an abstract dependency with no default implementation::

            @HinteDI.inject
            def perform_function(dependency: AbstractDependency):
                concrete_dependency = dependency.resolve_from_key("key")
                ...

        Usage with an abstract dependency with a default implementation::

            @HinteDI.inject
            def perform_function(dependency: AbstractDependency):
                # You can use the returned dependency right away...
                dependency.do_stuff()

                # ...Or you can resolve it into a dependency of another type
                resolved_dependency = dependency.resolve_from_key("key")

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
        raise (InjectionException(f"Could not inject argument {arg.name} because type '{arg.annotation.__name__}' is "
                                  f"not registered as a dependency."))

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
        if type(cls.dependencies[annotation]) is dict:
            return cls._get_default_abstract_dependency(annotation)
        if cls.dependencies[annotation] is None:
            cls.dependencies[annotation] = annotation()
        return cls.dependencies[annotation]

    @classmethod
    def _get_default_abstract_dependency(cls, abstract_base: type, key: str = "default"):
        cls._assert_implemented(abstract_base)
        key = cls._assert_valid_key_or_default(abstract_base, key)
        if type(cls.dependencies[abstract_base][key]) is ImplementationFactory:
            return cls.dependencies[abstract_base][key]
        real_resolved_type = cls._is_dependency_present(cls.dependencies[abstract_base][key])
        dependency = cls._get_dependency(real_resolved_type)
        if not hasattr(dependency, "resolve_from_key"):
            dependency.resolve_from_key = cls._resolve_from_key(abstract_base)
        return dependency

    @classmethod
    def _assert_implemented(cls, abstract_base: type):
        if len(cls.dependencies[abstract_base]) == 1:
            raise InjectionException(f"Could not inject an implementation of abstract base class "
                                     f"{abstract_base.__name__} because no implementations exist.")

    @classmethod
    def _assert_valid_key_or_default(cls, abstract_base: type, key: str) -> str:
        if key not in cls.dependencies[abstract_base]:
            key = cls.default_implementation
        return key

    @classmethod
    def _resolve_from_key(cls, base: type) -> Callable[[str], Any]:
        def wrapper(key: str) -> Any:
            if key in cls.dependencies[base]:
                return cls._get_dependency(cls.dependencies[base][key])
            raise InjectionException(f"Could not resolve key '{key}' for class {base.__name__}.")

        return wrapper
