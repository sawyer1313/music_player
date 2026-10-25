// Fernbedienung für den Pi-Musikplayer. Kein Framework, kein Build-Schritt.

const ICONS = {
  play: '<path d="M8 5v14l11-7z"/>',
  pause: '<path d="M6 5h4v14H6zM14 5h4v14h-4z"/>',
  next: '<path d="M6 18l8.5-6L6 6v12zM16 6v12h2V6h-2z"/>',
  prev: '<path d="M6 6h2v12H6zm3.5 6 8.5 6V6z"/>',
  repeat: '<path d="M7 7h10v3l4-4-4-4v3H5v6h2V7zm10 10H7v-3l-4 4 4 4v-3h12v-6h-2v4z"/>',
  shuffle: '<path d="M10.59 9.17 5.41 4 4 5.41l5.17 5.17 1.42-1.41zM14.5 4l2.04 2.04L4 18.59 5.41 20 17.96 7.46 20 9.5V4h-5.5zm.33 9.41-1.41 1.41 3.13 3.13L14.5 20H20v-5.5l-2.04 2.04-3.13-3.13z"/>',
  more: '<path d="M12 8a2 2 0 1 0 0-4 2 2 0 0 0 0 4zm0 2a2 2 0 1 0 0 4 2 2 0 0 0 0-4zm0 6a2 2 0 1 0 0 4 2 2 0 0 0 0-4z"/>',
  volume: '<path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3A4.5 4.5 0 0 0 14 8v8a4.47 4.47 0 0 0 2.5-4zM14 3.23v2.06a7 7 0 0 1 0 13.42v2.06A9 9 0 0 0 14 3.23z"/>',
  disc: '<path d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm0 14.5a4.5 4.5 0 1 1 0-9 4.5 4.5 0 0 1 0 9zm0-5.5a1 1 0 1 0 0 2 1 1 0 0 0 0-2z"/>',
  list: '<path d="M3 13h2v-2H3v2zm0 4h2v-2H3v2zm0-8h2V7H3v2zm4 4h14v-2H7v2zm0 4h14v-2H7v2zM7 7v2h14V7H7z"/>',
  album: '<path d="M20 2H8a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2zm-2.5 5H15v5.5a2.5 2.5 0 1 1-2.5-2.5c.57 0 1.08.19 1.5.51V5h3.5v2zM4 6H2v14a2 2 0 0 0 2 2h14v-2H4V6z"/>',
  search: '<path d="M15.5 14h-.79l-.28-.27A6.47 6.47 0 0 0 16 9.5 6.5 6.5 0 1 0 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/>',
  queue: '<path d="M15 6H3v2h12V6zm0 4H3v2h12v-2zM3 16h8v-2H3v2zM17 6v8.18A3 3 0 1 0 19 17V8h3V6h-5z"/>',
  up: '<path d="M7.41 15.41 12 10.83l4.59 4.58L18 14l-6-6-6 6z"/>',
  down: '<path d="M7.41 8.59 12 13.17l4.59-4.58L18 10l-6 6-6-6z"/>',
  close: '<path d="M19 6.41 17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>',
  playnext: '<path d="M3 10h11v2H3zm0-4h11v2H3zm0 8h7v2H3zm13-1v8l6-4z"/>',
  addend: '<path d="M14 10H3v2h11v-2zm0-4H3v2h11V6zm4 8v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zM3 16h7v-2H3v2z"/>',
  person: '<path d="M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>',
  power: '<path d="M13 3h-2v10h2V3zm4.83 2.17-1.42 1.42A6.92 6.92 0 0 1 19 12a7 7 0 1 1-11.42-5.42L6.17 5.17A8.93 8.93 0 0 0 3 12a9 9 0 0 0 18 0c0-2.74-1.23-5.18-3.17-6.83z"/>',
  trash: '<path d="M6 19a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/>',
};
const icon = name => `<svg viewBox="0 0 24 24" aria-hidden="true">${ICONS[name]}</svg>`;

const PLACEHOLDER = 'data:image/svg+xml,' + encodeURIComponent(
  '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><rect width="24" height="24" fill="#26262c"/>' +
  '<path fill="#55555f" d="M12 6v7.55A3.5 3.5 0 1 0 14 16.5V9h3V6h-5z" transform="translate(-1 -0.5)"/></svg>');

const $ = sel => document.querySelector(sel);
const view = $('#view');
const esc = s => String(s ?? '').replace(/[&<>"']/g, c =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
const cover = (id, size = 300) => id ? `/api/cover/${encodeURIComponent(id)}?size=${size}` : PLACEHOLDER;

function fmt(sec) {
  sec = Math.max(0, Math.floor(sec || 0));
  const h = Math.floor(sec / 3600), m = Math.floor(sec / 60) % 60, s = sec % 60;
  return (h ? `${h}:${String(m).padStart(2, '0')}` : m) + ':' + String(s).padStart(2, '0');
}
function fmtLong(sec) {
  const min = Math.round((sec || 0) / 60);
  return min >= 60 ? `${Math.floor(min / 60)} Std. ${min % 60} Min.` : `${min} Min.`;
}
const titles = n => `${n} Titel`;

// Kaputte Cover durch Platzhalter ersetzen
document.addEventListener('error', e => {
  const img = e.target;
  if (img.tagName === 'IMG' && !img.dataset.fallback) { img.dataset.fallback = '1'; img.src = PLACEHOLDER; }
}, true);

// ---------- API ----------

async function api(path, body) {
  const opts = body === undefined ? {} :
    { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) };
  const r = await fetch('/api' + path, opts);
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.error || `Fehler ${r.status}`);
  return data;
}
const post = (path, body = {}) => api(path, body).catch(e => { toast(e.message); throw e; });
const fire = (path, body) => post(path, body).catch(() => {});

let toastTimer;
function toast(msg) {
  const t = $('#toast');
  t.textContent = msg;
  t.classList.remove('hidden');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.add('hidden'), 2200);
}

// ---------- Live-Zustand per WebSocket ----------

let state = null, stateAt = 0;
let ws = null, retry = 0, retryTimer = null;

function connect() {
  clearTimeout(retryTimer);
  if (ws && ws.readyState <= 1) return;
  const sock = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/api/ws`);
  ws = sock;
  sock.onopen = () => { retry = 0; $('#offline').classList.add('hidden'); };
  sock.onmessage = e => {
    const msg = JSON.parse(e.data);
    if (msg.type === 'state') onState(msg.state);
  };
  sock.onclose = () => {
    if (ws !== sock) return;
    $('#offline').classList.remove('hidden');
    retryTimer = setTimeout(connect, Math.min(1000 * 2 ** retry++, 8000));
  };
}
setInterval(() => ws?.readyState === 1 && ws.send('ping'), 20000);
document.addEventListener('visibilitychange', () => {
  if (document.hidden) return;
  connect();
  api('/state').then(onState).catch(() => {});
});

function position() {
  if (!state) return 0;
  let p = state.position;
  if (state.status === 'playing') p += (performance.now() - stateAt) / 1000;
  return state.duration ? Math.min(p, state.duration) : p;
}

function onState(s) {
  const prev = state;
  state = s;
  stateAt = performance.now();
  if (s.error !== prev?.error || s.mpv_connected !== prev?.mpv_connected) showBanner(s);
  renderMini();
  if (route.tab === 'now') updateNow(prev?.current?.id !== s.current?.id);
  if (route.tab === 'queue' && prev && prev.queue_version !== s.queue_version) refreshQueue();
  markCurrent();
}

let bannerTimer;
function showBanner(s) {
  const err = $('#error');
  clearTimeout(bannerTimer);
  err.textContent = !s.mpv_connected ? 'Audio-Player (mpv) läuft nicht' : s.error || '';
  err.classList.toggle('hidden', !err.textContent);
  if (s.mpv_connected && s.error) bannerTimer = setTimeout(() => err.classList.add('hidden'), 8000);
}

function markCurrent() {
  const id = state?.current?.id;
  document.querySelectorAll('.row[data-song]').forEach(r => {
    const isCur = route.tab === 'queue' ? Number(r.dataset.i) === state?.index : r.dataset.song === id;
    r.classList.toggle('current', isCur);
  });
}

// ---------- Mini-Player ----------

$('#mini-next').innerHTML = icon('next');
$('#mini-toggle').onclick = () => fire('/player/toggle');
$('#mini-next').onclick = () => fire('/player/next');
$('#mini-open').onclick = () => { location.hash = '#/now'; };

function renderMini() {
  const show = state?.current && route.tab !== 'now';
  $('#mini').classList.toggle('hidden', !show);
  document.body.style.setProperty('--mini-h', show ? '60px' : '0px');
  if (!state?.current) return;
  const c = state.current;
  const img = $('#mini-cover'), src = cover(c.coverArt, 96);
  if (img.dataset.src !== src) { img.dataset.src = src; delete img.dataset.fallback; img.src = src; }
  $('#mini-title').textContent = c.title;
  $('#mini-artist').textContent = c.artist;
  $('#mini-toggle').innerHTML = icon(state.status === 'playing' ? 'pause' : 'play');
}

setInterval(() => {
  if (!state?.current) return;
  const pct = state.duration ? (position() / state.duration) * 100 : 0;
  $('#mini-progress').style.width = pct + '%';
  if (route.tab === 'now') updateProgress();
}, 500);

// ---------- Aktionsmenü ----------

function sheet(title, actions) {
  $('#sheet-title').textContent = title;
  const box = $('#sheet-actions');
  box.innerHTML = '';
  for (const a of actions) {
    const b = document.createElement('button');
    b.innerHTML = `${icon(a.icon)}<span>${esc(a.label)}</span>`;
    b.onclick = () => { closeSheet(); a.run(); };
    box.appendChild(b);
  }
  $('#sheet').classList.remove('hidden');
}
function closeSheet() { $('#sheet').classList.add('hidden'); }
$('#sheet').onclick = e => { if (e.target.id === 'sheet') closeSheet(); };
$('#sheet-cancel').onclick = closeSheet;

async function addSource(src, mode) {
  const res = await post('/queue/add', { ...src, mode }).catch(() => null);
  if (res && mode !== 'now') toast(mode === 'next' ? 'Wird als Nächstes gespielt' : `${titles(res.count)} angehängt`);
}

function songSheet(song) {
  const src = { type: 'song', id: song.id };
  const actions = [
    { icon: 'play', label: 'Jetzt spielen', run: () => addSource(src, 'now') },
    { icon: 'playnext', label: 'Als Nächstes spielen', run: () => addSource(src, 'next') },
    { icon: 'addend', label: 'Ans Ende der Warteschlange', run: () => addSource(src, 'end') },
  ];
  if (song.albumId) actions.push({ icon: 'album', label: 'Zum Album', run: () => { location.hash = `#/album/${song.albumId}`; } });
  if (song.artistId) actions.push({ icon: 'person', label: 'Zum Künstler', run: () => { location.hash = `#/artist/${song.artistId}`; } });
  sheet(`${song.title} – ${song.artist}`, actions);
}

function collectionSheet(name, src) {
  sheet(name, [
    { icon: 'playnext', label: 'Als Nächstes spielen', run: () => addSource(src, 'next') },
    { icon: 'addend', label: 'Ans Ende der Warteschlange', run: () => addSource(src, 'end') },
  ]);
}

// ---------- Bausteine ----------

function songRows(songs, { thumbs = true, numbers = false } = {}) {
  return songs.map((s, i) => `
    <li class="row" data-i="${i}" data-song="${esc(s.id)}">
      ${numbers ? `<span class="num">${esc(s.track ?? i + 1)}</span>` :
        thumbs ? `<img class="thumb" loading="lazy" src="${cover(s.coverArt, 96)}" alt="">` : ''}
      <div class="row-main">
        <div class="row-title ellipsis">${esc(s.title)}</div>
        <div class="row-sub ellipsis">${esc(s.artist)}${thumbs && s.album ? ' · ' + esc(s.album) : ''}</div>
      </div>
      <span class="dur">${fmt(s.duration)}</span>
      <button class="icon-btn small more-btn" aria-label="Mehr">${icon('more')}</button>
    </li>`).join('');
}

// Klick auf Titel: ganze Quelle ab diesem Titel spielen (oder einzeln, wenn src fehlt)
function bindSongList(ul, songs, src) {
  ul.addEventListener('click', e => {
    const row = e.target.closest('.row');
    if (!row) return;
    const song = songs[Number(row.dataset.i)];
    if (e.target.closest('.more-btn')) return songSheet(song);
    if (src) fire('/queue/play', { ...src, index: Number(row.dataset.i) });
    else addSource({ type: 'song', id: song.id }, 'now');
  });
}

function albumGrid(albums) {
  return albums.map(a => `
    <a class="card" href="#/album/${encodeURIComponent(a.id)}">
      <img loading="lazy" src="${cover(a.coverArt, 300)}" alt="">
      <div class="t ellipsis">${esc(a.name)}</div>
      <div class="s ellipsis">${esc(a.artist)}${a.year ? ' · ' + a.year : ''}</div>
    </a>`).join('');
}

function detailButtons(src, name) {
  const wrap = document.createElement('div');
  wrap.className = 'btn-row';
  wrap.innerHTML = `
    <button class="btn primary" data-a="play">${icon('play')}Abspielen</button>
    <button class="btn" data-a="shuffle">${icon('shuffle')}Zufällig</button>
    <button class="icon-btn" data-a="more" aria-label="Mehr">${icon('more')}</button>`;
  wrap.onclick = e => {
    const a = e.target.closest('[data-a]')?.dataset.a;
    if (a === 'play') fire('/queue/play', { ...src, index: 0 });
    if (a === 'shuffle') fire('/queue/play', { ...src, shuffle: true });
    if (a === 'more') collectionSheet(name, src);
  };
  return wrap;
}

const spinner = () => { view.innerHTML = '<div class="spinner"></div>'; };
const showError = e => { view.innerHTML = `<div class="empty">${esc(e.message)}</div>`; };

// ---------- Ansicht: Läuft gerade ----------

let seeking = false, volTimer = null, volDragging = false;

function viewNow() {
  view.innerHTML = `
    <div class="now" id="np">
      <img class="now-cover" id="np-cover" alt="">
      <div class="now-title ellipsis" id="np-title"></div>
      <div class="now-artist ellipsis" id="np-artist"></div>
      <div class="progress">
        <input type="range" id="np-seek" min="0" max="100" step="1" value="0" aria-label="Position">
        <div class="times"><span id="np-pos">0:00</span><span id="np-dur">0:00</span></div>
      </div>
      <div class="controls">
        <button class="icon-btn" id="np-shuffle" aria-label="Warteschlange mischen">${icon('shuffle')}</button>
        <button class="icon-btn mid" id="np-prev" aria-label="Zurück">${icon('prev')}</button>
        <button class="icon-btn big" id="np-toggle" aria-label="Play/Pause"></button>
        <button class="icon-btn mid" id="np-next" aria-label="Weiter">${icon('next')}</button>
        <button class="icon-btn" id="np-repeat" aria-label="Wiederholen">${icon('repeat')}</button>
      </div>
      <div class="volume">${icon('volume')}<input type="range" id="np-vol" min="0" max="100" aria-label="Lautstärke"></div>
    </div>
    <div class="empty hidden" id="np-empty">
      <div>Die Warteschlange ist leer.</div>
      <button class="btn primary" id="np-random">${icon('shuffle')}Zufallsmix starten</button>
    </div>`;

  $('#np-toggle').onclick = () => fire('/player/toggle');
  $('#np-prev').onclick = () => fire('/player/prev');
  $('#np-next').onclick = () => fire('/player/next');
  $('#np-shuffle').onclick = () => post('/queue/shuffle').then(() => toast('Warteschlange gemischt')).catch(() => {});
  $('#np-random').onclick = () => fire('/queue/play', { type: 'random', size: 50 });
  $('#np-repeat').onclick = () => {
    const modes = ['off', 'all', 'one'];
    fire('/player/repeat', { mode: modes[(modes.indexOf(state?.repeat) + 1) % 3] });
  };

  const seek = $('#np-seek');
  seek.oninput = () => {
    seeking = true;
    $('#np-pos').textContent = fmt(seek.value);
    paintRange(seek);
  };
  seek.onchange = async () => {
    await post('/player/seek', { position: Number(seek.value) }).catch(() => {});
    seeking = false;
  };

  const vol = $('#np-vol');
  vol.onpointerdown = () => { volDragging = true; };
  vol.oninput = () => {
    paintRange(vol);
    clearTimeout(volTimer);
    volTimer = setTimeout(() => fire('/player/volume', { volume: Number(vol.value) }), 120);
  };
  vol.onchange = () => {
    clearTimeout(volTimer);
    fire('/player/volume', { volume: Number(vol.value) });
    setTimeout(() => { volDragging = false; }, 400);
  };

  if (state) updateNow(true);
}

function paintRange(input) {
  const max = Number(input.max) || 1;
  input.style.setProperty('--p', (Number(input.value) / max) * 100 + '%');
}

function updateNow(trackChanged) {
  if (!$('#np')) return;
  const c = state?.current;
  $('#np').classList.toggle('hidden', !c);
  $('#np-empty').classList.toggle('hidden', !!c);
  if (!c) return;
  if (trackChanged || !$('#np-cover').src) {
    const img = $('#np-cover');
    delete img.dataset.fallback;
    img.src = cover(c.coverArt, 600);
    $('#np-title').innerHTML = c.albumId
      ? `<a href="#/album/${encodeURIComponent(c.albumId)}">${esc(c.title)}</a>` : esc(c.title);
    $('#np-artist').innerHTML = c.artistId
      ? `<a href="#/artist/${encodeURIComponent(c.artistId)}">${esc(c.artist)}</a>` : esc(c.artist);
  }
  $('#np-toggle').innerHTML = icon(state.status === 'playing' ? 'pause' : 'play');
  const rep = $('#np-repeat');
  rep.classList.toggle('active', state.repeat !== 'off');
  rep.classList.toggle('repeat-one', state.repeat === 'one');
  const vol = $('#np-vol');
  if (!volDragging) { vol.value = state.volume; paintRange(vol); }
  updateProgress();
}

function updateProgress() {
  const seek = $('#np-seek');
  if (!seek || seeking || !state?.current) return;
  seek.max = Math.max(1, Math.round(state.duration));
  seek.value = Math.round(position());
  paintRange(seek);
  $('#np-pos').textContent = fmt(position());
  $('#np-dur').textContent = fmt(state.duration);
}

// ---------- Ansicht: Playlists ----------

async function viewPlaylists(_, alive) {
  spinner();
  const lists = await api('/library/playlists');
  if (!alive()) return;
  view.innerHTML = `<h1>Playlists</h1>` + (lists.length ? `<ul class="list">${lists.map(p => `
    <li><a class="row" href="#/playlist/${encodeURIComponent(p.id)}">
      <img class="thumb" loading="lazy" src="${cover(p.coverArt, 96)}" alt="">
      <div class="row-main">
        <div class="row-title ellipsis">${esc(p.name)}</div>
        <div class="row-sub">${titles(p.songCount)} · ${fmtLong(p.duration)}</div>
      </div></a></li>`).join('')}</ul>` : '<div class="empty">Keine Playlists in Navidrome gefunden.</div>');
}

async function viewPlaylist([id], alive) {
  spinner();
  const pl = await api(`/library/playlist/${encodeURIComponent(id)}`);
  if (!alive()) return;
  renderCollection({
    title: pl.name, coverArt: pl.coverArt,
    sub: `${titles(pl.songs.length)} · ${fmtLong(pl.duration)}`,
    src: { type: 'playlist', id }, songs: pl.songs, numbers: false,
  });
}

function renderCollection({ title, sub, coverArt, src, songs, numbers, roundCover, extra }) {
  view.innerHTML = `
    <div class="detail-head">
      <img src="${cover(coverArt, 300)}" alt="" style="${roundCover ? 'border-radius:50%' : ''}">
      <div><h1>${esc(title)}</h1><div class="dim">${sub}</div></div>
    </div>`;
  view.appendChild(detailButtons(src, title));
  if (extra) view.insertAdjacentHTML('beforeend', extra);
  if (songs) {
    const ul = document.createElement('ul');
    ul.className = 'list';
    ul.innerHTML = songRows(songs, { numbers, thumbs: !numbers });
    bindSongList(ul, songs, src);
    view.appendChild(ul);
  }
  markCurrent();
}

// ---------- Ansicht: Bibliothek ----------

const LIB_KINDS = [
  ['newest', 'Neu'], ['random', 'Zufall'], ['recent', 'Zuletzt gespielt'],
  ['frequent', 'Oft gespielt'], ['alphabeticalByName', 'A–Z'], ['artists', 'Künstler'],
];

async function viewLibrary([kind = 'newest'], alive) {
  const chips = `<h1>Bibliothek</h1><div class="chips">${LIB_KINDS.map(([k, label]) =>
    `<a class="chip ${k === kind ? 'active' : ''}" href="#/library/${k}">${label}</a>`).join('')}</div>`;
  view.innerHTML = chips + '<div class="spinner"></div>';

  if (kind === 'artists') {
    const artists = await api('/library/artists');
    if (!alive()) return;
    let html = '', letter = '';
    for (const a of artists) {
      const l = (a.name[0] || '#').toUpperCase();
      if (l !== letter) { letter = l; html += `<li class="letter">${esc(l)}</li>`; }
      html += `<li><a class="row" href="#/artist/${encodeURIComponent(a.id)}">
        <img class="thumb round" loading="lazy" src="${cover(a.coverArt, 96)}" alt="">
        <div class="row-main"><div class="row-title ellipsis">${esc(a.name)}</div>
        <div class="row-sub">${a.albumCount} ${a.albumCount === 1 ? 'Album' : 'Alben'}</div></div></a></li>`;
    }
    view.innerHTML = chips + `<ul class="list">${html}</ul>`;
    return;
  }

  let offset = 0;
  const grid = document.createElement('div');
  grid.className = 'grid';
  const more = document.createElement('button');
  more.className = 'btn more';
  more.textContent = 'Mehr laden';
  const load = async () => {
    more.disabled = true;
    const albums = await api(`/library/albums?type=${kind}&offset=${offset}`);
    if (!alive()) return;
    offset += albums.length;
    grid.insertAdjacentHTML('beforeend', albumGrid(albums));
    more.classList.toggle('hidden', albums.length < 40);
    more.disabled = false;
  };
  more.onclick = () => load().catch(e => toast(e.message));
  await load();
  if (!alive()) return;
  view.innerHTML = chips;
  view.append(grid, more);
}

async function viewArtist([id], alive) {
  spinner();
  const a = await api(`/library/artist/${encodeURIComponent(id)}`);
  if (!alive()) return;
  renderCollection({
    title: a.name, coverArt: a.coverArt, roundCover: true,
    sub: `${a.albums.length} ${a.albums.length === 1 ? 'Album' : 'Alben'}`,
    src: { type: 'artist', id },
    extra: `<h2>Alben</h2><div class="grid">${albumGrid(a.albums)}</div>`,
  });
}

async function viewAlbum([id], alive) {
  spinner();
  const al = await api(`/library/album/${encodeURIComponent(id)}`);
  if (!alive()) return;
  const artist = al.artistId
    ? `<a href="#/artist/${encodeURIComponent(al.artistId)}"><u>${esc(al.artist)}</u></a>` : esc(al.artist);
  renderCollection({
    title: al.name, coverArt: al.coverArt,
    sub: `${artist}<br>${al.year ? al.year + ' · ' : ''}${titles(al.songs.length)} · ${fmtLong(al.duration)}`,
    src: { type: 'album', id }, songs: al.songs, numbers: true,
  });
}

// ---------- Ansicht: Suche ----------

let lastQuery = '';

function viewSearch(_, alive) {
  view.innerHTML = `<h1>Suche</h1>
    <input class="search-box" id="q" type="search" placeholder="Künstler, Alben, Titel …" autocomplete="off" enterkeyhint="search">
    <div id="results"></div>`;
  const input = $('#q');
  input.value = lastQuery;
  let timer, seq = 0;
  const run = async () => {
    const q = input.value.trim();
    lastQuery = q;
    const my = ++seq;
    const box = $('#results');
    if (!q) { box.innerHTML = ''; return; }
    box.innerHTML = '<div class="spinner"></div>';
    try {
      const r = await api(`/library/search?q=${encodeURIComponent(q)}`);
      if (my !== seq || !alive()) return;
      renderResults(box, r);
    } catch (e) { if (my === seq) box.innerHTML = `<div class="empty">${esc(e.message)}</div>`; }
  };
  input.oninput = () => { clearTimeout(timer); timer = setTimeout(run, 300); };
  input.onkeydown = e => { if (e.key === 'Enter') { clearTimeout(timer); input.blur(); run(); } };
  if (lastQuery) run(); else input.focus();
}

function renderResults(box, r) {
  if (!r.artists.length && !r.albums.length && !r.songs.length) {
    box.innerHTML = '<div class="empty">Nichts gefunden.</div>';
    return;
  }
  box.innerHTML = '';
  if (r.songs.length) {
    box.insertAdjacentHTML('beforeend', '<h2>Titel</h2>');
    const ul = document.createElement('ul');
    ul.className = 'list';
    ul.innerHTML = songRows(r.songs);
    bindSongList(ul, r.songs, null);
    box.appendChild(ul);
  }
  if (r.artists.length) {
    box.insertAdjacentHTML('beforeend', `<h2>Künstler</h2><ul class="list">${r.artists.map(a => `
      <li><a class="row" href="#/artist/${encodeURIComponent(a.id)}">
        <img class="thumb round" loading="lazy" src="${cover(a.coverArt, 96)}" alt="">
        <div class="row-main"><div class="row-title ellipsis">${esc(a.name)}</div></div></a></li>`).join('')}</ul>`);
  }
  if (r.albums.length) {
    box.insertAdjacentHTML('beforeend', `<h2>Alben</h2><div class="grid">${albumGrid(r.albums)}</div>`);
  }
  markCurrent();
}

// ---------- Ansicht: Warteschlange ----------

let queueData = { queue: [] };

async function viewQueue(_, alive) {
  spinner();
  queueData = await api('/queue');
  if (!alive()) return;
  view.innerHTML = `<h1>Warteschlange</h1>
    <div class="btn-row">
      <button class="btn" id="q-shuffle">${icon('shuffle')}Mischen</button>
      <button class="btn" id="q-clear">${icon('trash')}Leeren</button>
    </div>
    <div id="q-count" class="dim"></div>
    <ul class="list" id="q-list"></ul>`;
  $('#q-shuffle').onclick = () => fire('/queue/shuffle');
  $('#q-clear').onclick = () => { if (confirm('Warteschlange wirklich leeren?')) fire('/queue/clear'); };
  $('#q-list').addEventListener('click', e => {
    const row = e.target.closest('.row');
    if (!row) return;
    const i = Number(row.dataset.i);
    if (e.target.closest('.more-btn')) return queueSheet(i);
    fire('/queue/jump', { index: i });
  });
  renderQueue();
  $('#q-list .current')?.scrollIntoView({ block: 'center' });
}

async function refreshQueue() {
  const data = await api('/queue').catch(() => null);
  if (!data || route.tab !== 'queue') return;
  queueData = data;
  renderQueue();
}

function renderQueue() {
  const ul = $('#q-list');
  if (!ul) return;
  const q = queueData.queue;
  const total = q.reduce((t, s) => t + (s.duration || 0), 0);
  $('#q-count').textContent = q.length ? `${titles(q.length)} · ${fmtLong(total)}` : '';
  ul.innerHTML = q.length ? songRows(q) :
    '<div class="empty">Leer. Wähle eine Playlist oder ein Album aus.</div>';
  markCurrent();
}

function queueSheet(i) {
  const s = queueData.queue[i];
  if (!s) return;
  const move = to => fire('/queue/move', { from: i, to });
  const cur = state?.index ?? -1;
  const actions = [{ icon: 'play', label: 'Jetzt spielen', run: () => fire('/queue/jump', { index: i }) }];
  if (i !== cur && i !== cur + 1) {
    actions.push({ icon: 'playnext', label: 'Als Nächstes spielen', run: () => move(i < cur ? cur : cur + 1) });
  }
  if (i > 0) actions.push({ icon: 'up', label: 'Nach oben', run: () => move(i - 1) });
  if (i < queueData.queue.length - 1) actions.push({ icon: 'down', label: 'Nach unten', run: () => move(i + 1) });
  actions.push({ icon: 'close', label: 'Entfernen', run: () => fire('/queue/remove', { index: i }) });
  if (s.albumId) actions.push({ icon: 'album', label: 'Zum Album', run: () => { location.hash = `#/album/${s.albumId}`; } });
  sheet(`${s.title} – ${s.artist}`, actions);
}

// ---------- Ausschalten ----------

async function powerOff() {
  try {
    await api('/system/poweroff', {});
  } catch (e) {
    // Bricht die Verbindung ab, weil der Pi schon herunterfährt, ist das kein Fehler
    if (!(e instanceof TypeError)) return toast(e.message);
  }
  $('#offline').textContent = 'Pi ist ausgeschaltet. Zum Einschalten Strom kurz trennen.';
  toast('Pi fährt herunter …');
}
$('#tab-power').onclick = () => sheet('Pi ausschalten? Die Musik stoppt.', [
  { icon: 'power', label: 'Ausschalten', run: powerOff },
]);

// ---------- Router ----------

const ROUTES = [
  [/^#\/now$/, viewNow, 'now'],
  [/^#\/playlists$/, viewPlaylists, 'playlists'],
  [/^#\/playlist\/(.+)$/, viewPlaylist, 'playlists'],
  [/^#\/library(?:\/(\w+))?$/, viewLibrary, 'library'],
  [/^#\/artist\/(.+)$/, viewArtist, 'library'],
  [/^#\/album\/(.+)$/, viewAlbum, 'library'],
  [/^#\/search$/, viewSearch, 'search'],
  [/^#\/queue$/, viewQueue, 'queue'],
];
let route = { tab: null };
let renderId = 0;

async function router() {
  closeSheet();
  const hash = location.hash || '#/now';
  const match = ROUTES.map(([re, fn, tab]) => [hash.match(re), fn, tab]).find(([m]) => m);
  if (!match) { location.hash = '#/now'; return; }
  const [m, fn, tab] = match;
  const id = ++renderId;
  route = { tab };
  document.querySelectorAll('.tabs a').forEach(a => a.classList.toggle('active', a.dataset.tab === tab));
  renderMini();
  window.scrollTo(0, 0);
  try {
    await fn(m.slice(1).map(x => x && decodeURIComponent(x)), () => id === renderId);
  } catch (e) {
    if (id === renderId) showError(e);
  }
}

document.querySelectorAll('[data-icon]').forEach(el => { el.innerHTML = icon(el.dataset.icon); });
window.addEventListener('hashchange', router);
router();
connect();
