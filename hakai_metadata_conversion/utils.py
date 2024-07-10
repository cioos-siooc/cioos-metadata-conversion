
def drop_empty_values(dictionary):
    return {k: v for k, v in dictionary.items() if v}