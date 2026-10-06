# Contributing

Bug reports with the Blender version, the add-on version and the exact steps are the most useful contribution. Pull
requests are welcome; please keep them small and include or update the test of the add-on you change.

## Layout

```
terrain_blend/   retopo_kit/   fivem_toolkit/   ue5_bridge/    one folder per add-on (blender_manifest.toml inside)
test_<id>.py                                                  one headless test per add-on
docs/                                                         guides (English and Turkish) and screenshots
```

Every add-on is an extension for Blender 5.0 or newer (`blender_manifest.toml`, `blender_version_min = "5.0.0"`).

## Run a test

Each test builds real scenes in a background Blender and exits with a non-zero code when something fails. Run it from this
folder, once per Blender version you have (5.0 and 5.2 are the supported range):

```
blender -b --factory-startup --python-exit-code 1 --python test_terrain_blend.py
blender -b --factory-startup --python-exit-code 1 --python test_retopo_kit.py
blender -b --factory-startup --python-exit-code 1 --python test_ue5_bridge.py
blender -b --factory-startup --python-exit-code 1 --python test_fivem_toolkit.py
```

Notes:

- `test_fivem_toolkit.py` enables Sollumz as the extension `sollumz_dev` (edit the module name in `reset()` of the test if
  yours is called differently). Without Sollumz it prints a note and skips the prop, MLO and ped parts.
- `test_retopo_kit.py` also checks QRemeshify when it is installed.
- Blender 5.0 and 5.2 differ. On 5.0 set the environment variable `BDEV_BACKEND=opengl` before running
  `test_terrain_blend.py`: on the OpenGL backend only the Lite material is rendered and checked. On 5.2 leave it unset
  (Vulkan). `AK_LAYERS` sets the number of layers of that test (default 14).

## Build a release zip

```
blender --command extension build --source-dir terrain_blend --output-dir .
```

This validates the manifest and writes `terrain_blend-<version>.zip`. Install it with **Preferences > Get Extensions >
Install from Disk**.

## Style

- Python 3.13 (what Blender 5.x ships), 120 columns, [ruff](https://docs.astral.sh/ruff/) with rules `E`, `F`, `W`, `B`.
- All user-visible text is English in the code, with a Turkish translation in the add-on's `i18n.py`.
- Never change the user's scene silently: work on copies, or make the change an explicit button.
- Known differences between Blender 5.0 and 5.2 are documented in the guides; test both.

## License

By contributing you agree that your contribution is licensed under GPL-3.0-or-later, like the rest of the project.
