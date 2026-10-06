const SHEET_NAME = "Prospects";
const CONTENT_SHEET = "Content";
const CONTENT_PLAN_SHEET = "Content Planning";
const MAX_ATTEMPTS = 3;
const DAILY_SEND_LIMIT = 20;
const MAX_FOLLOWUPS_PER_RUN = 5;
const AGENCY_NAME = "Sonjaya Remote Business Services";
const MANUAL_SEND_COL = "Manual Send";
const SEND_RESULT_COL = "Send Result";
const CONTENT_HEADERS = ["Tanggal","Platform","Format","Topik","Hook","Caption","CTA","Visual Prompt","Asset URL","Status","Publish Result"];
const CONTENT_PLAN_HEADERS = ["Tanggal","Platform","Format","Tujuan","Topik","Hook","Caption","CTA","Slide Count","Carousel PDF URL","Carousel Cover URL","Slides JSON","Status","Publish Mode","Catatan"];
const SOCIAL_LEADS_SHEET = "Social Leads";
const SOCIAL_LEADS_HEADERS = ["Tanggal","Platform","Keyword","Username","User ID","Comment ID","Comment","Post ID","DM Status","WhatsApp Link","Catatan"];

const HEADERS = [
  "Lead ID","Tanggal ditemukan","Nama bisnis","Email","Sumber email","Website","Social",
  "Kota","Kategori","Bukti publik","Skor","Prioritas","Kebutuhan terdeteksi",
  "Layanan direkomendasikan","Pain point","Hook personal","Subject","Body","Status",
  "Sent At","Follow-up 1 At","Follow-up 2 At","Follow-up 3 At","Reply At","Reply Intent",
  "Last Reply","WhatsApp Handoff","Attempts","Last Error","Opt Out","Catatan","Manual Send","Send Result"
];

function sheet_(){
  const ss=SpreadsheetApp.getActiveSpreadsheet();
  let sh=ss.getSheetByName(SHEET_NAME);
  if(!sh) sh=ss.insertSheet(SHEET_NAME);
  ensureHeaders_(sh,HEADERS);
  sh.setFrozenRows(1);
  sh.getRange(1,1,1,HEADERS.length).setFontWeight("bold");
  sh.getDataRange().setWrap(true);
  configureProspectControls_(sh);
  return sh;
}

function ensureHeaders_(sh, headers){
  if(sh.getLastColumn()===0 || sh.getLastRow()===0){
    sh.getRange(1,1,1,headers.length).setValues([headers]);
    return;
  }
  const current=sh.getRange(1,1,1,Math.max(1,sh.getLastColumn())).getValues()[0].map(String);
  headers.forEach(function(h){
    if(current.indexOf(h)===-1){
      sh.getRange(1,sh.getLastColumn()+1).setValue(h).setFontWeight("bold");
    }
  });
}

function configureProspectControls_(sh){
  const manualCol=col_("Manual Send");
  if(manualCol<1)return;
  const rows=Math.max(sh.getMaxRows()-1,100);
  sh.getRange(2,manualCol,rows,1)
    .setDataValidation(SpreadsheetApp.newDataValidation().requireCheckbox().build())
    .setHorizontalAlignment("center");
  const statusCol=col_("Status");
  if(statusCol>0){
    sh.getRange(2,statusCol,rows,1).setDataValidation(
      SpreadsheetApp.newDataValidation().requireValueInList(
        ["READY","REVIEW","SENT","FOLLOWUP_1","FOLLOWUP_2","FOLLOWUP_3","FOLLOWUP_DONE","REPLIED","WA_HANDOFF","OPTOUT","ERROR","FAILED"], true
      ).build()
    );
  }
}

function socialLeadsSheet_(){
  const ss=SpreadsheetApp.getActiveSpreadsheet();
  let sh=ss.getSheetByName(SOCIAL_LEADS_SHEET);
  if(!sh)sh=ss.insertSheet(SOCIAL_LEADS_SHEET);
  ensureHeaders_(sh,SOCIAL_LEADS_HEADERS);
  sh.setFrozenRows(1);
  sh.getRange(1,1,1,SOCIAL_LEADS_HEADERS.length).setFontWeight("bold");
  sh.getDataRange().setWrap(true);
  return sh;
}

function colSocial_(name){return SOCIAL_LEADS_HEADERS.indexOf(name)+1;}

function normalizeKeyword_(s){
  return String(s||"").toUpperCase().replace(/[^A-Z0-9]+/g," ").replace(/\s+/g," ").trim();
}

function commentMatchesKeyword_(text){
  const keyword=PropertiesService.getScriptProperties().getProperty("IG_COMMENT_KEYWORD")||"REY MAU";
  const hay=normalizeKeyword_(text), needle=normalizeKeyword_(keyword);
  return Boolean(needle && (hay===needle || hay.indexOf(needle)!==-1));
}

function socialCommentExists_(commentId){
  if(!commentId)return false;
  const sh=socialLeadsSheet_(),last=sh.getLastRow();
  if(last<2)return false;
  return sh.getRange(2,colSocial_("Comment ID"),last-1,1).getValues()
    .some(r=>String(r[0]||"")===String(commentId));
}

function logSocialLead_(row){
  const sh=socialLeadsSheet_();
  const o=SOCIAL_LEADS_HEADERS.map(h=>row[h]||"");
  sh.appendRow(o);
}

function sendInstagramPrivateReply_(commentId,text){
  const token=PropertiesService.getScriptProperties().getProperty("IG_ACCESS_TOKEN")||"";
  const igUserId=PropertiesService.getScriptProperties().getProperty("IG_USER_ID")||"";
  const version=PropertiesService.getScriptProperties().getProperty("IG_API_VERSION")||"v26.0";
  const host=PropertiesService.getScriptProperties().getProperty("IG_MESSAGING_HOST")||"https://graph.instagram.com";
  if(!token||!igUserId)throw new Error("INSTAGRAM_MESSAGING_NOT_CONFIGURED");
  return urlFetchJson_(host+"/"+version+"/"+encodeURIComponent(igUserId)+"/messages",{
    method:"post",
    contentType:"application/json",
    headers:{Authorization:"Bearer "+token},
    payload:JSON.stringify({recipient:{comment_id:String(commentId)},message:{text:String(text||"").slice(0,1000)}}),
    muteHttpExceptions:true
  });
}

function handleInstagramWebhook_(body){
  let processed=0,matched=0,dmSent=0,errors=0;
  const entries=Array.isArray(body&&body.entry)?body.entry:[];
  entries.forEach(function(entry){
    const changes=Array.isArray(entry&&entry.changes)?entry.changes:[];
    changes.forEach(function(change){
      if(String(change.field||"").toLowerCase()!=="comments")return;
      const v=change.value||{}, commentId=String(v.id||v.comment_id||""), text=String(v.text||"");
      const from=v.from||{}, userId=String(from.id||""), username=String(from.username||from.name||"");
      const media=v.media||{}, postId=String(media.id||v.media_id||"");
      processed++;
      if(!commentId||!commentMatchesKeyword_(text)||socialCommentExists_(commentId))return;
      matched++;
      const wa=waLink_(username||"Instagram lead",username||"");
      let dmStatus="NO_WA_NUMBER",note="Keyword cocok; WA_NUMBER belum diatur.";
      if(wa){
        try{
          const msg="Halo "+(username?"@"+username:"")+"! 👋 Makasih sudah komen REY MAU. Kalau mau lanjut dan minta detail jasanya, langsung chat WhatsApp di sini:\n"+wa;
          const result=sendInstagramPrivateReply_(commentId,msg);
          dmStatus="DM_SENT"; note=JSON.stringify(result).slice(0,800); dmSent++;
        }catch(err){
          dmStatus="DM_ERROR"; note=String(err).slice(0,800); errors++;
        }
      }
      logSocialLead_({
        "Tanggal":Utilities.formatDate(now_(),"Asia/Jakarta","yyyy-MM-dd HH:mm:ss"),
        "Platform":"Instagram",
        "Keyword":PropertiesService.getScriptProperties().getProperty("IG_COMMENT_KEYWORD")||"REY MAU",
        "Username":username,
        "User ID":userId,
        "Comment ID":commentId,
        "Comment":text,
        "Post ID":postId,
        "DM Status":dmStatus,
        "WhatsApp Link":wa,
        "Catatan":note
      });
    });
  });
  return json_({ok:true,processed:processed,matched:matched,dm_sent:dmSent,errors:errors});
}

function contentPlanningSheet_(){
  const ss=SpreadsheetApp.getActiveSpreadsheet();
  let sh=ss.getSheetByName(CONTENT_PLAN_SHEET);
  if(!sh)sh=ss.insertSheet(CONTENT_PLAN_SHEET);
  ensureHeaders_(sh,CONTENT_PLAN_HEADERS);
  sh.setFrozenRows(1);
  sh.getRange(1,1,1,CONTENT_PLAN_HEADERS.length).setFontWeight("bold");
  sh.getDataRange().setWrap(true);
  return sh;
}

function contentSheet_(){
  const ss=SpreadsheetApp.getActiveSpreadsheet();
  let sh=ss.getSheetByName(CONTENT_SHEET);
  if(!sh) sh=ss.insertSheet(CONTENT_SHEET);
  const h=CONTENT_HEADERS;
  ensureHeaders_(sh,h);
  sh.setFrozenRows(1);
  sh.getRange(1,1,1,h.length).setFontWeight("bold");
  return sh;
}

function col_(name){return HEADERS.indexOf(name)+1;}
function now_(){return new Date();}
function json_(o){return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON);}
function auth_(body){
  const expected=PropertiesService.getScriptProperties().getProperty("WEBHOOK_TOKEN");
  return Boolean(expected&&body&&body.token===expected);
}
function ownerEmail_(){return String(Session.getEffectiveUser().getEmail()||"").toLowerCase();}

function waLink_(business,email){
  const number=String(PropertiesService.getScriptProperties().getProperty("WA_NUMBER")||"").replace(/\D/g,"");
  if(!number)return "";
  const text="Halo Rey, saya dari "+business+". Saya membalas email tentang kebutuhan bisnis kami. Email: "+email;
  return "https://wa.me/"+number+"?text="+encodeURIComponent(text);
}

function onOpen(){
  SpreadsheetApp.getUi().createMenu("Sonjaya")
    .addItem("Kirim Lead Terpilih","sendSelectedRows_")
    .addItem("Pasang Kontrol Manual Send","setup")
    .addToUi();
}

function onEdit(e){
  try{
    if(!e||!e.range)return;
    const sh=e.range.getSheet();
    if(sh.getName()!==SHEET_NAME)return;
    const manualCol=col_("Manual Send");
    if(manualCol<1||e.range.getColumn()>manualCol||e.range.getLastColumn()<manualCol)return;
    if(String(e.value||"").toUpperCase()!=="TRUE")return;
    for(let row=e.range.getRow();row<=e.range.getLastRow();row++)sendOneRow_(row);
  }catch(err){console.log(err);}
}

function scheduleAfterManualSend_(rowNum,first){
  const sh=sheet_();
  sh.getRange(rowNum,col_("Sent At")).setValue(first);
  sh.getRange(rowNum,col_("Follow-up 1 At")).setValue(new Date(first.getTime()+2*86400000));
  sh.getRange(rowNum,col_("Follow-up 2 At")).setValue(new Date(first.getTime()+5*86400000));
  sh.getRange(rowNum,col_("Follow-up 3 At")).setValue(new Date(first.getTime()+9*86400000));
}

function sendOneRow_(rowNum){
  const lock=LockService.getDocumentLock();
  lock.waitLock(15000);
  try{
    const sh=sheet_();
    if(rowNum<2||rowNum>sh.getLastRow())return {ok:false,error:"Invalid row"};
    const email=String(sh.getRange(rowNum,col_("Email")).getValue()||"").trim();
    const subject=String(sh.getRange(rowNum,col_("Subject")).getValue()||"").trim();
    const body=String(sh.getRange(rowNum,col_("Body")).getValue()||"").trim();
    const opt=String(sh.getRange(rowNum,col_("Opt Out")).getValue()||"").toUpperCase().trim();
    const status=String(sh.getRange(rowNum,col_("Status")).getValue()||"").toUpperCase().trim();
    if(opt==="YES")throw new Error("OPT_OUT");
    if(["SENT","FOLLOWUP_1","FOLLOWUP_2","FOLLOWUP_3","FOLLOWUP_DONE","REPLIED","WA_HANDOFF"].indexOf(status)>=0){
      sh.getRange(rowNum,col_(MANUAL_SEND_COL)).setValue(false);
      return {ok:false,error:"Already sent or handled"};
    }
    if(!email||!subject||!body)throw new Error("Email, Subject, dan Body wajib terisi sebelum kirim.");
    MailApp.sendEmail({to:email,subject:subject,body:body,name:AGENCY_NAME,replyTo:ownerEmail_()});
    const first=now_();
    sh.getRange(rowNum,col_("Status")).setValue("SENT");
    scheduleAfterManualSend_(rowNum,first);
    sh.getRange(rowNum,col_("Last Error")).clearContent();
    sh.getRange(rowNum,col_(MANUAL_SEND_COL)).setValue(false);
    sh.getRange(rowNum,col_(SEND_RESULT_COL)).setValue("SENT "+Utilities.formatDate(first,"Asia/Jakarta","yyyy-MM-dd HH:mm:ss"));
    return {ok:true,row:rowNum,email:email};
  }catch(err){
    const sh=sheet_();
    const attemptsCell=sh.getRange(rowNum,col_("Attempts")), attempts=Number(attemptsCell.getValue()||0)+1;
    attemptsCell.setValue(attempts);
    sh.getRange(rowNum,col_("Status")).setValue(attempts>=MAX_ATTEMPTS?"FAILED":"ERROR");
    sh.getRange(rowNum,col_("Last Error")).setValue(String(err).slice(0,1000));
    sh.getRange(rowNum,col_(MANUAL_SEND_COL)).setValue(false);
    sh.getRange(rowNum,col_(SEND_RESULT_COL)).setValue("ERROR: "+String(err).slice(0,500));
    return {ok:false,row:rowNum,error:String(err)};
  }finally{
    try{lock.releaseLock();}catch(e){}
  }
}

function sendSelectedRows_(){
  const sh=sheet_(),range=sh.getActiveRange();
  if(!range)return;
  const results=[];
  for(let row=range.getRow();row<=range.getLastRow();row++)results.push(sendOneRow_(row));
  const ok=results.filter(r=>r&&r.ok).length;
  SpreadsheetApp.getUi().alert(ok+" lead berhasil dikirim. Lead lain yang belum lengkap/tidak eligible tidak dikirim.");
}

function doGet(e){
  const p=(e&&e.parameter)||{};
  const verify=PropertiesService.getScriptProperties().getProperty("META_VERIFY_TOKEN")||"";
  if(p["hub.mode"]==="subscribe" && p["hub.verify_token"]===verify && p["hub.challenge"]){
    return ContentService.createTextOutput(p["hub.challenge"]);
  }
  return json_({ok:true,service:"Sonjaya Remote Agency",status:"running"});
}

function doPost(e){
  try{
    const body=JSON.parse((e.postData&&e.postData.contents)||"{}");
    if(body && body.object==="instagram")return handleInstagramWebhook_(body);
    if(!auth_(body))return json_({ok:false,error:"Unauthorized"});
    const a=body.action||"ingest";
    if(a==="ingest")return ingest_(body.rows||[]);
    if(a==="send_queue")return sendQueue_(Number(body.limit||DAILY_SEND_LIMIT));
    if(a==="scan_replies")return scanReplies_(Number(body.limit||20));
    if(a==="process_followups")return processFollowups_(Number(body.limit||MAX_FOLLOWUPS_PER_RUN));
    if(a==="mark_error")return markError_(String(body.id||""),String(body.error||""));
    if(a==="content_ingest")return ingestContent_(body.rows||[]);
    if(a==="publish_social")return publishSocial_(body);
    return json_({ok:false,error:"Unknown action"});
  }catch(err){return json_({ok:false,error:String(err)});}
}

function ingest_(rows){
  const sh=sheet_(), existing={};
  if(sh.getLastRow()>=2){
    sh.getRange(2,col_("Email"),sh.getLastRow()-1,1).getValues().forEach(function(r){
      const e=String(r[0]||"").toLowerCase().trim(); if(e)existing[e]=true;
    });
  }
  let added=0,duplicates=0,noEmail=0;
  rows.forEach(function(row){
    const email=String(row.recipient_email||"").toLowerCase().trim();
    if(!email||email.indexOf("@")===-1){noEmail++;return;}
    if(existing[email]){duplicates++;return;}
    const o=new Array(HEADERS.length).fill("");
    const set=(h,v)=>{const c=col_(h);if(c>0)o[c-1]=v==null?"":v;};
    const score=Number(row.skor||0);
    set("Lead ID",row.lead_id||Utilities.getUuid().replace(/-/g,"").slice(0,12));
    set("Tanggal ditemukan",row.tanggal_ditemukan||Utilities.formatDate(now_(),"Asia/Jakarta","yyyy-MM-dd HH:mm:ss"));
    set("Nama bisnis",row.nama_bisnis); set("Email",email); set("Sumber email",row.email_source_url);
    set("Website",row.website_url); set("Social",row.social_url); set("Kota",row.kota); set("Kategori",row.kategori);
    set("Bukti publik",row.bukti_publik); set("Skor",score); set("Prioritas",score>=85?"A":score>=75?"B":"C");
    set("Kebutuhan terdeteksi",row.detected_need); set("Layanan direkomendasikan",row.recommended_service);
    set("Pain point",row.pain_point); set("Hook personal",row.alasan);
    set("Subject",row.subject); set("Body",row.body); set("Status",row.status||"REVIEW");
    set("Opt Out","NO"); set("Attempts",0); set("Catatan",row.catatan);
    set("Manual Send",false); set("Send Result","WAITING_FOR_MANUAL_SEND");
    sh.appendRow(o);
    const newRow=sh.getLastRow();
    sh.getRange(newRow,col_("Manual Send"))
      .setDataValidation(SpreadsheetApp.newDataValidation().requireCheckbox().build())
      .setValue(false);
    existing[email]=true; added++;
  });
  return json_({ok:true,received:rows.length,added:added,duplicates:duplicates,no_email:noEmail});
}

function findRowById_(id){
  const sh=sheet_(); if(sh.getLastRow()<2)return -1;
  const v=sh.getRange(2,col_("Lead ID"),sh.getLastRow()-1,1).getValues();
  for(let i=0;i<v.length;i++)if(String(v[i][0]||"")===id)return i+2;
  return -1;
}

function markError_(id,error){
  if(!id)return json_({ok:false,error:"Missing id"});
  const sh=sheet_(),row=findRowById_(id);
  if(row<2)return json_({ok:false,error:"Lead ID not found"});
  const c=sh.getRange(row,col_("Attempts")),n=Number(c.getValue()||0)+1;
  c.setValue(n);
  sh.getRange(row,col_("Status")).setValue(n>=MAX_ATTEMPTS?"FAILED":"ERROR");
  sh.getRange(row,col_("Last Error")).setValue(String(error||"Unknown error").slice(0,1000));
  return json_({ok:true,id:id,attempts:n});
}

function outboundToday_(values,idx){
  const today=Utilities.formatDate(now_(),"Asia/Jakarta","yyyy-MM-dd");
  let n=0;
  values.forEach(function(r){
    ["Sent At","Follow-up 1 At","Follow-up 2 At","Follow-up 3 At"].forEach(function(h){
      const v=String(r[idx[h]]||"");
      if(v.indexOf(today)===0)n++;
    });
  });
  return n;
}

function sendQueue_(limit){
  return json_({ok:true,auto_send:false,sent:0,message:"Automatic initial email sending is disabled. Use Manual Send in the Prospects sheet."});
}

function findThreadByLeadId_(id){
  const threads=GmailApp.search('subject:"[SJ-'+id+']"',0,10);
  return threads.length?threads[0]:null;
}

function sendFollowupMessage_(leadId,email,subject,body){
  const thread=findThreadByLeadId_(leadId);
  if(thread){
    thread.reply(body,{name:AGENCY_NAME});
    return "THREAD";
  }
  MailApp.sendEmail({to:email,subject:subject,body:body,name:AGENCY_NAME,replyTo:ownerEmail_()});
  return "NEW_MESSAGE";
}

function followupBody_(business,service,pain,stage){
  const serviceText=service||"pekerjaan remote";
  if(stage===1){
    return "Halo tim "+business+",\n\nSaya follow up singkat soal email saya sebelumnya. Saya melihat ada peluang terkait "+serviceText+(pain?" — khususnya "+pain+".":".")+"\n\nKalau ini memang sedang dibutuhkan, saya bisa kirim contoh alur kerja yang sederhana dan bisa dikerjakan remote.\n\nSalam,\nRey\n"+AGENCY_NAME;
  }
  if(stage===2){
    return "Halo tim "+business+",\n\nSaya ingin memastikan email sebelumnya tidak terlewat. Untuk "+business+", saya mengusulkan bantuan remote di area "+serviceText+". Tidak perlu komitmen panjang; kita bisa mulai dari tugas yang paling mendesak.\n\nKalau relevan, cukup balas email ini dan saya kirim detailnya.\n\nSalam,\nRey\n"+AGENCY_NAME;
  }
  return "Halo tim "+business+",\n\nIni follow up terakhir saya terkait bantuan remote "+serviceText+". Saya tidak akan mengirim follow up lagi setelah ini. Kalau kebutuhan tersebut muncul di kemudian hari, cukup balas email ini.\n\nTerima kasih,\nRey\n"+AGENCY_NAME;
}

function processFollowups_(limit){
  const sh=sheet_(),last=sh.getLastRow();
  if(last<2)return json_({ok:true,processed:0});
  const values=sh.getRange(2,1,last-1,HEADERS.length).getValues();
  const idx={}; HEADERS.forEach(function(h,i){idx[h]=i;});
  const sentToday=outboundToday_(values,idx);
  let remaining=Math.max(0,Math.min(MailApp.getRemainingDailyQuota(),DAILY_SEND_LIMIT-sentToday));
  const now=now_(); let processed=0;
  const maxItems=Math.min(Math.max(1,limit||MAX_FOLLOWUPS_PER_RUN),remaining);
  for(let i=0;i<values.length&&processed<maxItems;i++){
    const r=values[i];
    const status=String(r[idx["Status"]]||"").toUpperCase().trim();
    const opt=String(r[idx["Opt Out"]]||"").toUpperCase().trim();
    if(opt==="YES"||["READY","REPLIED","WA_HANDOFF","OPTOUT","ERROR","FAILED","FOLLOWUP_DONE"].indexOf(status)>=0)continue;

    let stage=0,due=null,nextStatus="",timeCol="";
    if(status==="SENT"){stage=1;due=r[idx["Follow-up 1 At"]];nextStatus="FOLLOWUP_1";timeCol="Follow-up 1 At";}
    else if(status==="FOLLOWUP_1"){stage=2;due=r[idx["Follow-up 2 At"]];nextStatus="FOLLOWUP_2";timeCol="Follow-up 2 At";}
    else if(status==="FOLLOWUP_2"){stage=3;due=r[idx["Follow-up 3 At"]];nextStatus="FOLLOWUP_3";timeCol="Follow-up 3 At";}
    else continue;

    if(!(due instanceof Date)){due=new Date(String(due||""));} 
    if(isNaN(due.getTime())||due.getTime()>now.getTime())continue;

    const leadId=String(r[idx["Lead ID"]]||""),email=String(r[idx["Email"]]||"").trim(),subject=String(r[idx["Subject"]]||"").trim();
    if(!leadId||!email||!subject)continue;
    const business=String(r[idx["Nama bisnis"]]||"Perusahaan");
    const service=String(r[idx["Layanan direkomendasikan"]]||"pekerjaan remote");
    const pain=String(r[idx["Pain point"]]||"");
    const body=followupBody_(business,service,pain,stage);
    try{
      sendFollowupMessage_(leadId,email,subject,body);
      const rowNum=i+2;
      sh.getRange(rowNum,col_("Status")).setValue(stage===3?"FOLLOWUP_DONE":nextStatus);
      sh.getRange(rowNum,col_(timeCol)).setValue(now);
      sh.getRange(rowNum,col_("Last Error")).clearContent();
      processed++; remaining--;
    }catch(err){
      markError_(leadId,String(err));
    }
  }
  return json_({ok:true,processed:processed,sent_today:sentToday+processed,remaining:remaining});
}

function scanReplies_(limit){
  const sh=sheet_(),last=sh.getLastRow();
  if(last<2)return json_({ok:true,replied:0});
  const threads=GmailApp.search("in:inbox newer_than:7d -from:me",0,100);
  const owner=ownerEmail_();let replied=0;
  for(let ti=0;ti<threads.length&&replied<limit;ti++){
    const thread=threads[ti],subject=String(thread.getFirstMessageSubject()||"");
    const m=subject.match(/\[SJ-([a-f0-9]{12})\]/i); if(!m)continue;
    const row=findRowById_(m[1]); if(row<2)continue;
    const status=String(sh.getRange(row,col_("Status")).getValue()||"").toUpperCase();
    if(["WA_HANDOFF","OPTOUT"].indexOf(status)>=0)continue;

    const msgs=thread.getMessages();let inbound=null;
    for(let i=msgs.length-1;i>=0;i--){
      const from=String(msgs[i].getFrom()||"").toLowerCase();
      if(owner && from.indexOf(owner)===-1){inbound=msgs[i];break;}
    }
    if(!inbound)continue;

    const body=String(inbound.getPlainBody()||"").slice(0,5000),upper=body.toUpperCase();
    if(upper.indexOf("UNSUBSCRIBE")!==-1){
      sh.getRange(row,col_("Status")).setValue("OPTOUT");
      sh.getRange(row,col_("Opt Out")).setValue("YES");
      continue;
    }

    const business=String(sh.getRange(row,col_("Nama bisnis")).getValue()||"Perusahaan");
    const email=String(sh.getRange(row,col_("Email")).getValue()||"");
    const intent=/harga|price|biaya|cost|tertarik|minat|interested|bisa|boleh|minta|info|detail|contoh|diskusi|call|meeting|whatsapp|wa\b/i.test(body)?"INTERESTED":"REPLIED";
    const wa=waLink_(business,email);
    const replyText=wa
      ? "Terima kasih sudah membalas. Agar lebih cepat, kita bisa lanjut ke WhatsApp untuk membahas kebutuhan yang paling sesuai.\n\nWhatsApp: "+wa+"\n\nSalam,\nRey\n"+AGENCY_NAME
      : "Terima kasih sudah membalas. Saya akan menindaklanjuti kebutuhan Anda melalui email ini.\n\nSalam,\nRey\n"+AGENCY_NAME;
    try{thread.reply(replyText,{name:AGENCY_NAME});}catch(e){continue;}
    sh.getRange(row,col_("Status")).setValue(wa?"WA_HANDOFF":"REPLIED");
    sh.getRange(row,col_("Reply At")).setValue(now_());
    sh.getRange(row,col_("Reply Intent")).setValue(intent);
    sh.getRange(row,col_("Last Reply")).setValue(body.slice(0,1500));
    sh.getRange(row,col_("WhatsApp Handoff")).setValue(wa);
    replied++;
  }
  return json_({ok:true,replied:replied});
}

function ingestContent_(rows){
  const planningRows=rows.filter(function(r){return String(r.publish_mode||"") === "PLANNING_ONLY";});
  const legacyRows=rows.filter(function(r){return String(r.publish_mode||"") !== "PLANNING_ONLY";});
  let addedPlanning=0,addedLegacy=0;

  if(planningRows.length){
    const sh=contentPlanningSheet_(), existing={};
    if(sh.getLastRow()>=2){
      const all=sh.getRange(2,1,sh.getLastRow()-1,2).getValues();
      all.forEach(function(r){existing[String(r[0])+"|"+String(r[1])]=true;});
    }
    planningRows.forEach(function(r){
      const key=String(r.date)+"|"+String(r.platform);
      if(existing[key])return;
      sh.appendRow([
        r.date,r.platform,r.format||"CAROUSEL_7_SLIDES",r.objective||"",
        r.topic||"",r.hook||"",r.caption||"",r.cta||"",
        Number(r.slide_count||7),r.carousel_pdf_url||"",r.carousel_cover_url||"",
        r.slides_json||"",r.status||"PLANNED","PLANNING_ONLY",
        r.catatan||"Tidak diupload otomatis"
      ]);
      existing[key]=true; addedPlanning++;
    });
  }

  if(legacyRows.length){
    const sh=contentSheet_(), existing={};
    if(sh.getLastRow()>=2){
      const all=sh.getRange(2,1,sh.getLastRow()-1,4).getValues();
      all.forEach(function(r){existing[String(r[0])+"|"+String(r[1])+"|"+String(r[3])]=true;});
    }
    legacyRows.forEach(function(r){
      const key=String(r.date)+"|"+String(r.platform)+"|"+String(r.topic);
      if(existing[key])return;
      sh.appendRow([
        r.date,r.platform,r.format,r.topic,r.hook,r.caption,r.cta,r.visual_prompt,
        r.asset_url||"",r.status||"PLANNED",r.publish_result||"NOT_UPLOADED"
      ]);
      existing[key]=true;addedLegacy++;
    });
  }

  return json_({ok:true,added_planning:addedPlanning,added_legacy:addedLegacy});
}

function urlFetchJson_(url,options){
  const res=UrlFetchApp.fetch(url,options||{muteHttpExceptions:true});
  const code=res.getResponseCode(),txt=res.getContentText();
  let data={};
  try{data=JSON.parse(txt||"{}");}catch(e){data={raw:txt};}
  if(code<200||code>=300)throw new Error("HTTP "+code+": "+txt.slice(0,1000));
  return data;
}

function publishInstagramPhoto_(imageUrl,caption){
  const token=PropertiesService.getScriptProperties().getProperty("IG_ACCESS_TOKEN")||"";
  const userId=PropertiesService.getScriptProperties().getProperty("IG_USER_ID")||"";
  const version=PropertiesService.getScriptProperties().getProperty("IG_API_VERSION")||"v26.0";
  if(!token||!userId)return {ok:false,error:"INSTAGRAM_NOT_CONFIGURED"};
  const base="https://graph.facebook.com/"+version+"/"+encodeURIComponent(userId);
  const container=urlFetchJson_(base+"/media?image_url="+encodeURIComponent(imageUrl)+"&caption="+encodeURIComponent(caption||"")+"&access_token="+encodeURIComponent(token),{method:"post",muteHttpExceptions:true});
  const creationId=container.id;
  if(!creationId)return {ok:false,error:"Instagram container not created"};
  Utilities.sleep(5000);
  const published=urlFetchJson_(base+"/media_publish?creation_id="+encodeURIComponent(creationId)+"&access_token="+encodeURIComponent(token),{method:"post",muteHttpExceptions:true});
  return {ok:true,platform:"instagram",id:published.id||creationId};
}

function refreshTikTok_(){
  const key=PropertiesService.getScriptProperties().getProperty("TIKTOK_CLIENT_KEY")||"";
  const secret=PropertiesService.getScriptProperties().getProperty("TIKTOK_CLIENT_SECRET")||"";
  const refresh=PropertiesService.getScriptProperties().getProperty("TIKTOK_REFRESH_TOKEN")||"";
  if(!key||!secret||!refresh)throw new Error("TIKTOK_REFRESH_NOT_CONFIGURED");
  const res=UrlFetchApp.fetch("https://open.tiktokapis.com/v2/oauth/token/",{
    method:"post",contentType:"application/x-www-form-urlencoded",
    payload:{client_key:key,client_secret:secret,grant_type:"refresh_token",refresh_token:refresh},
    muteHttpExceptions:true
  });
  const code=res.getResponseCode(),txt=res.getContentText();let data={};
  try{data=JSON.parse(txt||"{}");}catch(e){}
  if(code<200||code>=300||!data.access_token)throw new Error("TikTok refresh HTTP "+code+": "+txt.slice(0,500));
  PropertiesService.getScriptProperties().setProperty("TIKTOK_ACCESS_TOKEN",data.access_token);
  if(data.refresh_token)PropertiesService.getScriptProperties().setProperty("TIKTOK_REFRESH_TOKEN",data.refresh_token);
  return data.access_token;
}

function publishTikTokPhoto_(imageUrl,caption){
  let token=PropertiesService.getScriptProperties().getProperty("TIKTOK_ACCESS_TOKEN")||"";
  if(!token){
    try{token=refreshTikTok_();}catch(e){return {ok:false,error:String(e)};}
  }

  let creator;
  try{
    creator=urlFetchJson_("https://open.tiktokapis.com/v2/post/publish/creator_info/query/",{
      method:"post",contentType:"application/json",headers:{Authorization:"Bearer "+token},
      payload:"{}",muteHttpExceptions:true
    });
  }catch(e){
    try{
      token=refreshTikTok_();
      creator=urlFetchJson_("https://open.tiktokapis.com/v2/post/publish/creator_info/query/",{
        method:"post",contentType:"application/json",headers:{Authorization:"Bearer "+token},
        payload:"{}",muteHttpExceptions:true
      });
    }catch(err){return {ok:false,error:String(err)};}
  }

  const options=((creator.data&&creator.data.privacy_level_options)||[]);
  const privacy=options.indexOf("PUBLIC_TO_EVERYONE")>=0
    ? "PUBLIC_TO_EVERYONE"
    : (options[0]||"SELF_ONLY");

  const initPayload={
    post_info:{
      description:String(caption||"").slice(0,2200),
      privacy_level:privacy,
      auto_add_music:false,
      brand_organic_toggle:true,
      is_aigc:true
    },
    source_info:{source:"PULL_FROM_URL",photo_images:[imageUrl],photo_cover_index:0},
    post_mode:"DIRECT_POST",
    media_type:"PHOTO"
  };

  let result;
  try{
    result=urlFetchJson_("https://open.tiktokapis.com/v2/post/publish/content/init/",{
      method:"post",contentType:"application/json",headers:{Authorization:"Bearer "+token},
      payload:JSON.stringify(initPayload),muteHttpExceptions:true
    });
  }catch(e){
    try{
      token=refreshTikTok_();
      creator=urlFetchJson_("https://open.tiktokapis.com/v2/post/publish/creator_info/query/",{
        method:"post",contentType:"application/json",headers:{Authorization:"Bearer "+token},
        payload:"{}",muteHttpExceptions:true
      });
      const refreshedOptions=((creator.data&&creator.data.privacy_level_options)||[]);
      initPayload.post_info.privacy_level=refreshedOptions.indexOf("PUBLIC_TO_EVERYONE")>=0
        ? "PUBLIC_TO_EVERYONE" : (refreshedOptions[0]||"SELF_ONLY");
      result=urlFetchJson_("https://open.tiktokapis.com/v2/post/publish/content/init/",{
        method:"post",contentType:"application/json",headers:{Authorization:"Bearer "+token},
        payload:JSON.stringify(initPayload),muteHttpExceptions:true
      });
    }catch(err){return {ok:false,error:String(err)};}
  }

  if(result.error && result.error.code && result.error.code!=="ok"){
    return {ok:false,error:JSON.stringify(result.error)};
  }
  return {
    ok:true,
    platform:"tiktok",
    publish_id:result.data&&result.data.publish_id?result.data.publish_id:""
  };
}

function publishSocial_(body){
  const platform=String(body.platform||"").toLowerCase();
  const imageUrl=String(body.image_url||"").trim();
  const caption=String(body.caption||"").trim();
  if(!imageUrl)return json_({ok:false,error:"Missing image_url"});
  let result;
  if(platform==="instagram")result=publishInstagramPhoto_(imageUrl,caption);
  else if(platform==="tiktok")result=publishTikTokPhoto_(imageUrl,caption);
  else return json_({ok:false,error:"Unsupported platform"});
  return json_(result);
}

function markContentPublished_(date,platform,result){
  const sh=contentSheet_(),last=sh.getLastRow();
  if(last<2)return;
  const vals=sh.getRange(2,1,last-1,11).getValues();
  for(let i=0;i<vals.length;i++){
    if(String(vals[i][0])===String(date)&&String(vals[i][1]).toLowerCase()===String(platform).toLowerCase()){
      sh.getRange(i+2,10).setValue(result.ok?"PUBLISHED":"PUBLISH_ERROR");
      sh.getRange(i+2,11).setValue(JSON.stringify(result));
    }
  }
}

function setup(){
  sheet_();contentSheet_();contentPlanningSheet_();socialLeadsSheet_();
  const triggers=ScriptApp.getProjectTriggers();
  if(!triggers.some(t=>t.getHandlerFunction()==="hourlyAutomation_")){
    ScriptApp.newTrigger("hourlyAutomation_").timeBased().everyHours(1).create();
  }
  return "Sonjaya system ready";
}

function hourlyAutomation_(){
  try{scanReplies_(20);}catch(e){console.log(e);}
  try{processFollowups_(MAX_FOLLOWUPS_PER_RUN);}catch(e){console.log(e);}
}
