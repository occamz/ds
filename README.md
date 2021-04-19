# ds - docker snapshot utility

Note:
- This repository is still a work in progress.
- Running `docker volume prune` removes the snapshots. This might need some thinking.


### Install:
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install --editable .
```

### Shell completion:
```bash
# For Bash, add this to ~/.bashrc:
eval "$(_DS_COMPLETE=source_bash ds)"

# For Zsh, add this to ~/.zshrc:
eval "$(_DS_COMPLETE=source_zsh ds)"
```

### Example setup (postgres snapshots):
#### 1) Browse to your project root
```bash
cd code/your-awesome-project
```

#### 2) Create `ds.yaml` template file
```bash
ds init
```

#### 3) Edit your `ds.yaml`
```yaml
# The target container
container_name: "postgres"

# The directory inside said container that you want to snapshot
directory: "/var/lib/postgresql/data"

# Identifier to separate projects, this allows you:
# - To have multiple projects with the same container name
# - To have multiple setups (ie. docker-compose / kind) for the same project
namespace: "your-awesome-project"
```

### Practical usage:

#### Create snapshot
```bash
ds create name-goes-here
# or auto-generate a name
ds create 
```

#### Restore snapshot
```bash
ds restore name-goes-here
# or restore the latest snapshot
ds restore
```

#### List snapshots
```bash
ds ls
```

#### List snapshots
```bash
ds delete name-goes-here
```