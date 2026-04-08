from xclif import command


@command("shell-init")
def _() -> None:
    """Output a `worm` shell function that wraps git-worm with cd integration.

    The `worm switch` command will cd into the worktree directory,
    which is not possible with a plain subprocess. All other commands
    are forwarded to git-worm as-is.

    Add `eval "$(git-worm shell-init)"` to your shell rc file.
    """
    print("""\
worm() {
    if [ "$1" = "switch" ] && [ -n "$2" ]; then
        local wt_dir
        wt_dir="$(git rev-parse --show-toplevel)/.worktrees/$2"
        if [ -d "$wt_dir" ]; then
            cd "$wt_dir"
            echo "Switched to worktree '$2' @ $wt_dir"
        else
            echo "Error: No worktree found for '$2'" >&2
            return 1
        fi
    elif [ "$1" = "new" ]; then
        local _worm_out _worm_cd
        _worm_out="$(git-worm "$@")" || { echo "$_worm_out"; return 1; }
        _worm_cd="$(echo "$_worm_out" | grep '^__worm_cd__:' | cut -d: -f2-)"
        echo "$_worm_out" | grep -v '^__worm_cd__:'
        if [ -n "$_worm_cd" ] && [ -d "$_worm_cd" ]; then
            cd "$_worm_cd"
        fi
    else
        git-worm "$@"
    fi
}""")
