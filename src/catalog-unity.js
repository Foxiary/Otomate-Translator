// Tools of the Unity engine (engines/unity/tools). Ids carry a `unity-` prefix so
// they never collide with the Otomate catalog in saved form values.
const A = (name, kind = 'text', help = '', optional = false) => ({name, kind, help, positional: true, required: !optional});
const V = (name, kind = 'text', help = '', required = false, repeat = false) => ({name, kind, help, required, repeat});
const B = (name, help = '') => ({name, kind: 'bool', help});
const T = (id, group, title, description, script, prefix, args, note = '') => ({id: `unity-${id}`, group, title, description, script, prefix, args, note});

const DRY = 'Dry run by default; tick apply to write. When the output is the input file itself, a .bak copy is kept.';
const UV = V('--unity-version', 'text', 'Fallback Unity version for files that carry none, e.g. 2021.3.0f1');
const PACKER = V('--packer', 'text', 'auto (lz4 for bundles, none for .assets), lz4, lzma, none, original');

const groups = ['Dump', 'Inspect', 'Text', 'Layout', 'Fonts', 'Executable', 'Release'];
const symbols = {Dump: '⇣', Inspect: '◎', Text: '▦', Layout: '▭', Fonts: 'Aa', Executable: '⌘', Release: '◈'};
const summaries = {
  Dump: 'Read ExeFS and RomFS straight out of an NSP with your prod.keys.',
  Inspect: 'See what a bundle or .assets file holds before editing it.',
  Text: 'Translate TextAssets through a spreadsheet, or fix terms in place.',
  Layout: 'Fit translated text to its TextMeshPro box: size, wrapping, auto-size.',
  Fonts: 'Swap the TTF of a dynamic font, or bake new glyphs into a static atlas.',
  Executable: 'Patch IL2CPP string literals and build IPS32 code patches.',
  Release: 'Package the mod for Ryujinx and Atmosphere.'
};

const tools = [
  T('exefs', 'Dump', 'Extract ExeFS', 'Write main, main.npdm and the decompressed main.flat from a game or update NSP.', 'tools/switchfs.py', ['exefs'],
    [A('NSP', 'file'), A('output folder', 'dir'), V('--keys', 'file', 'prod.keys; defaults to the one in Ryujinx/system')]),
  T('romfs', 'Dump', 'Extract RomFS', 'Extract the RomFS of every NCA in an NSP (base game or DLC) into <out>/<title id>/romfs.', 'tools/switchfs.py', ['romfs'],
    [A('NSP', 'file'), A('output folder', 'dir'), V('--keys', 'file', 'prod.keys; defaults to the one in Ryujinx/system'), B('--list', 'Only list the files'), V('--show', 'number', 'How many file names to print')],
    'Update NSPs (BKTR patch RomFS) are not supported; extract the base game.'),
  T('nso', 'Dump', 'Decompress NSO', 'Lay the three LZ4 segments of an NSO out as a flat memory image.', 'tools/switchfs.py', ['nso'],
    [A('NSO (main)', 'file'), A('output flat image', 'save')]),

  T('ls', 'Inspect', 'List objects', 'List objects in a bundle or .assets file, or count them per type.', 'tools/unityls.py', [],
    [A('bundle or .assets', 'file'), V('--type', 'text', 'Only this type, e.g. TextAsset, Font, MonoBehaviour'), V('--name', 'text', 'Only names matching this glob'), B('--summary', 'Count objects per type'), UV]),

  T('text-dump', 'Text', 'Dump TextAssets', 'Write each TextAsset to <name>.txt exactly as stored.', 'tools/textasset.py', ['dump'],
    [A('bundle or .assets', 'file'), A('output folder', 'dir'), V('--name', 'text', 'Only names matching this glob'), UV]),
  T('text-import', 'Text', 'Import TextAssets', 'Replace every TextAsset whose dumped .txt was edited; JSON must stay valid.', 'tools/textasset.py', ['import'],
    [A('bundle or .assets', 'file'), A('folder from Dump', 'dir'), V('--out', 'save', 'Output file', true), PACKER, B('--apply', 'Write the file'), UV], DRY),
  T('text-replace', 'Text', 'Replace a term', 'Swap one string inside one TextAsset; JSON structure is guarded.', 'tools/textasset.py', ['replace'],
    [A('bundle or .assets', 'file'), A('TextAsset name'), A('old text'), A('new text'), V('--count', 'number', 'Refuse unless it occurs exactly this many times'), V('--out', 'save', 'Output file', true), PACKER, B('--apply', 'Write the file'), UV], DRY),
  T('sheet-export', 'Text', 'Export JSON to sheet', 'Write the string values of JSON TextAssets to an XLSX: ID | Source | Translation.', 'tools/jsonsheet.py', ['export'],
    [A('bundle or .assets', 'file'), A('output XLSX', 'save'), V('--name', 'text', 'Only TextAssets matching this glob'), V('--key', 'text', 'Only values whose key matches this regex, e.g. ^(jp|text)$'), V('--path', 'text', 'Only JSON pointers matching this regex'), B('--all', 'Keep empty and letter-less values'), B('--nested', 'Open strings that are themselves JSON, such as choice lists'), UV]),
  T('sheet-apply', 'Text', 'Apply sheet', 'Write the Translation column back at each value\'s exact position; formatting and BOM are kept.', 'tools/jsonsheet.py', ['apply'],
    [A('bundle or .assets', 'file'), A('translated XLSX', 'file'), V('--out', 'save', 'Output file', true), V('--sheet-name', 'text', 'Worksheet (default: first)'), V('--token', 'text', 'Regex that must occur equally often in Source and Translation, one per line', false, true), B('--force', 'Write even where Source no longer matches the file'), PACKER, B('--apply', 'Write the file'), UV],
    'Rows whose Source no longer matches the file are skipped. Write <empty> to blank a value. ' + DRY),

  T('tmp-list', 'Layout', 'Find text boxes', 'List TextMeshPro components with their box, size, auto-size, wrapping and spacing.', 'tools/tmp.py', ['list'],
    [A('bundle or .assets', 'file'), V('--text', 'text', 'Only components whose text matches this regex'), V('--object', 'text', 'Only GameObjects matching this glob'), V('--nodes-from', 'file', 'UI bundle to borrow the TMP type tree from (.assets files)'), UV]),
  T('tmp-set', 'Layout', 'Adjust text box', 'Change one TextMeshPro component by path id: box size and position, font size, auto-size range, wrapping, overflow, spacing, margins.', 'tools/tmp.py', ['set'],
    [A('bundle or .assets', 'file'), A('path id', 'number'), V('--width', 'number', 'Box width'), V('--height', 'number', 'Box height'), V('--x', 'number', 'Box position x'), V('--y', 'number', 'Box position y'), V('--font-size', 'number'), V('--auto-size', 'text', 'on or off'), V('--size-min', 'number', 'Smallest auto-size'), V('--size-max', 'number', 'Largest auto-size; keep the original size'), V('--wrap', 'text', 'on or off'), V('--overflow', 'number', '0 overflow, 1 ellipsis, 2 masking, 3 truncate, 4 scroll, 5 page'), V('--char-spacing', 'number'), V('--line-spacing', 'number'), V('--margin', 'text', 'left,top,right,bottom'), V('--nodes-from', 'file', 'UI bundle to borrow the TMP type tree from'), V('--out', 'save', 'Output file', true), PACKER, B('--apply', 'Write the file'), UV], DRY),

  T('tmpfont-info', 'Fonts', 'List TMP fonts', 'List TextMeshPro font assets: static or dynamic, atlas, padding, free space, and which requested characters are missing.', 'tools/tmpfont.py', ['info'],
    [A('bundle or .assets', 'file'), V('--charset', 'text', 'vietnamese or latin', false, true), V('--text', 'text', 'Characters to check'), V('--sheet', 'file', 'XLSX whose column C to check'), UV]),
  T('tmpfont-verify', 'Fonts', 'Verify atlas generator', 'Rebuild existing glyphs of a static font from its own TTF and compare: run before trusting Add glyphs on a new game.', 'tools/tmpfont.py', ['verify'],
    [A('bundle or .assets', 'file'), A('font asset name'), A('source TTF', 'file'), V('--face-index', 'number'), V('--sample', 'number', 'How many glyphs to compare'), UV]),
  T('tmpfont-add', 'Fonts', 'Add glyphs to static font', 'Bake missing characters into a static TMP atlas as SDF tiles, the way TMP does, without the Unity Editor.', 'tools/tmpfont.py', ['add'],
    [A('bundle or .assets', 'file'), A('font asset name'), A('TTF to draw from', 'file'), V('--face-index', 'number'), V('--charset', 'text', 'vietnamese or latin', false, true), V('--text', 'text', 'Characters to add'), V('--sheet', 'file', 'Add every character used in column C'), B('--replace', 'Re-bake characters that already exist, so old and new letters match'), V('--preview', 'save', 'PNG of a sample line'), V('--preview-text', 'text'), V('--out', 'save', 'Output file', true), PACKER, B('--apply', 'Write the file'), UV],
    'Run Verify atlas generator on this asset first. ' + DRY),
  T('font-list', 'Fonts', 'List fonts', 'List Font objects with the face and character count of their embedded TTF.', 'tools/font.py', ['list'],
    [A('bundle or .assets', 'file'), UV]),
  T('font-extract', 'Fonts', 'Extract font', 'Save the TTF embedded in a Font object.', 'tools/font.py', ['extract'],
    [A('bundle or .assets', 'file'), A('font name'), A('output TTF', 'save'), UV]),
  T('font-replace', 'Fonts', 'Replace font', 'Put a new TTF into a Font object; dynamic TextMeshPro fonts render from it.', 'tools/font.py', ['replace'],
    [A('bundle or .assets', 'file'), A('font name'), A('new TTF', 'file'), V('--out', 'save', 'Output file', true), PACKER, B('--apply', 'Write the file'), UV],
    'The same font is often duplicated across bundles; replace every copy. ' + DRY),
  T('font-coverage', 'Fonts', 'Check coverage', 'Report characters a TTF cannot draw, from a charset, text, or a sheet\'s Translation column.', 'tools/font.py', ['coverage'],
    [A('TTF', 'file'), V('--charset', 'text', 'vietnamese or latin', false, true), V('--text', 'text', 'Characters to check'), V('--sheet', 'file', 'XLSX whose column C to check')]),

  T('il2cpp-find', 'Executable', 'Find IL2CPP literal', 'Search the string literals of global-metadata.dat.', 'tools/il2cpp.py', ['find'],
    [A('global-metadata.dat', 'file'), A('text'), B('--contains', 'Substring match instead of equality')]),
  T('il2cpp-patch', 'Executable', 'Patch IL2CPP literal', 'Replace one literal in place; the new text may not be longer in UTF-8 bytes.', 'tools/il2cpp.py', ['patch'],
    [A('global-metadata.dat', 'file'), A('old text'), A('new text'), V('--out', 'save', 'Output file', true), B('--apply', 'Write the file')],
    'The patch is tied to this exact game version. ' + DRY),
  T('ips32', 'Executable', 'Build IPS32 patch', 'Write <build id>.ips from RVA:OLD:NEW patches, each checked against main.flat.', 'tools/ips32.py', [],
    [A('NSO (main)', 'file'), A('output folder', 'dir'), V('--patch', 'text', 'RVA:OLDHEX:NEWHEX, one per line', true, true), V('--flat', 'file', 'Flat image (default: main.flat beside the NSO)'), B('--apply', 'Write the .ips')],
    'Offsets are RVAs, not the dump.cs Offset column. ' + DRY),

  T('release', 'Release', 'Package release', 'Zip the mod for Ryujinx and Atmosphere; .resS and scratch files are left out.', 'tools/release.py', [],
    [V('--title-id', 'text', 'Base game title id, 16 hex digits', true), V('--romfs', 'dir', 'Mod RomFS folder', true), V('--exefs', 'dir', 'Mod ExeFS folder (.ips)'), V('--aoc', 'text', 'DLC as TITLEID=folder, one per line', false, true), V('--name', 'text', 'Mod folder name', true), V('--version', 'text', 'Release label', true), V('--out-dir', 'dir', 'Where to write the zips', true), B('--build', 'Write the zips (otherwise print the plan)')])
];

module.exports = {tools, groups, symbols, summaries};
