# BDBag/RO "Meta-Manifest" Examples
Sample configuration files for creating and updating BDBags with Research Object metadata from JSON "meta-manifests".

The directory `samples/sample1` contains three files, `metadata.json`, `ro_metadata.json` and `remote-files.json` that can be used to create 
a `bdbag` using exclusively remote file references via `fetch.txt`, but with a complete set of bag-local RO metadata and customizable `bag-info.txt` metadata fields.

Invoke the following `bdbag` command from the bdbag source root directory to test this example:
```bash
mkdir ro-test
bdbag --update --remote-file-manifest ./examples/metamanifests/samples/sample1/remote-files.json --metadata-file ./examples/metamanifests/samples/sample1/metadata.json --ro-metadata-file ./examples/metamanifests/samples/sample1/ro_metadata.json ./ro-test
```