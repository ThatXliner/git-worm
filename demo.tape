# git-worm demo — run with: vhs demo.tape
# Produces demo.gif

Output demo.mp4

Set Shell "bash"
Set FontSize 14
Set Width 900
Set Height 500
Set Padding 20
Set TypingSpeed 60ms
Set Theme "Catppuccin Mocha"
Set WindowBar Colorful
Set BorderRadius 10

# --- Setup: create a demo repo with gitignored files ---

Hide
Type "export FORCE_COLOR=1"
Enter
Sleep 200ms
Type "rm -rf /tmp/myapp && mkdir /tmp/myapp && cd /tmp/myapp && git init"
Enter
Sleep 500ms
Type "git commit --allow-empty -m 'initial commit'"
Enter
Sleep 500ms
Type "echo 'SECRET=hunter2' > .env"
Enter
Type "mkdir -p .venv/lib && echo 'fake' > .venv/lib/site.py"
Enter
Type "echo '.env' >> .gitignore && echo '.venv/' >> .gitignore"
Enter
Type "git add .gitignore && git commit -m 'add gitignore'"
Enter
Sleep 500ms
Type 'eval "$(git-worm shell-init)"'
Enter
Sleep 500ms
Type "clear"
Enter
Sleep 500ms
Show

# --- Scene 1: Show that gitignored files exist in our repo ---

Type "# Our repo has gitignored files: .env, .venv/"
Enter
Sleep 1s

Type "ls .env .venv/"
Enter
Sleep 2s

# --- Scene 2: The problem — plain git worktree loses them ---

Type "# The problem: git worktree doesn't copy them"
Enter
Sleep 1s

Type "git worktree add .worktrees/bugfix -b bugfix"
Enter
Sleep 1.5s
Type "cd .worktrees/bugfix"
Enter
Type "ls .env .venv/"
Enter
Sleep 2.5s

# --- Scene 3: More pain — you have to copy manually ---

Type "# You have to copy everything manually..."
Enter
Sleep 1s

Type "cp ../../.env .env && cp -r ../../.venv .venv"
Enter
Sleep 1.5s

Type "# Every. Single. Time."
Enter
Sleep 2s

# Clean up the raw worktree
Hide
Type "cd ../.."
Enter
Type "git worktree remove .worktrees/bugfix && git branch -d bugfix"
Enter
Sleep 500ms
Type "clear"
Enter
Sleep 500ms
Show

# --- Scene 4: The fix — one command does it all ---

Type "# With git-worm, one command does it all"
Enter
Sleep 1s

Type "git worm new feat-login"
Enter
Sleep 3s

Type "# .env and .venv/ are already there"
Enter
Sleep 1s

Type "cd .worktrees/feat-login"
Enter
Type "ls .env .venv/"
Enter
Sleep 2.5s

Type "git worm list"
Enter
Sleep 2.5s

Type "cd /tmp/myapp && git worm rm feat-login"
Enter
Sleep 2s

Sleep 1s
