// Reference implementation of the HeyBox "web" hkey signature, transcribed
// from the site's JavaScript bundle (see the luckylca/xhhBackCrack project).
//
// This file exists only to cross-check the Python port in
// hey2steam/signing.py. Run both and compare the output:
//
//   node tests/reference_hkey.js /game/get_game_list_v3 1726809839 <NONCE>
//   python -c "from hey2steam import signing as s; print(s.hkey('/game/get_game_list_v3', 1726809839, '<NONCE>', 'web'))"
//
// Note: under Git Bash on Windows, MSYS path conversion rewrites the leading
// "/game/..." argument into a Windows path. Prefix the invocation with
// "MSYS_NO_PATHCONV=1" (or run from PowerShell/cmd) to avoid that.

const crypto = require('crypto');

function Vm(e) { return (e & 128) ? (255 & ((e << 1) ^ 27)) : (e << 1); }
function qm(e) { return Vm(e) ^ e; }
function dollar_m(e) { return qm(Vm(e)); }
function Ym(e) { return dollar_m(qm(Vm(e))); }
function Gm(e) { return Ym(e) ^ dollar_m(e) ^ qm(e); }

function Km_full(e_arr) {
  const e = [...e_arr];
  const t = [0, 0, 0, 0];
  t[0] = Gm(e[0]) ^ Ym(e[1]) ^ dollar_m(e[2]) ^ qm(e[3]);
  t[1] = qm(e[0]) ^ Gm(e[1]) ^ Ym(e[2]) ^ dollar_m(e[3]);
  t[2] = dollar_m(e[0]) ^ qm(e[1]) ^ Gm(e[2]) ^ Ym(e[3]);
  t[3] = Ym(e[0]) ^ dollar_m(e[1]) ^ qm(e[2]) ^ Gm(e[3]);
  e[0] = t[0]; e[1] = t[1]; e[2] = t[2]; e[3] = t[3];
  return e;
}

function av(e, t, n) {
  const i = t.slice(0, n);
  let r = '';
  for (const char of e) { r += i[char.charCodeAt(0) % i.length]; }
  return r;
}

function sv(e, t) {
  let r = '';
  for (const char of e) { r += t[char.charCodeAt(0) % t.length]; }
  return r;
}

function get_hkey(url_path, timestamp, nonce) {
  const charset = 'AB45STUVWZEFGJ6CH01D237IXYPQRKLMN89';
  const parts = url_path.split('/').filter((p) => p);
  const normalized_path = '/' + parts.join('/') + '/';
  const comp1 = av(String(timestamp), charset, -2);
  const comp2 = sv(normalized_path, charset);
  const comp3 = sv(nonce, charset);
  const comps = [comp1, comp2, comp3];
  const max_len = Math.max(...comps.map((c) => c.length));
  let interleaved = '';
  for (let k = 0; k < max_len; k++) {
    for (const c of comps) { if (k < c.length) interleaved += c[k]; }
  }
  const i_str = interleaved.slice(0, 20);
  const md5_hash = crypto.createHash('md5').update(i_str).digest('hex');
  const hkey_prefix = av(md5_hash.slice(0, 5), charset, -4);
  const suffix_input = Array.from(md5_hash.slice(-6)).map((c) => c.charCodeAt(0));
  const km_output = Km_full(suffix_input);
  const checksum_str = String(km_output.reduce((a, b) => a + b, 0) % 100).padStart(2, '0');
  return hkey_prefix + checksum_str;
}

const [path, ts, nonce] = process.argv.slice(2);
console.log(get_hkey(path, parseInt(ts, 10), nonce));
