def pytest_collection_modifyitems(items):
    for item in items:
        tags = set()
        obj = getattr(item, "obj", None)
        cls = getattr(item, "cls", None)

        if obj is not None:
            tags.update(getattr(obj, "tags", set()))
        if cls is not None:
            tags.update(getattr(cls, "tags", set()))

        for tag in tags:
            item.add_marker(tag)
