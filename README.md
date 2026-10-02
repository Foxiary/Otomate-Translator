# VE-ES Desktop

An Electron interface for the [VE-ES toolkit](https://github.com/Foxiary/VE-ES). It includes the repository's Python scripts and exposes all 34 current command-line operations through forms with file pickers, live output, and cancellation. The included `ffugen.py` is updated to the latest upstream revision, including dark outline rendering with `--stroke`.

The app does **not** include game data, fonts, translation workbooks, or keys. Supply your own files in a project folder. Scripts, `build.py`, `fonts.json`, and source documentation are copied into a new folder when you select it. Existing files are kept.

## Start

1. Install Node.js and Python 3.
2. Clone with the toolkit submodule: `git clone --recursive https://github.com/Foxiary/VE-ES-Desktop.git`. In an existing clone, run `git submodule update --init`.
3. From this folder, run `npm install` and `npm start`.
4. In the app, open **Python environment → Set up Python packages**. This creates a private environment under the app's user data folder and installs Pillow, fontTools, openpyxl, and NumPy. You can instead choose an existing Python executable with those packages installed.
5. Use **Workspace** to choose the folder holding your game assets. See **Source documentation** for the expected layout and translation workflow.

If npm blocks Electron's install script, run `npm approve-scripts electron` and `node node_modules/electron/install.js` once.

## Package

- macOS: `npm run dist:mac`
- Windows x64: `npm run dist:win -- --x64`
- Linux: `npm run dist:linux`

This delivery includes a macOS Apple Silicon DMG, plus a Windows x64 installer and portable executable. The builds are unsigned, so macOS Gatekeeper or Windows SmartScreen may show a warning. The Windows packages were built on macOS and could not be launched here; build on Windows for native runtime testing.

## How the app works

Each operation launches an original Python script with an argument array, without a shell. Repeated values such as `--font` and `--sheet` use one value per line. Relative paths resolve from the selected workspace. Run output appears in the log. The **Stop** button terminates the current process.

`build.py` is specific to the Virche project layout. Most tools also accept input from another Otomate game as documented upstream. `translate_glossary.py` contains fixed sample translations from the source repository; its form labels them as samples.

On startup, the app updates scripts and configuration in an existing workspace only when they still match the previous bundled revision. User edited files are preserved. New files are added. Retired upstream scripts may remain in older workspaces but no longer appear in the tool catalog.

`engine/` is a git submodule of [Foxiary/VE-ES](https://github.com/Foxiary/VE-ES), currently at commit `019ccce`. To move it to a newer upstream revision, run `git -C engine pull origin master` and commit the new `engine` pointer. Add the hashes of the files being replaced to `src/engine-update.json` first, so existing workspaces that still hold the old bundled files are updated.
