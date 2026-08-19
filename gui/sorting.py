import re


def natural_sort_key(value):
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r'(\d+)', str(value))]
