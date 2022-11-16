import pytest

from hintedi import HinteDI, InjectionException


@HinteDI.singleton
class SingletonDependency:
    pass


@HinteDI.instance
class InstanceDependency:
    pass


class TestInjector(HinteDI):  # isolate test cases here to allow resetting constructor
    pass


class TestHinteDI:

    def test_singleton_when_used_as_dependency_then_same_instance_injected(self):
        class Injected:

            @HinteDI.inject
            def __init__(self, dependency: SingletonDependency):
                self.dependency = dependency

        first_injected = Injected()
        second_injected = Injected()
        assert type(first_injected.dependency) is SingletonDependency
        assert first_injected.dependency is second_injected.dependency

    def test_instance_when_used_as_dependency_then_different_instance_injected(self):
        class Injected:

            @HinteDI.inject
            def __init__(self, dependency: InstanceDependency):
                self.dependency = dependency

        first_injected = Injected()
        second_injected = Injected()
        assert type(first_injected.dependency) is InstanceDependency
        assert type(second_injected.dependency) is InstanceDependency
        assert first_injected.dependency is not second_injected.dependency

    def test_inject_when_injected_with_all_dependencies_provided_then_no_dependency_injected(self):
        @HinteDI.instance
        class Injectable:
            def __init__(self, value: int = 1):
                self.value = value

        def provided_test(first: Injectable, second: Injectable):
            return first.value != 1 and second.value != 1

        assert provided_test(Injectable(2), Injectable(3))

    def test_inject_given_function_with_default_arguments_when_injected_then_default_arguments_not_injected(self):
        @HinteDI.instance
        class Injectable:
            def __init__(self, value: int = 1):
                self.value = value

        @HinteDI.inject
        def default_test(argument: Injectable, another: Injectable = Injectable(2)):
            return another.value > argument.value

        assert default_test()

    def test_inject_given_used_with_method_when_injected_then_self_argument_not_injected(self):
        @HinteDI.singleton
        class Injectable:
            def __init__(self, value: int = 1):
                self.value = value

        class Dependent:

            @HinteDI.inject
            def __init__(self, injectable: Injectable):
                self.injectable = injectable

        assert Injectable().value == Dependent().injectable.value

    def test_inject_given_used_with_class_method_when_injected_then_cls_argument_not_injected(self):
        @HinteDI.singleton
        class Injectable:
            def __init__(self, value: int = 1):
                self.value = value

        class Dependent:

            @classmethod
            @HinteDI.inject
            def method(cls, injectable: Injectable):
                return injectable.value

        assert Injectable().value == Dependent.method()

    def test_inject_given_args_possible_when_injected_then_args_not_injected(self):
        @HinteDI.singleton
        class Injectable:

            def __init__(self, value: bool = True):
                self.value = value

        @HinteDI.inject
        def args_test(argument: Injectable, *args):
            return argument.value and not args

        assert args_test()

    def test_inject_given_kwargs_possible_when_injected_then_kwargs_not_injected(self):
        @HinteDI.singleton
        class Injectable:

            def __init__(self, value: bool = True):
                self.value = value

        @HinteDI.inject
        def args_test(argument: Injectable, **kwargs):
            return argument.value and not kwargs

        assert args_test()

    def test_inject_given_kwargs_present_when_injected_then_dependency_still_injected(self):
        @HinteDI.singleton
        class Injectable:

            def __init__(self, value: bool = True):
                self.value = value

        @HinteDI.inject
        def args_test(argument: Injectable, **kwargs):
            return argument.value and kwargs

        assert args_test(extra="argument")

    def test_inject_when_injecting_method_with_default_args_and_kwargs_then_only_dependencies_injected(self):
        @HinteDI.singleton
        class Injectable:

            def __init__(self, value: bool = True):
                self.value = value

        class Dependent:

            @HinteDI.inject
            def __init__(self, injectable: Injectable, default: bool = True, *args, **kwargs):
                self.injectable = injectable
                self.default = default
                self.args = args
                self.kwargs = kwargs

            def __bool__(self):
                return self.injectable and self.default and not self.args and not self.kwargs

        assert Dependent()

    def test_inject_given_dependency_with_no_resolution_then_error_raised_with_missing_dependency(self):
        class Dependency:
            pass

        class DependentClass:
            @TestInjector.inject
            def __init__(self, dependency: Dependency):
                self.dependency = dependency
        
        expected_exception = InjectionException(f"Could not inject argument dependency because type "
                                                f"'{Dependency.__name__}' is not registered as a dependency.")

        with pytest.raises(InjectionException) as actual_exception:
            DependentClass()
            assert str(expected_exception) == str(actual_exception)

    def test_inject_given_dependency_with_no_annotation_then_error_raised_with_missing_annotation(self):
        class DependentClass:
            @TestInjector.inject
            def __init__(self, dependency):
                self.dependency = dependency

        expected_exception = InjectionException(f"Could not inject argument dependency because it doesn't have a type "
                                                f"annotation.")

        with pytest.raises(InjectionException) as actual_exception:
            DependentClass()
            assert str(expected_exception) == str(actual_exception)

    @pytest.mark.parametrize("dependency_type", [HinteDI.singleton, HinteDI.instance, HinteDI.abstract_base])
    def test_singleton_given_dependency_of_same_type_then_error_raised_with_duplicate_dependency(self, dependency_type):
        @dependency_type
        class DuplicatedDependency:
            pass

        expected_exception = InjectionException(f"Could not register dependency {DuplicatedDependency.__name__} as a "
                                                f"dependency with identical name already exists.")

        with pytest.raises(InjectionException) as actual_exception:
            HinteDI.singleton(DuplicatedDependency)
            assert str(expected_exception) == str(actual_exception)

    @pytest.mark.parametrize("dependency_type", [HinteDI.singleton, HinteDI.instance, HinteDI.abstract_base])
    def test_instance_given_dependency_of_same_type_then_error_raised_with_duplicate_dependency(self, dependency_type):
        @dependency_type
        class DuplicatedDependency:
            pass

        expected_exception = InjectionException(f"Could not register dependency {DuplicatedDependency.__name__} as a "
                                                f"dependency with identical name already exists.")

        with pytest.raises(InjectionException) as actual_exception:
            HinteDI.instance(DuplicatedDependency)
            assert str(expected_exception) == str(actual_exception)
