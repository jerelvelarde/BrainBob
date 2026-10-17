# Publish the Bob pilot to Hugging Face

Target: `JerelVelarde/bob-benchmark` (dataset repository).

The build uses committed Git objects only, with an allowlist for the two benchmark packages and specification. It never uploads the repository working directory. The dataset card has three explicit configurations so the different suites remain separate. Public gold is documented; no hidden-test claims are made. No license is invented for the source project.

```sh
python3 publishing/huggingface/build.py --ref HEAD --out /tmp/bob-hf-release
```

Review `README.md` and `release-manifest.json` in that new output directory. Verify data loading with `datasets`, run the bundled tests from an extracted `bob-source.zip`, and upload **only the eight generated files** through the Hugging Face dataset upload page or authenticated `huggingface_hub` client. The browser may already have a login even if the CLI does not. Do not extract browser credentials or put tokens in the repository.

For an authenticated client, create the public dataset if absent, then upload the generated directory. If the target exists, inspect its contents first; do not overwrite unrelated work. Record the returned Hugging Face commit and verify the public card/files before reporting publication. Adding an open license requires a maintainer's explicit choice; the current card states that reuse terms are unspecified.

`release-manifest.json` records SHA-256 for every source file and each generated artifact other than the manifest itself. ZIP timestamps are fixed for deterministic bytes and do not represent file creation times. To reproduce a release, use its recorded source revision.
