const SHEET_NAME = "Prospects";
const CONTENT_SHEET = "Content";
const MAX_ATTEMPTS = 3;
const DAILY_SEND_LIMIT = 20;
const WA_NUMBER = "6287813871926";
const AGENCY_NAME = "Sonjaya Remote Business Services";

const HEADERS = [
  "Lead ID","Tanggal ditemukan","Nama bisnis","Email","Sumber email","Website","Social",
  "Kota","Kategori","Bukti publik","Skor","Prioritas","Kebutuhan terdeteksi",
  "Layanan direkomendasikan","Pain point","Hook personal","Subject","Body","Status",
  "Sent At","Reply At","Reply Intent","Last Reply","WhatsApp Handoff","Attempts",
  "Last Error","Opt Out","Catatan"
];

function sheet_(){
  const ss=SpreadsheetApp.getActiveSpreadsheet();
  let sh=ss.getSheetByName(SHEET_NAME);
  if(!sh) sh=ss.insertSheet(SHEET_NAME);
  if(sh.getLastRow()===0) sh.getRange(1,1,1,HEADERS.length).setValues([HEADERS]);
  sh.setFrozenRows(1);
  sh.getRange(1,1,1,HEADERS.length).setFontWeight("bold");
  sh.getDataRange().setWrap(true);
  return sh;
}
function contentSheet_(){
  const ss=SpreadsheetApp.getActiveSpreadsheet();
  let sh=ss.getSheetByName(CONTENT_SHEET);
  if(!sh) sh=ss.insertSheet(CONTENT_SHEET);
  const headers=["Tanggal","Platform","Format","Topik","Hook","Caption","CTA","Visual Prompt","Status"];
  if(sh.getLastRow()===0) sh.getRange(1,1,1,headers.length).setValues([headers]);
  sh.setFrozenRows(1); sh.getRange(1,1,1,headers.length).setFontWeight("bold");
  return sh;
}
function col_(name){ return HEADERS.indexOf(name)+1; }
function now_(){ return new Date(); }
function json_(obj){
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}
function auth_(body){
  const expected=PropertiesService.getScriptProperties().getProperty("WEBHOOK_TOKEN");
  return Boolean(expected && body && body.token===expected);
}
function waLink_(business,email){
  const text="Halo Rey, saya dari "+business+". Saya membalas email tentang kebutuhan bisnis kami. Email: "+email;
  return "https://wa.me/"+WA_NUMBER+"?text="+encodeURIComponent(text);
}

function doGet(){ return json_({ok:true,service:"Sonjaya Remote Agency",status:"running"}); }

function doPost(e){
  try{
    const body=JSON.parse((e.postData&&e.postData.contents)||"{}");
    if(!auth_(body)) return json_({ok:false,error:"Unauthorized"});
    const action=body.action||"ingest";
    if(action==="ingest") return ingest_(body.rows||[]);
    if(action==="send_queue") return sendQueue_(Number(body.limit||DAILY_SEND_LIMIT));
    if(action==="scan_replies") return scanReplies_(Number(body.limit||20));
    if(action==="mark_error") return markError_(String(body.id||""),String(body.error||""));
    if(action==="content_ingest") return ingestContent_(body.rows||[]);
    return json_({ok:false,error:"Unknown action"});
  }catch(err){ return json_({ok:false,error:String(err)}); }
}

function ingest_(rows){
  const sh=sheet_();
  const existing={};
  if(sh.getLastRow()>=2){
    sh.getRange(2,col_("Email"),sh.getLastRow()-1,1).getValues().forEach(function(r){
      const e=String(r[0]||"").toLowerCase().trim(); if(e) existing[e]=true;
    });
  }
  let added=0,duplicates=0,noEmail=0;
  rows.forEach(function(row){
    const email=String(row.recipient_email||"").toLowerCase().trim();
    if(!email||email.indexOf("@")===-1){noEmail++;return;}
    if(existing[email]){duplicates++;return;}
    const out=new Array(HEADERS.length).fill("");
    const set=(h,v)=>out[col_(h)-1]=v==null?"":v;
    set("Lead ID",row.lead_id||Utilities.getUuid().replace(/-/g,"").slice(0,12));
    set("Tanggal ditemukan",row.tanggal_ditemukan||Utilities.formatDate(now_(),"Asia/Jakarta","yyyy-MM-dd HH:mm:ss"));
    set("Nama bisnis",row.nama_bisnis); set("Email",email); set("Sumber email",row.email_source_url);
    set("Website",row.website_url); set("Social",row.social_url); set("Kota",row.kota);
    set("Kategori",row.kategori); set("Bukti publik",row.bukti_publik); set("Skor",Number(row.skor||0));
    set("Prioritas",Number(row.skor||0)>=85?"A":Number(row.skor||0)>=75?"B":"C");
    set("Kebutuhan terdeteksi",row.detected_need); set("Layanan direkomendasikan",row.recommended_service);
    set("Pain point",row.pain_point); set("Hook personal",row.alasan); set("Subject",row.subject); set("Body",row.body);
    set("Status",row.status||"REVIEW"); set("Opt Out","NO"); set("Attempts",0); set("Catatan",row.catatan);
    sh.appendRow(out); existing[email]=true; added++;
  });
  return json_({ok:true,received:rows.length,added:added,duplicates:duplicates,no_email:noEmail});
}

function sendQueue_(limit){
  const sh=sheet_(); const last=sh.getLastRow();
  if(last<2) return json_({ok:true,sent_today:0,sent:0,quota:MailApp.getRemainingDailyQuota()});
  limit=Math.max(1,Math.min(limit||DAILY_SEND_LIMIT,DAILY_SEND_LIMIT));
  const values=sh.getRange(2,1,last-1,HEADERS.length).getValues();
  const idx={}; HEADERS.forEach(function(h,i){idx[h]=i;});
  const today=Utilities.formatDate(now_(),"Asia/Jakarta","yyyy-MM-dd");
  let sentToday=0; const q=[];
  values.forEach(function(r){
    const sentAt=String(r[idx["Sent At"]]||""); if(sentAt.indexOf(today)===0) sentToday++;
    const status=String(r[idx["Status"]]||"").toUpperCase().trim();
    const opt=String(r[idx["Opt Out"]]||"").toUpperCase().trim();
    if(status!=="READY"||opt==="YES") return;
    const email=String(r[idx["Email"]]||"").trim(), subject=String(r[idx["Subject"]]||"").trim(), body=String(r[idx["Body"]]||"").trim();
    if(!email||!subject||!body) return;
    const attempts=Number(r[idx["Attempts"]]||0); if(attempts>=MAX_ATTEMPTS) return;
    q.push({row:r,_row:r,leadId:String(r[idx["Lead ID"]]||""),email,subject,body,score:Number(r[idx["Skor"]]||0),business:String(r[idx["Nama bisnis"]]||"")});
  });
  q.sort(function(a,b){return b.score-a.score;});
  const remaining=Math.max(0,Math.min(MailApp.getRemainingDailyQuota(),DAILY_SEND_LIMIT-sentToday));
  const selected=q.slice(0,Math.min(limit,remaining));
  let sent=0;
  selected.forEach(function(x){
    try{
      MailApp.sendEmail({to:x.email,subject:x.subject,body:x.body,name:AGENCY_NAME,replyTo:Session.getActiveUser().getEmail()});
      const rowNum=findRowById_(x.leadId);
      if(rowNum>1){
        sh.getRange(rowNum,col_("Status")).setValue("SENT");
        sh.getRange(rowNum,col_("Sent At")).setValue(now_());
        sh.getRange(rowNum,col_("Last Error")).clearContent();
      }
      sent++;
    }catch(err){ markError_(x.leadId,String(err)); }
  });
  return json_({ok:true,sent_today:sentToday+sent,sent:sent,remaining:Math.max(0,DAILY_SEND_LIMIT-sentToday-sent),gmail_quota:MailApp.getRemainingDailyQuota()});
}

function findRowById_(id){
  const sh=sheet_(); if(sh.getLastRow()<2) return -1;
  const vals=sh.getRange(2,col_("Lead ID"),sh.getLastRow()-1,1).getValues();
  for(let i=0;i<vals.length;i++) if(String(vals[i][0]||"")===id) return i+2;
  return -1;
}

function markError_(id,error){
  if(!id) return json_({ok:false,error:"Missing id"});
  const sh=sheet_(), row=findRowById_(id);
  if(row<2) return json_({ok:false,error:"Lead ID not found"});
  const c=sh.getRange(row,col_("Attempts")), attempts=Number(c.getValue()||0)+1;
  c.setValue(attempts); sh.getRange(row,col_("Status")).setValue(attempts>=MAX_ATTEMPTS?"FAILED":"ERROR");
  sh.getRange(row,col_("Last Error")).setValue(String(error||"Unknown error").slice(0,1000));
  return json_({ok:true,id:id,attempts:attempts});
}

function scanReplies_(limit){
  const sh=sheet_(); const last=sh.getLastRow();
  if(last<2) return json_({ok:true,replied:0});
  const rows=sh.getRange(2,1,last-1,HEADERS.length).getValues();
  const idx={}; HEADERS.forEach(function(h,i){idx[h]=i;});
  const threads=GmailApp.search("in:inbox newer_than:3d -from:me",0,50);
  let replied=0;
  for(let t=0;t<threads.length&&replied<limit;t++){
    const thread=threads[t], subject=thread.getFirstMessageSubject()||"";
    const m=subject.match(/\[SJ-([a-f0-9]{12})\]/i); if(!m) continue;
    const leadId=m[1], rowNum=findRowById_(leadId); if(rowNum<2) continue;
    const current=sh.getRange(rowNum,col_("Status")).getValue();
    if(String(current).toUpperCase()==="WA_HANDOFF"||String(current).toUpperCase()==="OPTOUT") continue;
    const msgs=thread.getMessages(); let inbound=null;
    for(let i=msgs.length-1;i>=0;i--){ if(!msgs[i].getFrom().toLowerCase().includes(Session.getActiveUser().getEmail().toLowerCase())){inbound=msgs[i];break;} }
    if(!inbound) continue;
    const body=String(inbound.getPlainBody()||"").slice(0,5000);
    const upper=body.toUpperCase();
    if(upper.includes("UNSUBSCRIBE")){
      sh.getRange(rowNum,col_("Status")).setValue("OPTOUT"); sh.getRange(rowNum,col_("Opt Out")).setValue("YES");
      continue;
    }
    const business=String(sh.getRange(rowNum,col_("Nama bisnis")).getValue()||"Perusahaan");
    const email=String(sh.getRange(rowNum,col_("Email")).getValue()||"");
    const intent=/harga|price|biaya|cost|tertarik|minat|interested|bisa|boleh|minta|info|detail|contoh|diskusi|call|meeting|whatsapp|wa\b/i.test(body)?"INTERESTED":"REPLIED";
    const wa=waLink_(business,email);
    const replyText="Terima kasih sudah membalas. Agar lebih cepat, kita bisa lanjut ke WhatsApp untuk membahas kebutuhan yang paling sesuai.\\n\\nWhatsApp: "+wa+"\\n\\nSalam,\\nRey\\n"+AGENCY_NAME;
    try{ thread.reply(replyText,{name:AGENCY_NAME}); }catch(e){ continue; }
    sh.getRange(rowNum,col_("Status")).setValue("WA_HANDOFF");
    sh.getRange(rowNum,col_("Reply At")).setValue(now_());
    sh.getRange(rowNum,col_("Reply Intent")).setValue(intent);
    sh.getRange(rowNum,col_("Last Reply")).setValue(body.slice(0,1500));
    sh.getRange(rowNum,col_("WhatsApp Handoff")).setValue(wa);
    replied++;
  }
  return json_({ok:true,replied:replied});
}

function ingestContent_(rows){
  const sh=contentSheet_();
  if(!Array.isArray(rows)) rows=[];
  rows.forEach(function(r){
    sh.appendRow([r.date,r.platform,r.format,r.topic,r.hook,r.caption,r.cta,r.visual_prompt,r.status||"PLANNED"]);
  });
  return json_({ok:true,added:rows.length});
}

function setup(){
  sheet_(); contentSheet_();
  // Optional hourly reply monitor. The install happens only once and uses the owner's Google authorization.
  const triggers=ScriptApp.getProjectTriggers();
  if(!triggers.some(t=>t.getHandlerFunction()==="hourlyReplyMonitor_")){
    ScriptApp.newTrigger("hourlyReplyMonitor_").timeBased().everyHours(1).create();
  }
  return "Sonjaya system ready";
}
function hourlyReplyMonitor_(){ scanReplies_(20); }
