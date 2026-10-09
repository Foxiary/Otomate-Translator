// The toolkits the app can drive. Each engine is a folder under engines/ whose
// files are copied into that engine's own workspace; the user switches between
// them from the rail, and every engine keeps its own workspace and form values.
const engines = [
  {
    id: 'otomate',
    name: 'Otomate',
    subtitle: 'Idea Factory · CPK, STCM2L, FFU',
    dir: 'otomate',
    copy: ['tools', 'build.py', 'fonts.json', 'DICH.md', 'CLAUDE.md', 'Font'],
    docs: [['Translation workflow', 'DICH.md'], ['Format notes', 'CLAUDE.md'],
      ['Tool reference', 'tools/README.md'], ['Font setup', 'Font/README.md']],
    flow: 'Create a sheet → translate column C → merge and relink → apply by ID → repack.',
    modules: ['PIL', 'fontTools', 'openpyxl', 'numpy'],
    hashes: require('./engine-update.json'),
    groups: ['Build', 'Fonts', 'Archives', 'Sheets', 'Apply', 'Executable', 'Diagnostics'],
    symbols: {Build: '◈', Fonts: 'Aa', Archives: '▤', Sheets: '▦', Apply: '↗', Executable: '⌘', Diagnostics: '◎'},
    summaries: {
      Build: 'Create the translated SYSTEM.cpk from your project assets.',
      Fonts: 'Generate, inspect, and adjust FFU bitmap fonts.',
      Archives: 'Explore and repack game containers and assets.',
      Sheets: 'Extract, align, and prepare translation workbooks.',
      Apply: 'Write translations back into game resources.',
      Executable: 'Inspect and patch text stored in ExeFS.',
      Diagnostics: 'Check rendered text against game font metrics.'
    },
    tools: require('./catalog-otomate').tools
  },
  {
    id: 'unity',
    name: 'Unity',
    subtitle: 'UnityPy · bundles, TextMeshPro, IL2CPP',
    dir: 'unity',
    copy: ['tools', 'README.md', 'docs'],
    docs: [['Engine guide', 'README.md'], ['Tool reference', 'tools/README.md'],
      ['Data layout', 'docs/01-data-layout.md'], ['Text rendering', 'docs/02-text-rendering.md'],
      ['Repacking', 'docs/04-repacking.md']],
    flow: 'Export text to a sheet → translate → apply the sheet into the bundles → check layout → package the mod.',
    modules: ['UnityPy', 'PIL', 'openpyxl', 'numpy', 'fontTools', 'Crypto', 'lz4'],
    hashes: {},
    groups: require('./catalog-unity').groups,
    symbols: require('./catalog-unity').symbols,
    summaries: require('./catalog-unity').summaries,
    tools: require('./catalog-unity').tools
  }
];

module.exports = {engines};
