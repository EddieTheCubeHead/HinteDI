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
                self.dependency = dependency.from_key(dependency_key)

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

        expected_exception = InjectionException(f"Could not register a complete implementation {InvalidDependency} for "
                                                f"class {InvalidBase} because {InvalidBase} is not registered as "
                                                f"abstract base dependency.")

        with pytest.raises(InjectionException) as actual_exception:
            dependency_type(base=InvalidBase, key="foo")(InvalidDependency)
            assert str(expected_exception) == str(actual_exception)

    @pytest.mark.parametrize("dependency_type", [HinteDI.singleton_implementation, HinteDI.instance_implementation])
    def test_implementation_given_default_exists_when_creating_default_then_exception_thrown(self, dependency_type):
        class InvalidDefault:
            pass

        expected_exception = InjectionException(f"Could not create default implementation {InvalidDefault} for base "
                                                f"{AbstractBaseDependency} because default implementation already "
                                                f"exists as class {DefaultConcreteDependency}.")

        with pytest.raises(InjectionException) as actual_exception:
            dependency_type(base=AbstractBaseDependency, key="foo", is_default=True)(InvalidDefault)
            assert str(expected_exception) == str(actual_exception)

    @pytest.mark.parametrize("dependency_type", [HinteDI.singleton_implementation, HinteDI.instance_implementation])
    def test_implementation_given_key_taken_when_creating_implementation_then_exception_thrown(self, dependency_type):
        class InvalidKeyName:
            pass

        expected_exception = InjectionException(f"Could not create implementation {InvalidKeyName} for base "
                                                f"{AbstractBaseDependency} because implementation with the key "
                                                f"'default' already exists as class {DefaultConcreteDependency}.")

        with pytest.raises(InjectionException) as actual_exception:
            dependency_type(base=AbstractBaseDependency, key="default")(InvalidKeyName)
            assert str(expected_exception) == str(actual_exception)

    def test_inject_given_base_class_with_no_implementations_when_injecting_base_then_exception_thrown(self):
        @HinteDI.abstract_base
        class UnimplementedBase:
            pass

        @HinteDI.inject
        def invalid_injection(foo: UnimplementedBase):
            pass

        expected_exception = InjectionException(f"Could not inject an implementation of abstract base class "
                                                f"{UnimplementedBase} because no implementations exist.")

        with pytest.raises(InjectionException) as actual_exception:
            invalid_injection()
            assert str(expected_exception) == str(actual_exception)

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

    def test_inject_given_implementation_factory_returned_when_calling_from_key_then_correct_dependency_returned(self):
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

        assert type(Injected().dependency.from_key("1")) == FirstDependency

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

        expected_exception = InjectionException(f"Could not resolve key '2' or find a default implementation for class"
                                                f"{BaseWithNoDefault}")

        with pytest.raises(InjectionException) as actual_exception:
            Injected().dependency.from_key("2")
            assert str(expected_exception) == str(actual_exception)
