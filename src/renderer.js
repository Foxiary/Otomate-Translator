const $ = id => document.getElementById(id);
let state;
let activeGroup = null;
let activeId = null;
let running = false;
let formValues = {};
let currentLog = '';

function titleOf(name) { return name.replace(/^--/, '').replace(/[-_]/g, ' '); }
function elt(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}
function engine() { return state.engines.find(item => item.id === state.settings.engine); }
function tools() { return engine().tools; }
function tool() { return tools().find(item => item.id === activeId); }
// Land on the first tool of the engine unless the current selection belongs to it.
function selectDefault() {
  if (tool()) return;
  activeGroup = engine().groups.find(group => tools().some(t => t.group === group));
  activeId = tools().find(t => t.group === activeGroup)?.id;
}
function updateWorkspace() {
  $('workspace-name').textContent = state.workspace.split(/[\\/]/).pop() || 'Project';
  $('workspace-path').textContent = state.workspace;
}
function renderEngines() {
  const box = $('engines'); box.replaceChildren();
  for (const item of state.engines) {
    const button = elt('button', `engine-button ${item.id === state.settings.engine ? 'active' : ''}`);
    button.type = 'button';
    button.title = item.subtitle;
    button.append(elt('strong', '', item.name), elt('small', '', item.subtitle));
    button.addEventListener('click', () => switchEngine(item.id));
    box.append(button);
  }
}
async function switchEngine(id) {
  if (id === state.settings.engine) return;
  if (running) {showError('Wait for the current command to finish before switching engines.'); return;}
  captureValues();
  try {
    const result = await window.vees.setEngine(id);
    state.settings = result.settings; state.workspace = result.workspace;
    $('search').value = '';
    selectDefault();
    updatePython(result.python);
    render();
  } catch (error) {showError(error.message);}
}
function updatePython(check) {
  const badge = $('python-status');
  badge.className = `env-pill ${check.ok ? 'good' : 'bad'}`;
  badge.textContent = check.ok ? `Python ${check.version} · ready` : 'Python setup needed';
  badge.title = check.ok ? state.settings.python : check.message;
}
function renderGroups() {
  const nav = $('groups'); nav.replaceChildren();
  const {groups, symbols} = engine();
  for (const group of groups) {
    const count = tools().filter(t => t.group === group).length;
    const button = elt('button', `group-button ${activeGroup === group ? 'active' : ''}`);
    button.type = 'button';
    button.append(elt('span', 'icon', symbols[group]), elt('span', '', group), elt('span', 'count', String(count)));
    button.addEventListener('click', () => {
      captureValues(); activeGroup = group; $('search').value = '';
      const first = tools().find(t => t.group === group);
      if (first) activeId = first.id;
      render();
    });
    nav.append(button);
  }
}
function renderTools() {
  const query = $('search').value.toLowerCase().trim();
  const visible = tools().filter(t => query ? `${t.title} ${t.description} ${t.group} ${t.script}`.toLowerCase().includes(query) : t.group === activeGroup);
  $('group-title').textContent = query ? 'Search results' : activeGroup;
  $('group-subtitle').textContent = query ? `${visible.length} matching ${engine().name} commands.` : engine().summaries[activeGroup];
  $('tool-count').textContent = String(tools().length);
  const list = $('tool-list'); list.replaceChildren();
  if (!visible.length) list.append(elt('div', 'empty', 'No commands match this search.'));
  for (const t of visible) {
    const button = elt('button', `tool-card ${activeId === t.id ? 'active' : ''}`);
    button.type = 'button';
    const line = elt('div','tool-card-title');
    line.append(elt('span','',t.title),elt('span','', activeId === t.id ? '↗' : ''));
    button.append(line,elt('small','',t.description));
    button.addEventListener('click', () => {captureValues(); activeId = t.id; activeGroup = t.group; render();});
    list.append(button);
  }
}
function captureValues() {
  if (!state) return;
  const current = tool();
  if (!current) return;
  const values = {};
  for (const arg of current.args) {
    const input = document.querySelector(`[data-arg="${CSS.escape(arg.name)}"]`);
    if (input) values[arg.name] = arg.kind === 'bool' ? input.checked : input.value;
  }
  formValues[current.id] = values;
}
function renderForm() {
  const current = tool();
  $('breadcrumb').textContent = `${engine().name.toUpperCase()} / ${current.group.toUpperCase()} / ${current.script.toUpperCase()}`;
  $('tool-title').textContent = current.title;
  $('tool-description').textContent = current.description;
  $('notice').classList.toggle('hidden', !current.note);
  $('notice').textContent = current.note;
  const values = formValues[current.id] || state.settings.values[current.id] || {};
  const fields = $('form-fields'); fields.replaceChildren();
  for (const [index, arg] of current.args.entries()) {
    const field = elt('div',`field ${arg.kind === 'bool' ? 'toggle-field' : ''} ${arg.repeat || arg.help?.length > 85 ? 'wide' : ''}`);
    const label = elt('label','',titleOf(arg.name));
    label.htmlFor = `arg-${index}`;
    if (arg.required) label.append(elt('span','required','*'));
    let input;
    if (arg.kind === 'bool') {
      input = elt('input'); input.type = 'checkbox'; input.checked = !!values[arg.name];
      input.id = `arg-${index}`; input.dataset.arg = arg.name;
      const words = elt('div'); words.append(label);
      if (arg.help) words.append(elt('div','help',arg.help));
      field.append(input,words);
    } else {
      field.append(label);
      const row = elt('div','input-row');
      input = arg.repeat ? elt('textarea') : elt('input');
      if (!arg.repeat) input.type = arg.kind === 'number' ? 'text' : 'text';
      input.id = `arg-${index}`; input.dataset.arg = arg.name;
      input.value = values[arg.name] ?? '';
      input.placeholder = arg.repeat ? 'One value per line' : arg.kind === 'save' ? 'Choose an output path…' : arg.kind === 'dir' ? 'Choose a folder…' : arg.kind === 'file' ? 'Choose a file or folder…' : 'Optional';
      row.append(input);
      if (['file','dir','save'].includes(arg.kind)) {
        const browse = elt('button','browse','Browse'); browse.type = 'button';
        browse.addEventListener('click', async () => {
          try {
            const selected = await window.vees.choosePath(arg.kind, arg.repeat ? '' : input.value);
            if (selected) input.value = arg.repeat && input.value.trim() ? `${input.value.trim()}\n${selected}` : selected;
            input.focus();
          } catch (error) {showError(error.message);}
        });
        row.append(browse);
      }
      field.append(row);
      if (arg.help) field.append(elt('div','help',arg.help));
    }
    fields.append(field);
  }
  $('run-hint').textContent = `${current.script}${current.prefix.length ? ' ' + current.prefix.join(' ') : ''} · ${state.workspace}`;
  $('run-button').disabled = running;
  $('cancel-button').disabled = !running;
}
function render() {renderEngines();renderGroups();renderTools();renderForm();updateWorkspace();}
function showError(message) {
  $('notice').classList.remove('hidden');
  $('notice').textContent = message;
}
function setLog(text) {currentLog = text; $('log').textContent = text; $('log').scrollTop = $('log').scrollHeight;}
function status(text, css) {
  $('run-status').textContent = text;
  const dot = document.querySelector('.console-dot');
  dot.className = `console-dot ${css || ''}`;
}
function dialogContent(title, build) {
  $('dialog-title').textContent = title;
  const body = $('dialog-body');body.replaceChildren();build(body);
  $('info-dialog').showModal();
}
function paragraph(parent, text, cls = '') {parent.append(elt('p',cls,text));}
function action(parent, label, callback) {const b=elt('button','',label); b.type='button';b.addEventListener('click', callback);parent.append(b);}
function showDocs() {
  dialogContent('Source documentation', body => {
    paragraph(body,`The ${engine().name} engine's Python scripts are copied into its own workspace. The app does not include game assets, fonts, translations, or Nintendo keys.`);
    paragraph(body,`Recommended flow: ${engine().flow}`);
    for (const [label,name] of engine().docs) {
      action(body,label,async()=>{const error=await window.vees.openDocument(name);if(error)showError(error);});
    }
  });
}
function showPython() {
  dialogContent('Python environment', body => {
    paragraph(body,`The ${engine().name} tools need Python 3 with these modules: ${engine().modules.join(', ')}. Set up an isolated environment for this app, which installs the packages for every engine, or choose an existing Python installation.`);
    paragraph(body,`Current executable: ${state.settings.python}`,'mono');
    action(body,'Set up Python packages', async () => {
      try {await window.vees.setupPython();$('info-dialog').close();}
      catch(error){showError(error.message);}
    });
    action(body,'Choose Python executable', async () => {
      try {
        const result=await window.vees.choosePython();
        if(result){state.settings.python=result.python;updatePython(result.check);$('info-dialog').close();}
      } catch(error){showError(error.message);}
    });
  });
}

async function start() {
  state = await window.vees.state();
  formValues = structuredClone(state.settings.values || {});
  selectDefault();
  updatePython(state.python);
  render();
  $('search').addEventListener('input', renderTools);
  $('workspace-button').addEventListener('click', async () => {
    try {
      const result = await window.vees.chooseWorkspace();
      if (result) {state.workspace = result.workspace;updateWorkspace();renderForm();updatePython(result.python);}
    } catch(error){showError(error.message);}
  });
  $('open-folder').addEventListener('click', async () => {const error=await window.vees.openWorkspace();if(error)showError(error);});
  $('docs-button').addEventListener('click',showDocs);
  $('python-button').addEventListener('click',showPython);
  $('dialog-close').addEventListener('click',()=>$('info-dialog').close());
  $('clear-log').addEventListener('click',()=>setLog(''));
  $('tool-form').addEventListener('submit',event=>event.preventDefault());
  $('run-button').addEventListener('click',async()=>{
    if(running)return;
    captureValues();
    const current = tool();
    try {
      await window.vees.run(current.id,formValues[current.id]);
    } catch(error){showError(error.message);}
  });
  $('cancel-button').addEventListener('click',async()=>{await window.vees.cancel();});
  window.vees.on('run-start',event=>{
    running=true;renderForm();setLog(`$ ${event.command.map(x=>/\s/.test(x)?JSON.stringify(x):x).join(' ')}\n\n`);
    status('Running…','running');
  });
  window.vees.on('run-output',event=>{setLog(currentLog+event.text);});
  window.vees.on('run-end',event=>{
    running=false;renderForm();const ok=event.code===0;
    setLog(`${currentLog}\n${ok?'Completed successfully':event.signal?'Stopped':`Exited with code ${event.code}`}\n`);
    status(ok?'Complete':event.signal?'Stopped':'Failed',ok?'success':'failed');
    window.vees.state().then(fresh=>{state.settings=fresh.settings;state.workspace=fresh.workspace;updatePython(fresh.python);}).catch(()=>{});
  });
}
start().catch(error=>{document.body.textContent=`Unable to start Otome Translator: ${error.message}`;});
