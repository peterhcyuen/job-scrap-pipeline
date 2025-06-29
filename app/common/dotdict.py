class DotDict(dict):
    """A dictionary that allows attribute-style access."""

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(f"'DotDict' object has no attribute '{key}'")

    def __setattr__(self, key, value):
        self[key] = value

    def __delattr__(self, key):
        try:
            del self[key]
        except KeyError:
            raise AttributeError(f"'DotDict' object has no attribute '{key}'")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for k, v in self.items():  # make nested dicts dottable
            if isinstance(v, dict):
                self[k] = DotDict(v)
