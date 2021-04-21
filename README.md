# ds - docker snapshot

`ds` is a development utility for managing snapshots inside a docker container.

Personally I use it to quickly save the state of my development database, try out something that mutates the state - a data migration or user interaction - and return to the initial state. Often repeatedly, because trial and error is essential. You can probably use it on any sort of stored data, probably. 

Note: This repository is still a work in progress.

## Installing
```bash
# Note: excutable will be called `ds`
pip install docker-snapshot
```

Shell completion:
```bash
# For Bash, add this to ~/.bashrc:
eval "$(_DS_COMPLETE=source_bash ds)"

# For Zsh, add this to ~/.zshrc:
eval "$(_DS_COMPLETE=source_zsh ds)"
```


## Usage

Create a snapshot
```bash
ds create name-goes-here
# or auto-generate a name
ds create 
```

Restore a snapshot
```bash
ds restore name-goes-here
# or restore the latest snapshot
ds restore
```

List snapshots
```bash
ds ls
```

Delete snapshots
```bash
ds delete name-goes-here
```

## Example project setup
In this example we use `ds` to create and restore database snapshots in our development environment. The projects `docker-compose.yml` file could look something like this:
```
version: "3.8"
services:
  db:
    container_name: db
    restart: always
    image: postgres:13
    env_file: .env
    ports:
      - 5432:5432
    volumes:
      - db-volume:/var/lib/postgresql/data
  ...
```

1) Browse to your project root
```bash
cd code/your-awesome-project
```

2) Create `ds.yaml` template file
```bash
ds init
```

3) Edit your `ds.yaml`
```yaml
# The target container
container_name: "db"

# The directory inside said container that you want to snapshot
directory: "/var/lib/postgresql/data"

# Identifier to separate projects, this allows you:
# - To have multiple projects with the same container name
# - To have multiple setups (ie. docker-compose / kind) for the same project
namespace: "your-awesome-project"
```
