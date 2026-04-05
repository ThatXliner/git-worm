from xclif import command


@command("shell-init")
def _() -> None:
    """Output a shell function for cd integration.

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
    else
        git-worm "$@"
    fi
}""")
