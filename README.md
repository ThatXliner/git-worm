# git-werk

A better git worktree manager. Built with [Xclif](https://github.com/ThatXliner/xclif).

## Why?

`git worktree` is powerful but raw. git-werk adds:

- **Automatic file management** — gitignored files (`.env`, `.venv`, `node_modules`, etc.) are copied into new worktrees so switching feels like `git switch`
- **Smart package manager detection** — pnpm/bun/Yarn PnP users don't get unnecessary `node_modules` copies
- **Nice UI** — Rich-formatted output, tree views, colored status

## Install

```bash
pip install git-werk
```

Or with [uv](https://github.com/astral-sh/uv):

```bash
uv tool install git-werk
```

## Usage

```bash
# Create a new worktree (copies .env, .venv, etc. automatically)
git werk new feat-login

# Create from a specific ref
git werk new feat-login --from-ref main

# List all worktrees
git werk list

# Print worktree path
git werk switch feat-login

# Remove a worktree
git werk rm feat-login

# Remove even if dirty
git werk rm feat-login --force

# Shell integration (add to .bashrc/.zshrc)
eval "$(git-werk shell-init)"
# Then: werk switch feat-login  (auto-cds)
```

## Configuration

Optional `.git-werk.toml` in your repo root:

```toml
[settings]
worktree_dir = ".worktrees"  # default

[[share]]
path = ".env*"
strategy = "copy"

[[share]]
path = "node_modules"
strategy = "ignore"

[[share]]
path = "target"
strategy = "symlink"
```

Strategies: `copy`, `reflink` (COW, falls back to copy), `symlink`, `ignore`.

When a config file is present, it replaces the default behavior entirely.

## Default Behavior (no config)

1. All gitignored files/dirs are detected
2. `.git/` and `.worktrees/` are excluded
3. Files are plain-copied, directories are reflinked (with copy fallback)
4. `node_modules/` is skipped if pnpm, bun, or Yarn PnP is detected

## License

MIT
