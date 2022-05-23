# HinteDI - simple dependency injection system with type hints

This package is a small utility I have been using in my own projects, a super simple tool for basic dependency 
injection in python based on type hints and decorators.

This package exposes three classes: HinteDI, InjectionException and InstanceSentinel. Import HinteDI and use 
```@HinteDI.singleton``` and ```@HinteDI.instance``` to create dependencies and ```@HinteDI.inject``` to mark a 
function as requiring dependency injection. Type hint the dependencies in the injected function and HinteDI will 
inject the dependencies for you. See the docs at [GitHub pages](https://eddiethecubehead.github.io/HinteDI/) for better documentation about the package.
