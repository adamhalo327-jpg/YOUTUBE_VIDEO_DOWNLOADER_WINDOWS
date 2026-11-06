import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync} from 'node:fs';
import {createHash,randomUUID} from 'node:crypto';
import worker from '../cloud_worker/src/worker.js';
const db=new DatabaseSync(':memory:');
const src=new URL('../cloud_worker/',import.meta.url);
for(const file of ['token_shop_12_1_migration.sql','token_admin_grants_12_1_migration.sql','token_shop_14_0_migration.sql'])db.exec(readFileSync(new URL(file,src),'utf-8'));
db.exec('CREATE TABLE security_rate_limits(bucket_key TEXT PRIMARY KEY,window_start INTEGER NOT NULL,count INTEGER NOT NULL)');
const adapter={prepare(sql){return {bind(...args){return {
 async first(){return db.prepare(sql).get(...args)||null;},
 async all(){return {results:db.prepare(sql).all(...args)};},
 async run(){const data=db.prepare(sql).run(...args);return {meta:{changes:data.changes}};}
}}}},async batch(statements){db.exec('BEGIN');try{const rows=[];for(const s of statements)rows.push(await s.run());db.exec('COMMIT');return rows;}catch(e){db.exec('ROLLBACK');throw e;}}};
const wallet=randomUUID(),secret='yvdw-'+'ab'.repeat(32),device='a'.repeat(32),ip='1.2.3.4',day=new Date().toISOString().slice(0,10);
const hash=createHash('sha256').update(secret).digest('hex');
db.prepare('INSERT INTO token_wallets VALUES (?,?,?,?,?,?)').run(wallet,hash,device,day,'ip',day);
for(let n=0;n<3;n++)db.prepare('INSERT INTO token_ledger VALUES (?,?,?,?,?,?,?,?)').run(randomUUID(),wallet,10,'reward',day,'hash'+n,'ip',new Date().toISOString());
const env={DB:adapter,ADMIN_TOKEN:'local-test-admin-secret',RATE_LIMIT_SALT:'test-salt'};
async function ask(path,data={}){
 const resp=await worker.fetch(new Request('https://yvd-premium-cloud.example'+path,{method:'POST',headers:{'Authorization':'Bearer '+secret,'Content-Type':'application/json','CF-Connecting-IP':ip},body:JSON.stringify({device,...data})}),env);
 const json=await resp.json();return {status:resp.status,...json};
}
let state=await ask('/wallet/status');assert.equal(state.status,200);assert.equal(state.balance,30);assert.equal(state.wallet_id,wallet);
let missions=await ask('/wallet/missions');assert.equal(missions.status,200);assert.equal(missions.missions.find(x=>x.id==='DAILY_3').progress,3);
let claim=await ask('/wallet/claim-mission',{mission:'DAILY_3'});assert.equal(claim.awarded,20);assert.equal(claim.balance,50);
claim=await ask('/wallet/claim-mission',{mission:'DAILY_3'});assert.equal(claim.awarded,0);assert.equal(claim.balance,50);
let purchase=await ask('/wallet/buy',{package:'PLUS',request_id:randomUUID()});assert.equal(purchase.status,409);assert.equal(purchase.balance,50);
db.prepare('INSERT INTO token_admin_grants VALUES (?,?,?,?,?,?)').run(randomUUID(),wallet,500,'test','actor',new Date().toISOString());
const id=randomUUID();purchase=await ask('/wallet/buy',{package:'PLUS',request_id:id});assert.equal(purchase.status,200);assert.equal(purchase.balance,300);
const expiry=Date.parse(purchase.premium_until);
purchase=await ask('/wallet/buy',{package:'PLUS',request_id:id});assert.equal(purchase.already_processed,true);assert.equal(purchase.balance,300);
purchase=await ask('/wallet/buy',{package:'STARTER',request_id:randomUUID()});assert.equal(purchase.status,200);assert.equal(purchase.balance,200);assert.ok(Date.parse(purchase.premium_until)>expiry);
state=await ask('/wallet/status');assert.equal(state.balance,200);
assert.equal(db.prepare('SELECT COUNT(*) AS n FROM token_mission_claims14').get().n,1);
console.log('TOKEN SHOP 14 Worker integration OK: saldo, misje, duplikaty, pakiety i zgodność starego STARTER');
