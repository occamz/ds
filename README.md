# ds - docker snapshot utility

Install:
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install --editable .
```

Shell completion:
```bash
# For Bash, add this to ~/.bashrc:
eval "$(_DS_COMPLETE=source_bash ds)"

# For Zsh, add this to ~/.zshrc:
eval "$(_DS_COMPLETE=source_zsh ds)"
```