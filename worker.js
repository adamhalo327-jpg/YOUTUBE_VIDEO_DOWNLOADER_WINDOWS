// YVD Premium Cloud for Cloudflare Workers + D1. Set ADMIN_TOKEN as Worker secret.
// App users never receive admin token. No CORS headers => browser origins are not enabled.
const encoder = new TextEncoder();
const json = (data,status=200)=>new Response(JSON.stringify(data),{status,headers:{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store'}});
const sha = async value => Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',encoder.encode(value)))).map(x=>x.toString(16).padStart(2,'0')).join('');
const random = (n=24)=>Array.from(crypto.getRandomValues(new Uint8Array(n))).map(x=>x.toString(16).padStart(2,'0')).join('');
const iso = ()=>new Date().toISOString();
const active = row=> row && !row.revoked && (!row.expires_at || row.expires_at>iso());
const safeEqual=(a,b)=>{
 const aa=encoder.encode(a),bb=encoder.encode(b);
 let diff=aa.length^bb.length;
 for(let i=0;i<Math.max(aa.length,bb.length);i++)diff|=(aa[i]||0)^(bb[i]||0);
 return diff===0;
};
export default {async fetch(request,env){
 try {
  const url=new URL(request.url),path=url.pathname;
  if(path==='/health' && request.method==='GET')return json({ok:true,service:'YVD Premium Cloud 5.0'});
  if(!env.DB)return json({error:'Baza D1 nie skonfigurowana'},503);
  if(request.method!=='POST')return json({error:'Method not allowed'},405);
  if(Number(request.headers.get('content-length')||0)>32768)return json({error:'Request too large'},413);
  const body=await request.json();
  if(!body || typeof body!=='object' || Array.isArray(body))return json({error:'Invalid JSON'},400);
  if(path.startsWith('/admin/')){
   if(!env.ADMIN_TOKEN || !safeEqual(request.headers.get('Authorization')||'',`Bearer ${env.ADMIN_TOKEN}`))return json({error:'Unauthorized'},401);
   if(path==='/admin/issue'){
    const owner=String(body.owner||'').trim();const minutes=body.minutes;
    if(!owner || owner.length>100 || !(minutes===null || (Number.isSafeInteger(minutes) && minutes>=1 && minutes<=52560000)))return json({error:'Invalid owner or duration'},400);
    const id=crypto.randomUUID(),code='YVD5-'+random(20),expires=minutes===null?null:new Date(Date.now()+minutes*60000).toISOString();
    await env.DB.prepare('INSERT INTO licenses (id,code_hash,owner,created_at,expires_at) VALUES (?,?,?,?,?)').bind(id,await sha(code),owner,iso(),expires).run();
    return json({id,code,owner,expires_at:expires});
   }
   if(path==='/admin/list'){
    const res=await env.DB.prepare('SELECT id,owner,created_at,expires_at,revoked,device IS NOT NULL AS activated FROM licenses ORDER BY created_at DESC LIMIT 200').all();
    return json({licenses:res.results});
   }
   if(path==='/admin/stats'){
    const x=await env.DB.prepare('SELECT COUNT(*) AS total, SUM(CASE WHEN revoked=1 THEN 1 ELSE 0 END) AS revoked, SUM(CASE WHEN device IS NOT NULL THEN 1 ELSE 0 END) AS activated FROM licenses').first();
    return json({stats:x});
   }
   if(path==='/admin/revoke'){
    const id=String(body.id||'');if(!/^[a-f0-9-]{36}$/.test(id))return json({error:'Invalid id'},400);
    const row=await env.DB.prepare('UPDATE licenses SET revoked=1 WHERE id=?').bind(id).run();return json({ok:row.meta.changes>0});
   }
   if(path==='/admin/extend'){
    const id=String(body.id||''),minutes=body.minutes;
    if(!/^[a-f0-9-]{36}$/.test(id)|| !Number.isSafeInteger(minutes)||minutes<1||minutes>52560000)return json({error:'Invalid input'},400);
    const row=await env.DB.prepare('SELECT expires_at FROM licenses WHERE id=? AND revoked=0').bind(id).first();
    if(!row)return json({error:'Not found'},404);
    if(row.expires_at===null)return json({ok:true,expires_at:null});
    const exp=new Date(Math.max(Date.now(),Date.parse(row.expires_at))+minutes*60000).toISOString();
    await env.DB.prepare('UPDATE licenses SET expires_at=? WHERE id=?').bind(exp,id).run();return json({ok:true,expires_at:exp});
   }
   return json({error:'Not found'},404);
  }
  if(path==='/activate'){
   const code=String(body.code||''),device=String(body.device||'');
   if(!/^YVD5-[a-f0-9]{40}$/.test(code)|| !/^[a-f0-9]{32}$/.test(device))return json({error:'Invalid code or device'},400);
   const row=await env.DB.prepare('SELECT * FROM licenses WHERE code_hash=?').bind(await sha(code)).first();
   if(!active(row))return json({active:false,error:'Kod nie istnieje lub wygasł'},403);
   if(row.device && row.device!==device)return json({active:false,error:'Kod przypisany do innego urządzenia'},403);
   // Keep existing token upon same-device activation only if the client already knows it? Rotate token for owner of code.
   const token='yvd5t-'+random(32);
   await env.DB.prepare('UPDATE licenses SET device=?,token_hash=? WHERE id=?').bind(device,await sha(token),row.id).run();
   return json({active:true,token,expires_at:row.expires_at,owner:row.owner});
  }
  if(path==='/validate'){
   const token=String(body.token||''),device=String(body.device||'');
   if(!/^yvd5t-[a-f0-9]{64}$/.test(token)|| !/^[a-f0-9]{32}$/.test(device))return json({active:false},403);
   const row=await env.DB.prepare('SELECT * FROM licenses WHERE token_hash=? AND device=?').bind(await sha(token),device).first();
   return json({active:!!active(row),owner:row?.owner||null,expires_at:row?.expires_at||null});
  }
  return json({error:'Not found'},404);
 }catch(e){return json({error:'Request failed'},400)}
}};
