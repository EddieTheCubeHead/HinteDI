import pytest

from hintedi import HinteDI, InjectionException, ImplementationFactory


@HinteDI.abstract_base
class AbstractBaseDependency:
    pass


@HinteDI.singleton_implementation(base=AbstractBaseDependency, key="default", is_default=True)
class DefaultConcreteDependency(AbstractBaseDependency):
    pass


@HinteDI.instance_implementation(base=AbstractBaseDependency, key="instance")
class InstanceConcreteDependency(AbstractBaseDependency):
    pass


class TestInjector(HinteDI):  # isolate test cases again to allow resetting constructor
    pass


class TestKeyBasedInjection:

    def test_abstract_base_dependency_when_not_resolved_with_key_then_default_used(self):
        class Injected:

            @HinteDI.inject
            def __init__(self, dependency: AbstractBaseDependency):
                self.dependency = dependency

        injected = Injected()
        assert type(injected.dependency) is DefaultConcreteDependency

    def test_abstract_base_dependency_when_resolved_with_correct_key_then_key_dependency_used(self):
        class Injected:

            @HinteDI.inject
            def __init__(self, dependency: AbstractBaseDependency, *, dependency_key: str):
                self.dependency = dependency.resolve_from_key(dependency_key)

        instance_injected = Injected(dependency_key="instance")
        default_injected = Injected(dependency_key="default")
        assert type(instance_injected.dependency) is InstanceConcreteDependency
        assert type(default_injected.dependency) is DefaultConcreteDependency

    def test_abstract_base_dependency_given_implementation_exists_then_it_can_be_used_as_dependency_alone(self):
        class Injected:

            @HinteDI.inject
            def __init__(self, dependency: InstanceConcreteDependency):
                self.dependency = dependency

        assert type(Injected().dependency) is InstanceConcreteDependency

    @pytest.mark.parametrize("dependency_type", [HinteDI.singleton_implementation, HinteDI.instance_implementation])
    def test_implementation_registration_given_no_abstract_base_then_exception_raised(self, dependency_type):
        class InvalidBase:
            pass

        class InvalidDependency:
            pass

        expected_exception = InjectionException(f"Could not register a complete implementation "
                                                f"{InvalidDependency.__name__} for class {InvalidBase.__name__} "
                                                f"because {InvalidBase.__name__} is not registered as abstract base "
                                                f"dependency.")

        with pytest.raises(InjectionException) as actual_exception:
            dependency_type(base=InvalidBase, key="foo")(InvalidDependency)
        assert str(expected_exception) == str(actual_exception.value)

    @pytest.mark.parametrize("dependency_type", [HinteDI.singleton_implementation, HinteDI.instance_implementation])
    def test_implementation_given_default_exists_when_creating_default_then_exception_thrown(self, dependency_type):
        class InvalidDefault:
            pass

        expected_exception = InjectionException(f"Could not create default implementation {InvalidDefault.__name__} "
                                                f"for base {AbstractBaseDependency.__name__} because default "
                                                f"implementation already exists as class "
                                                f"{DefaultConcreteDependency.__name__}.")

        with pytest.raises(InjectionException) as actual_exception:
            dependency_type(base=AbstractBaseDependency, key="foo", is_default=True)(InvalidDefault)
        assert str(expected_exception) == str(actual_exception.value)

    @pytest.mark.parametrize("dependency_type", [HinteDI.singleton_implementation, HinteDI.instance_implementation])
    def test_implementation_given_key_taken_when_creating_implementation_then_exception_thrown(self, dependency_type):
        class InvalidKeyName:
            pass

        expected_exception = InjectionException(f"Could not create implementation {InvalidKeyName.__name__} for base "
                                                f"{AbstractBaseDependency.__name__} because implementation with the "
                                                f"key 'default' already exists as class "
                                                f"{DefaultConcreteDependency.__name__}.")

        with pytest.raises(InjectionException) as actual_exception:
            dependency_type(base=AbstractBaseDependency, key="default")(InvalidKeyName)
        assert str(expected_exception) == str(actual_exception.value)

    @pytest.mark.parametrize("dependency_type", [HinteDI.singleton_implementation, HinteDI.instance_implementation])
    def test_implementation_when_creating_default_with_resolve_from_key_attribute_then_exception_thrown(self, dependency_type):
        @HinteDI.abstract_base
        class AnotherBase:
            pass

        class InvalidAttributeHolder:
            def resolve_from_key(self):
                pass

        expected_exception = InjectionException(f"Could not create default implementation "
                                                f"{InvalidAttributeHolder.__name__} for base {AnotherBase.__name__} "
                                                f"because default implementations cannot have an attribute named "
                                                f"'resolve_from_key'.")

        with pytest.raises(InjectionException) as actual_exception:
            dependency_type(base=AnotherBase, key="default", is_default=True)(InvalidAttributeHolder)
        assert str(expected_exception) == str(actual_exception.value)

    @pytest.mark.parametrize("dependency_type", [HinteDI.singleton_implementation, HinteDI.instance_implementation])
    def test_implementation_when_creating_default_with_resolve_from_key_attribute_then_exception_thrown(self, dependency_type):
        class ValidAttributeHolder:
            def resolve_from_key(self):
                pass

        dependency_type(base=AbstractBaseDependency, key="attribute_holder")

    def test_inject_given_base_class_with_no_implementations_when_injecting_base_then_exception_thrown(self):
        @HinteDI.abstract_base
        class UnimplementedBase:
            pass

        @HinteDI.inject
        def invalid_injection(foo: UnimplementedBase):
            pass

        expected_exception = InjectionException(f"Could not inject an implementation of abstract base class "
                                                f"{UnimplementedBase.__name__} because no implementations exist.")

        with pytest.raises(InjectionException) as actual_exception:
            invalid_injection()
        assert str(expected_exception) == str(actual_exception.value)

    def test_inject_given_base_class_with_no_default_when_injecting_then_returns_implementation_factory(self):
        @HinteDI.abstract_base
        class BaseWithNoDefault:
            pass

        @HinteDI.singleton_implementation(base=BaseWithNoDefault, key="1")
        class FirstDependency:
            pass

        class Injected:

            @HinteDI.inject
            def __init__(self, dependency: BaseWithNoDefault):
                self.dependency = dependency

        assert type(Injected().dependency) == ImplementationFactory

    def test_inject_given_implementation_factory_returned_when_calling_resolve_from_key_then_correct_dependency_returned(self):
        @HinteDI.abstract_base
        class BaseWithNoDefault:
            pass

        @HinteDI.singleton_implementation(base=BaseWithNoDefault, key="1")
        class FirstDependency:
            pass

        class Injected:

            @HinteDI.inject
            def __init__(self, dependency: BaseWithNoDefault):
                self.dependency = dependency

        assert type(Injected().dependency.resolve_from_key("1")) == FirstDependency

    def test_inject_given_implementation_factory_returned_when_calling_with_invalid_key_then_exception_thrown(self):
        @HinteDI.abstract_base
        class BaseWithNoDefault:
            pass

        @HinteDI.singleton_implementation(base=BaseWithNoDefault, key="1")
        class FirstDependency:
            pass

        class Injected:

            @HinteDI.inject
            def __init__(self, dependency: BaseWithNoDefault):
                self.dependency = dependency

        expected_exception = InjectionException(f"Could not resolve key '2' for class {BaseWithNoDefault.__name__}.")

        with pytest.raises(InjectionException) as actual_exception:
            Injected().dependency.resolve_from_key("2")
        assert str(expected_exception) == str(actual_exception.value)

    def test_inject_given_default_dependency_when_attempting_to_resolve_invalid_key_then_exception_thrown(self):
        class Injected:

            @HinteDI.inject
            def __init__(self, dependency: AbstractBaseDependency):
                self.dependency = dependency

        expected_exception = InjectionException(f"Could not resolve key '2' for class "
                                                f"{AbstractBaseDependency.__name__}.")

        with pytest.raises(InjectionException) as actual_exception:
            Injected().dependency.resolve_from_key("2")
        assert str(expected_exception) == str(actual_exception.value)

    def test_inject_given_already_resolved_then_resolve_from_key_method_not_added(self):
        class Injected:

            @HinteDI.inject
            def __init__(self, dependency: AbstractBaseDependency):
                self.dependency = dependency

        resolved_dependency = Injected().dependency.resolve_from_key("instance")
        assert not hasattr(resolved_dependency, "resolve_from_key")
