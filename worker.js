/**
 * YOUTUBE VIDEO DOWNLOADER Premium Cloud 5.1 Security Edition
 * Cloudflare Workers + D1. Compatible with 5.0 Windows client and Admin Center.
 * Secrets: ADMIN_TOKEN (required, high entropy), RATE_LIMIT_SALT (recommended).
 * D1 binding: DB. Run sql/01_security_5_1.sql before deploying.
 * No secrets in code; no browser CORS policy is granted.
 */
const encoder = new TextEncoder();
const LIMITS = Object.freeze({
  '/activate': {max: 12, seconds: 600},
  '/validate': {max: 300, seconds: 600},
  'admin': {max: 40, seconds: 600},
});
const JSON_HEADERS = {
  'Content-Type': 'application/json; charset=utf-8',
  'Cache-Control': 'no-store',
  'X-Content-Type-Options': 'nosniff',
  'Referrer-Policy': 'no-referrer',
};
const json = (data, status = 200, extraHeaders = {}) =>
  new Response(JSON.stringify(data), {status, headers: {...JSON_HEADERS, ...extraHeaders}});
const digest = async value => Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', encoder.encode(value))))
  .map(byte => byte.toString(16).padStart(2, '0')).join('');
const random = (n = 24) => Array.from(crypto.getRandomValues(new Uint8Array(n)))
  .map(byte => byte.toString(16).padStart(2, '0')).join('');
const nowIso = () => new Date().toISOString();
const active = (row, now = nowIso()) => Boolean(row && !row.revoked && (!row.expires_at || row.expires_at > now));
const UUID = /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i;
const CODE = /^YVD5-[a-f0-9]{40}$/;
const DEVICE = /^[a-f0-9]{32}$/;
const TOKEN = /^yvd5t-[a-f0-9]{64}$/;
const ADMIN_PATHS = new Set(['/admin/issue', '/admin/list', '/admin/stats', '/admin/revoke', '/admin/extend', '/admin/token-wallet', '/admin/token-grant']);
const safeEqual = (a, b) => {
  const left = encoder.encode(a), right = encoder.encode(b);
  let diff = left.length ^ right.length;
  for (let i = 0; i < Math.max(left.length, right.length); i++) diff |= (left[i] || 0) ^ (right[i] || 0);
  return diff === 0;
};

async function readJson(request) {
  const type = request.headers.get('content-type') || '';
  if (!/^application\/json\s*(;|$)/i.test(type)) return {error: json({error: 'Content-Type must be application/json'}, 415)};
  const length = Number(request.headers.get('content-length') || 0);
  if (length > 16384) return {error: json({error: 'Request too large'}, 413)};
  // Stream-limit real bytes; Content-Length is not trusted.
  const reader = request.body?.getReader();
  if (!reader) return {error: json({error: 'Invalid JSON'}, 400)};
  const chunks = [];
  let bytes = 0;
  try {
    for (;;) {
      const {value, done} = await reader.read();
      if (done) break;
      bytes += value.byteLength;
      if (bytes > 16384) {await reader.cancel(); return {error: json({error: 'Request too large'}, 413)};}
      chunks.push(value);
    }
    const all = new Uint8Array(bytes);
    let offset = 0;
    for (const chunk of chunks) {all.set(chunk, offset); offset += chunk.byteLength;}
    const value = JSON.parse(new TextDecoder('utf-8', {fatal: true}).decode(all));
    if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('Not an object');
    return {value};
  } catch (_) {return {error: json({error: 'Invalid JSON'}, 400)};}
}

async function ipFingerprint(request, env) {
  // Cloudflare supplies CF-Connecting-IP at edge; no raw IP is stored in D1.
  const ip = request.headers.get('CF-Connecting-IP') || 'unknown';
  const salt = env.RATE_LIMIT_SALT || env.ADMIN_TOKEN || '';
  return digest(`${salt}:${ip}`);
}

async function rateLimit(env, scope, fingerprint, spec) {
  const now = Math.floor(Date.now() / 1000);
  const windowStart = Math.floor(now / spec.seconds) * spec.seconds;
  const key = await digest(`${scope}:${fingerprint}`);
  // Atomic increment in D1; existing key resets when a new time window begins.
  await env.DB.prepare(`INSERT INTO security_rate_limits (bucket_key, window_start, count)
    VALUES (?, ?, 1)
    ON CONFLICT(bucket_key) DO UPDATE SET
      count = CASE WHEN window_start = excluded.window_start THEN count + 1 ELSE 1 END,
      window_start = excluded.window_start`)
    .bind(key, windowStart).run();
  const row = await env.DB.prepare('SELECT count FROM security_rate_limits WHERE bucket_key = ?').bind(key).first();
  if (!row || row.count > spec.max) {
    const seconds = Math.max(1, (windowStart + spec.seconds) - now);
    return json({error: 'Too many requests'}, 429, {'Retry-After': String(seconds)});
  }
  return null;
}

async function audit(db, event, licenseId, requesterFingerprint, detail = '') {
  await db.prepare('INSERT INTO admin_audit (id, event, license_id, actor_fingerprint, detail, created_at) VALUES (?, ?, ?, ?, ?, ?)')
    .bind(crypto.randomUUID(), event, licenseId || null, requesterFingerprint, detail, nowIso()).run();
}

async function handleAdmin(path, body, env, fingerprint) {
  if (path === '/admin/issue') {
    const owner = typeof body.owner === 'string' ? body.owner.trim() : '';
    const minutes = body.minutes;
    if (!owner || owner.length > 100 || !(minutes === null || (Number.isSafeInteger(minutes) && minutes >= 1 && minutes <= 52560000)))
      return json({error: 'Invalid owner or duration'}, 400);
    const id = crypto.randomUUID(), code = 'YVD5-' + random(20);
    const expires = minutes === null ? null : new Date(Date.now() + minutes * 60000).toISOString();
    await env.DB.batch([
      env.DB.prepare('INSERT INTO licenses (id, code_hash, owner, created_at, expires_at) VALUES (?, ?, ?, ?, ?)')
        .bind(id, await digest(code), owner, nowIso(), expires),
      env.DB.prepare('INSERT INTO admin_audit (id, event, license_id, actor_fingerprint, detail, created_at) VALUES (?, ?, ?, ?, ?, ?)')
        .bind(crypto.randomUUID(), 'issue', id, fingerprint, minutes === null ? 'unlimited' : `${minutes} minutes`, nowIso()),
    ]);
    return json({id, code, owner, expires_at: expires});
  }
  if (path === '/admin/list') {
    const rows = await env.DB.prepare('SELECT id, owner, created_at, expires_at, revoked, device IS NOT NULL AS activated FROM licenses ORDER BY created_at DESC LIMIT 200').all();
    return json({licenses: rows.results});
  }
  if (path === '/admin/stats') {
    const row = await env.DB.prepare('SELECT COUNT(*) AS total, SUM(CASE WHEN revoked=1 THEN 1 ELSE 0 END) AS revoked, SUM(CASE WHEN device IS NOT NULL THEN 1 ELSE 0 END) AS activated FROM licenses').first();
    return json({stats: row});
  }
  if (path === '/admin/revoke') {
    const id = String(body.id || '');
    if (!UUID.test(id)) return json({error: 'Invalid id'}, 400);
    const row = await env.DB.prepare('SELECT id, revoked FROM licenses WHERE id = ?').bind(id).first();
    if (!row) return json({ok: false});
    if (!row.revoked) {
      await env.DB.batch([
        env.DB.prepare('UPDATE licenses SET revoked = 1 WHERE id = ? AND revoked = 0').bind(id),
        env.DB.prepare('INSERT INTO admin_audit (id, event, license_id, actor_fingerprint, detail, created_at) VALUES (?, ?, ?, ?, ?, ?)')
          .bind(crypto.randomUUID(), 'revoke', id, fingerprint, '', nowIso()),
      ]);
    }
    return json({ok: true});
  }
  if (path === '/admin/extend') {
    const id = String(body.id || ''), minutes = body.minutes;
    if (!UUID.test(id) || !Number.isSafeInteger(minutes) || minutes < 1 || minutes > 52560000)
      return json({error: 'Invalid input'}, 400);
    const row = await env.DB.prepare('SELECT expires_at FROM licenses WHERE id = ? AND revoked = 0').bind(id).first();
    if (!row) return json({error: 'Not found'}, 404);
    if (row.expires_at === null) return json({ok: true, expires_at: null});
    const expires = new Date(Math.max(Date.now(), Date.parse(row.expires_at)) + minutes * 60000).toISOString();
    // Guard against concurrent extensions overwriting another admin's change.
    const update = await env.DB.prepare('UPDATE licenses SET expires_at = ? WHERE id = ? AND revoked = 0 AND expires_at = ?')
      .bind(expires, id, row.expires_at).run();
    if (!update.meta?.changes) return json({error: 'License changed; retry'}, 409);
    await audit(env.DB, 'extend', id, fingerprint, `${minutes} minutes`);
    return json({ok: true, expires_at: expires});
  }
  if (path === '/admin/token-wallet') {
    const id = typeof body.wallet_id === 'string' ? body.wallet_id.trim() : '';
    if (!UUID.test(id)) return json({error: 'Nieprawidłowy identyfikator portfela'}, 400);
    const found=await env.DB.prepare('SELECT id, created_at FROM token_wallets WHERE id=?').bind(id).first();
    if(!found)return json({error:'Nie znaleziono portfela'},404);
    const grants=await env.DB.prepare('SELECT COALESCE(SUM(amount),0) AS total FROM token_admin_grants WHERE wallet_id=?').bind(id).first();
    const rewards=await env.DB.prepare('SELECT COALESCE(SUM(delta),0) AS total FROM token_ledger WHERE wallet_id=?').bind(id).first();
    return json({wallet_id:id,created_at:found.created_at,balance:Number(grants?.total||0)+Number(rewards?.total||0)});
  }
  if (path === '/admin/token-grant') {
    const id=typeof body.wallet_id==='string'?body.wallet_id.trim():'';
    const amount=body.amount;
    const reason=typeof body.reason==='string'?body.reason.trim():'';
    const requestId=typeof body.request_id==='string'?body.request_id:'';
    if (!UUID.test(id) || !UUID.test(requestId) || !Number.isSafeInteger(amount) || amount<1 || amount>10000 || !reason || reason.length>180)
      return json({error:'Podaj ID portfela, 1–10000 tokenów, powód i UUID operacji'},400);
    const existing=await env.DB.prepare('SELECT wallet_id,amount FROM token_admin_grants WHERE id=?').bind(requestId).first();
    if(existing) return existing.wallet_id===id && Number(existing.amount)===amount
      ? json({ok:true,already_processed:true,wallet_id:id,balance:await balanceOf(env,id)})
      : json({error:'Identyfikator operacji został już użyty'},409);
    const found=await env.DB.prepare('SELECT id FROM token_wallets WHERE id=?').bind(id).first();
    if(!found)return json({error:'Nie znaleziono portfela'},404);
    const stamp=nowIso();
    await env.DB.batch([
      env.DB.prepare('INSERT OR IGNORE INTO token_admin_grants(id,wallet_id,amount,reason,actor_fingerprint,created_at) VALUES(?,?,?,?,?,?)')
        .bind(requestId,id,amount,reason,fingerprint,stamp),
      env.DB.prepare(`INSERT OR IGNORE INTO admin_audit(id,event,license_id,actor_fingerprint,detail,created_at)
        SELECT ?,'token_grant',NULL,?, ?,? WHERE EXISTS(SELECT 1 FROM token_admin_grants WHERE id=? AND wallet_id=?)`)
        .bind('grant:'+requestId,fingerprint,JSON.stringify({wallet_id:id,amount,reason}),stamp,requestId,id)
    ]);
    return json({ok:true,wallet_id:id,amount,balance:await balanceOf(env,id)});
  }
  return json({error: 'Not found'}, 404);
}


// TOKEN SHOP 12.1 — ledger authoritative in D1, no client-side minting.
// The desktop is untrusted: its "download completed" signal is NOT cryptographic proof.
const WALLET_DEVICE = /^[a-f0-9]{32}$/;
const WALLET_KEY = /^yvdw-[a-f0-9]{64}$/;
const TOKEN_PACKAGES = Object.freeze({STARTER:[100,1],PRO:[500,7],ULTRA:[1500,30]});
const unix = () => Math.floor(Date.now()/1000);
const walletAuth = async (request, body, env) => {
  const token=(request.headers.get('authorization')||'').replace(/^Bearer /i,'');
  if(!WALLET_KEY.test(token) || !WALLET_DEVICE.test(body.device)) return null;
  const row=await env.DB.prepare('SELECT id FROM token_wallets WHERE secret_hash=? AND device=?')
    .bind(await digest(token),body.device).first();
  return row?.id || null;
};
const balanceOf = async (env,id) => {
  const a=await env.DB.prepare('SELECT COALESCE(SUM(delta),0) AS balance FROM token_ledger WHERE wallet_id=?').bind(id).first();
  const g=await env.DB.prepare('SELECT COALESCE(SUM(amount),0) AS total FROM token_admin_grants WHERE wallet_id=?').bind(id).first();
  return Number(a?.balance||0)+Number(g?.total||0);
};
const walletStatus = async (env,id) => {
  const expiry=await env.DB.prepare('SELECT MAX(expires_at_s) AS expiry FROM token_purchases WHERE wallet_id=?').bind(id).first();
  const expires=Number(expiry?.expiry||0);
  return {wallet_id:id,balance:await balanceOf(env,id),premium_until:expires>0?new Date(expires*1000).toISOString():null,active:expires>unix()};
};
async function handleWallet(path,body,request,env,ipHash) {
  const device=typeof body.device==='string'?body.device:'';
  if(!WALLET_DEVICE.test(device))return json({error:'Invalid device'},400);
  const day=new Date().toISOString().slice(0,10);
  if(path==='/wallet/register') {
    const blocked=await rateLimit(env,'wallet-register',ipHash,{max:6,seconds:3600});
    if(blocked)return blocked;
    // Guest registration is capped per network fingerprint, not proof of real identity.
    const current=await env.DB.prepare('SELECT COUNT(*) AS n FROM token_wallets WHERE ip_hash=? AND day=?').bind(ipHash,day).first();
    if(Number(current?.n||0)>=3)return json({error:'Dzienny limit nowych portfeli na tej sieci'},429);
    const key='yvdw-'+random(32),id=crypto.randomUUID();
    await env.DB.prepare('INSERT INTO token_wallets(id,secret_hash,device,created_at,ip_hash,day) VALUES(?,?,?,?,?,?)')
      .bind(id,await digest(key),device,nowIso(),ipHash,day).run();
    return json({wallet_token:key,balance:0,premium_until:null,active:false});
  }
  const id=await walletAuth(request,body,env);
  if(!id)return json({error:'Nieautoryzowany portfel'},401);
  if(path==='/wallet/status')return json(await walletStatus(env,id));
  if(path==='/wallet/start') {
    if(typeof body.url!=='string'||body.url.length>2048)return json({error:'Invalid URL'},400);
    let address;
    try{address=new URL(body.url);if(address.protocol!=='https:'&&address.protocol!=='http:')throw Error();
      if(address.username||address.password||address.port||!address.hostname||address.hostname==='localhost')throw Error();
    }catch(_){return json({error:'Invalid URL'},400)}
    const hash=await digest(address.origin.toLowerCase()+address.pathname+address.search);
    const existing=await env.DB.prepare('SELECT id FROM token_sessions WHERE wallet_id=? AND day=? AND url_hash=?')
      .bind(id,day,hash).first();
    if(existing)return json({ticket:existing.id,repeat:true});
    const ticket=crypto.randomUUID();
    await env.DB.prepare('INSERT OR IGNORE INTO token_sessions(id,wallet_id,day,url_hash,started_at_s) VALUES(?,?,?,?,?)')
      .bind(ticket,id,day,hash,unix()).run();
    const row=await env.DB.prepare('SELECT id FROM token_sessions WHERE wallet_id=? AND day=? AND url_hash=?')
      .bind(id,day,hash).first();
    return json({ticket:row?.id||ticket});
  }
  if(path==='/wallet/complete') {
    const ticket=typeof body.ticket==='string'?body.ticket:'';
    if(!UUID.test(ticket))return json({error:'Invalid ticket'},400);
    // One atomic INSERT: checks server time, cap and duplicates inside the same D1 write.
    const receipt='reward:'+ticket, now=unix();
    const added=await env.DB.prepare(`INSERT OR IGNORE INTO token_ledger
      (id,wallet_id,delta,kind,day,url_hash,ip_hash,created_at)
      SELECT ?,s.wallet_id,10,'reward',s.day,s.url_hash,?,?
      FROM token_sessions s WHERE s.id=? AND s.wallet_id=?
      AND s.started_at_s <= ? AND s.started_at_s >= ? AND s.day=?
      AND NOT EXISTS (SELECT 1 FROM token_ledger l WHERE l.wallet_id=s.wallet_id AND l.day=s.day AND l.url_hash=s.url_hash AND l.kind='reward')
      AND (SELECT COALESCE(SUM(delta),0) FROM token_ledger l WHERE l.wallet_id=s.wallet_id AND l.day=s.day AND l.kind='reward') < 100
      AND (SELECT COALESCE(SUM(delta),0) FROM token_ledger l WHERE l.ip_hash=? AND l.day=s.day AND l.kind='reward') < 300`)
      .bind(receipt,ipHash,nowIso(),ticket,id,now-2,now-7200,day,ipHash).run();
    const awarded=Number(added.meta?.changes||0)===1?10:0;
    return json({...await walletStatus(env,id),awarded,reason:awarded?'Przyznano 10 tokenów':'Brak nagrody: limit, duplikat lub nieprawidłowe zgłoszenie'});
  }
  if(path==='/wallet/buy') {
    const name=typeof body.package==='string'?body.package:'';
    const spec=TOKEN_PACKAGES[name];
    if(!spec)return json({error:'Nieznany pakiet'},400);
    const requestId=typeof body.request_id==='string'?body.request_id:'';
    if(!UUID.test(requestId))return json({error:'Invalid request id'},400);
    const debit='buy:'+requestId;
    const existing=await env.DB.prepare('SELECT 1 AS ok FROM token_purchases WHERE id=? AND wallet_id=?').bind(requestId,id).first();
    if(existing)return json({...await walletStatus(env,id),already_processed:true});
    // D1 batch is transactional. Conditional debit + entitlement use the same idempotency ID.
    await env.DB.batch([
      env.DB.prepare(`INSERT OR IGNORE INTO token_ledger(id,wallet_id,delta,kind,day,url_hash,ip_hash,created_at)
       SELECT ?,?,-?,'purchase',?,NULL,NULL,?
       WHERE ((SELECT COALESCE(SUM(delta),0) FROM token_ledger WHERE wallet_id=?) + (SELECT COALESCE(SUM(amount),0) FROM token_admin_grants WHERE wallet_id=?))>=?`)
       .bind(debit,id,spec[0],day,nowIso(),id,id,spec[0]),
      env.DB.prepare(`INSERT OR IGNORE INTO token_purchases(id,wallet_id,package,price,expires_at_s,created_at)
       SELECT ?,?,?,?,MAX(?,COALESCE((SELECT MAX(expires_at_s) FROM token_purchases WHERE wallet_id=?),0))+?,?
       FROM token_ledger WHERE id=? AND wallet_id=?`)
       .bind(requestId,id,name,spec[0],unix(),id,spec[1]*86400,nowIso(),debit,id)
    ]);
    const row=await env.DB.prepare('SELECT id FROM token_purchases WHERE id=? AND wallet_id=?').bind(requestId,id).first();
    if(!row)return json({...await walletStatus(env,id),error:'Za mało tokenów'},409);
    return json({...await walletStatus(env,id),package:name});
  }
  return json({error:'Not found'},404);
}

export default {
  async fetch(request, env) {
    try {
      const url = new URL(request.url), path = url.pathname;
      if (path === '/health' && request.method === 'GET') return json({ok: true, service: 'YVD Premium Cloud 5.1 + Token Shop 12.1'});
      if (!env.DB) return json({error: 'Baza D1 nie skonfigurowana'}, 503);
      if (request.method !== 'POST') return json({error: 'Method not allowed'}, 405, {'Allow': 'POST'});
      if (path.startsWith('/wallet/')) {
        if(!['/wallet/register','/wallet/status','/wallet/start','/wallet/complete','/wallet/buy'].includes(path))return json({error:'Not found'},404);
        const fp=await ipFingerprint(request,env);
        const limit=await rateLimit(env,'wallet-api',fp,{max:150,seconds:600});
        if(limit)return limit;
        const parsed=await readJson(request);if(parsed.error)return parsed.error;
        return handleWallet(path,parsed.value,request,env,fp);
      }
      if (!ADMIN_PATHS.has(path) && path !== '/activate' && path !== '/validate') return json({error: 'Not found'}, 404);
      if (path.startsWith('/admin/') && (!env.ADMIN_TOKEN || !safeEqual(request.headers.get('Authorization') || '', `Bearer ${env.ADMIN_TOKEN}`))) {
        const fingerprint = await ipFingerprint(request, env);
        const limited = await rateLimit(env, 'admin-auth', fingerprint, LIMITS.admin);
        return limited || json({error: 'Unauthorized'}, 401);
      }
      const fingerprint = await ipFingerprint(request, env);
      const spec = path.startsWith('/admin/') ? LIMITS.admin : LIMITS[path];
      if (path.startsWith('/admin/') && !env.ADMIN_TOKEN) return json({error: 'Server not configured'}, 503);
      const limited = await rateLimit(env, path.startsWith('/admin/') ? 'admin' : path, fingerprint, spec);
      if (limited) return limited;
      const parsed = await readJson(request);
      if (parsed.error) return parsed.error;
      const body = parsed.value;
      if (path.startsWith('/admin/')) return handleAdmin(path, body, env, fingerprint);
      if (path === '/activate') {
        const code = typeof body.code === 'string' ? body.code : '';
        const device = typeof body.device === 'string' ? body.device : '';
        if (!CODE.test(code) || !DEVICE.test(device)) return json({error: 'Invalid code or device'}, 400);
        const row = await env.DB.prepare('SELECT id, owner, expires_at, revoked, device FROM licenses WHERE code_hash = ?')
          .bind(await digest(code)).first();
        if (!active(row)) return json({active: false, error: 'Kod nie istnieje lub wygasł'}, 403);
        if (row.device && row.device !== device) return json({active: false, error: 'Kod przypisany do innego urządzenia'}, 403);
        const token = 'yvd5t-' + random(32);
        // Atomic compare-and-set prevents simultaneous binding to different devices.
        const updated = await env.DB.prepare(`UPDATE licenses SET device = ?, token_hash = ?
          WHERE id = ? AND revoked = 0 AND (expires_at IS NULL OR expires_at > ?)
          AND (device IS NULL OR device = ?)`)
          .bind(device, await digest(token), row.id, nowIso(), device).run();
        if (!updated.meta?.changes) return json({active: false, error: 'Kod przypisany do innego urządzenia lub wygasł'}, 403);
        return json({active: true, token, expires_at: row.expires_at, owner: row.owner});
      }
      if (path === '/validate') {
        const token = typeof body.token === 'string' ? body.token : '';
        const device = typeof body.device === 'string' ? body.device : '';
        if (!TOKEN.test(token) || !DEVICE.test(device)) return json({active: false}, 403);
        const row = await env.DB.prepare('SELECT owner, expires_at, revoked FROM licenses WHERE token_hash = ? AND device = ?')
          .bind(await digest(token), device).first();
        return json({active: active(row), owner: row?.owner || null, expires_at: row?.expires_at || null});
      }
      return json({error: 'Not found'}, 404);
    } catch (error) {
      // Do not echo exceptions, D1 statements, tokens or sensitive data.
      console.error('YVD Cloud 5.1 request failed', error?.name || 'Unknown error');
      return json({error: 'Service temporarily unavailable'}, 503);
    }
  },
};
