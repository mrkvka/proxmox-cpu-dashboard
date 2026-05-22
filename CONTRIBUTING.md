# Contributing

## Development

```bash
make test          # Python unit tests + py_compile
make shellcheck    # shell scripts
```

On a Proxmox VE 9.x host:

```bash
bash install.sh
bash scripts/verify-patch.sh
```

## Version bump

1. Edit `VERSION` at repo root  
2. Run `bash install.sh` on a test node  
3. Update `CHANGELOG.md`  

## Pull requests

- Keep changes focused; match existing shell/Python style  
- Do not reintroduce a separate HTTP API on :8087  
- External integrations belong in separate projects; document endpoints in `docs/API.md` only  

## Reporting issues

Include:

- `pveversion -v`  
- Output of `bash scripts/verify-patch.sh`  
- `perl -c /usr/share/perl5/PVE/API2/Nodes.pm`  

## UI changes

Edit files under `src/ui/` (load order in [docs/PLUGIN.md](docs/PLUGIN.md)). Run `bash install-ui.sh` on a test node.
