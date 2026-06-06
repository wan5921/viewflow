class Meta(type):
    def __new__(mcs, name, bases, attrs):
        print("Meta.__new__", name)
        return super().__new__(mcs, name, bases, attrs)

class Base(metaclass=Meta):
    def __init_subclass__(cls, **kwargs):
        print("Base.__init_subclass__", cls.__name__)
        super().__init_subclass__(**kwargs)

    def __new__(cls, *args, version=None, **kwargs):
        if version is not None:
            new_cls = type(f"{cls.__name__}V{version}", (cls,), {'version': version})
            return object.__new__(new_cls)
        return object.__new__(cls)

class MyFlow(Base):
    pass

print("--- Instantiating MyFlow(version=2) ---")
f = MyFlow(version=2)
print(f.__class__)
print(f.version)
