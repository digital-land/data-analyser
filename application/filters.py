def do_something(value):
    if isinstance(value, str):
        return f"Did something with {value}!"
    else:
        return value
