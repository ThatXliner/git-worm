from dataclasses import replace as _replace


def _get_remove():
    from git_worm.routes.remove import _ as remove
    return remove


# Alias: `git worm rm` → `git worm remove`
_ = _replace(_get_remove(), name="rm")
