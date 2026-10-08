const SHEET_NAME = "Prospects";
const CONTENT_SHEET = "Content";
const CONTENT_PLAN_SHEET = "Content Planning";
const MAX_ATTEMPTS = 3;
const DAILY_SEND_LIMIT = 20;
const MAX_FOLLOWUPS_PER_RUN = 10;
const BATCH_SEND_LIMIT = 30;
const MAX_DAILY_AUTOMATED_SENDS = 360;
const AGENCY_NAME = "Sonjaya Remote Business Services";
const MANUAL_SEND_COL = "Manual Send";
const SEND_RESULT_COL = "Send Result";
const CONTENT_HEADERS = ["Tanggal","Platform","Format","Topik","Hook","Caption","CTA","Visual Prompt","Asset URL","Status","Publish Result"];
const CONTENT_PLAN_HEADERS = ["Tanggal","Platform","Format","Tujuan","Topik","Hook","Caption","CTA","Slide Count","Carousel PDF URL","Carousel Cover URL","Slides JSON","Status","Publish Mode","Catatan","Pilar Konten","Script Lengkap","Slide 1 URL","Slide 2 URL","Slide 3 URL","Slide 4 URL","Slide 5 URL","Slide 6 URL","Slide 7 URL","Slide 1 Preview","Slide 2 Preview","Slide 3 Preview","Slide 4 Preview","Slide 5 Preview","Slide 6 Preview","Slide 7 Preview"];
const AUTOMATION_LOG_SHEET = "Automation Log";
const AUTOMATION_LOG_HEADERS = ["Tanggal","Cycle","Initial Sent","Follow-ups Sent","Replies Processed","Errors","Quota Before","Quota After","Status","Detail"];
const SOCIAL_LEADS_HEADERS = ["Tanggal","Platform","Keyword","Username","User ID","Comment ID","Comment","Post ID","DM Status","WhatsApp Link","Catatan"];
const CODE_VERSION = "2026-10-08.1";
// Production social automation handlers are enabled in this version.

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
  backfillProspectControls_(sh);
  return sh;
}

function prospectDataLastRow_(sh){
  const emailCol=col_("Email"), leadIdCol=col_("Lead ID");
  const max=sh.getMaxRows();
  if(max<2)return 1;
  const emails=sh.getRange(2,emailCol,max-1,1).getValues();
  const ids=sh.getRange(2,leadIdCol,max-1,1).getValues();
  for(let i=max-2;i>=0;i--){
    if(String(emails[i][0]||"").trim() || String(ids[i][0]||"").trim())return i+2;
  }
  return 1;
}

function backfillProspectControls_(sh){
  const last=prospectDataLastRow_(sh);
  if(last<2)return;
  const n=last-1, manualCol=col_("Manual Send"), resultCol=col_(SEND_RESULT_COL), statusCol=col_("Status");
  const statuses=sh.getRange(2,statusCol,n,1).getValues();
  const manual=sh.getRange(2,manualCol,n,1).getValues();
  const results=sh.getRange(2,resultCol,n,1).getValues();
  const handled=["SENT","FOLLOWUP_1","FOLLOWUP_2","FOLLOWUP_3","FOLLOWUP_DONE","REPLIED","WA_HANDOFF","OPTOUT"];
  const manualOut=manual.map((r)=>[r[0]==="" || r[0]===null ? false : r[0]]);
  const resultOut=results.map((r,i)=>{
    if(r[0]!=="" && r[0]!==null)return [r[0]];
    const st=String(statuses[i][0]||"").toUpperCase().trim();
    return [handled.indexOf(st)>=0 ? "LEGACY_EXISTING_STATE" : "WAITING_FOR_MANUAL_SEND"];
  });
  if(JSON.stringify(manualOut)!==JSON.stringify(manual))sh.getRange(2,manualCol,n,1).setValues(manualOut);
  if(JSON.stringify(resultOut)!==JSON.stringify(results))sh.getRange(2,resultCol,n,1).setValues(resultOut);

  // Remove only automation-control residue below the last real lead.
  // Business/lead columns are never touched.
  const extraStart=last+1, extraCount=sh.getMaxRows()-last;
  if(extraCount>0){
    sh.getRange(extraStart,manualCol,extraCount,1).clearContent();
    sh.getRange(extraStart,resultCol,extraCount,1).clearContent();
  }
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
  const last=prospectDataLastRow_(sh);
  const rows=Math.max(1,last-1);
  sh.getRange(2,manualCol,rows,1)
    .setDataValidation(SpreadsheetApp.newDataValidation().requireCheckbox().build())
    .setHorizontalAlignment("center");
  const statusCol=col_("Status");
  if(statusCol>0){
    sh.getRange(2,statusCol,rows,1).setDataValidation(
      SpreadsheetApp.newDataValidation().requireValueInList(
        ["READY","REVIEW","MANUAL_SEND","SENT","FOLLOWUP_1","FOLLOWUP_2","FOLLOWUP_3","FOLLOWUP_DONE","REPLIED","WA_HANDOFF","OPTOUT","ERROR","FAILED"], true
      ).build()
    );
  }
}

function automationLogSheet_(){
  const ss=SpreadsheetApp.getActiveSpreadsheet();
  let sh=ss.getSheetByName(AUTOMATION_LOG_SHEET);
  if(!sh)sh=ss.insertSheet(AUTOMATION_LOG_SHEET);
  ensureHeaders_(sh,AUTOMATION_LOG_HEADERS);
  sh.setFrozenRows(1);
  sh.getRange(1,1,1,AUTOMATION_LOG_HEADERS.length).setFontWeight("bold");
  sh.getDataRange().setWrap(true);
  sh.setColumnWidth(1,145);
  sh.setColumnWidth(2,150);
  sh.setColumnWidth(3,105);
  sh.setColumnWidth(4,120);
  sh.setColumnWidth(5,120);
  sh.setColumnWidth(6,90);
  sh.setColumnWidth(7,105);
  sh.setColumnWidth(8,105);
  sh.setColumnWidth(9,100);
  sh.setColumnWidth(10,520);
  return sh;
}

function contentPlanningSheet_(){
  const ss=SpreadsheetApp.getActiveSpreadsheet();
  let sh=ss.getSheetByName(CONTENT_PLAN_SHEET);
  if(!sh)sh=ss.insertSheet(CONTENT_PLAN_SHEET);
  ensureHeaders_(sh,CONTENT_PLAN_HEADERS);
  sh.setFrozenRows(1);
  sh.getRange(1,1,1,CONTENT_PLAN_HEADERS.length).setFontWeight("bold");
  sh.getDataRange().setWrap(true);
  sh.setColumnWidth(1,105);
  sh.setColumnWidth(2,95);
  sh.setColumnWidth(3,135);
  sh.setColumnWidth(4,180);
  sh.setColumnWidth(5,260);
  sh.setColumnWidth(6,300);
  sh.setColumnWidth(7,420);
  sh.setColumnWidth(8,260);
  sh.setColumnWidth(10,230);
  sh.setColumnWidth(11,230);
  sh.setColumnWidth(16,220);
  sh.setColumnWidth(17,520);
  for(let col=18;col<=24;col++)sh.setColumnWidth(col,230);
  for(let col=25;col<=31;col++)sh.setColumnWidth(col,180);
  if(sh.getLastRow()>=2){
    sh.setRowHeights(2,sh.getLastRow()-1,180);
  }
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

function onOpen(){
  SpreadsheetApp.getUi().createMenu("Sonjaya")
    .addItem("Status Sistem","systemStatus")
    .addItem("Jalankan Sales Cycle Sekarang","salesAutomation_")
    .addItem("Pasang Automation 2 Jam","setup")
    .addToUi();
}

function manualSendOnEdit_(e){
  try{
    if(!e||!e.range)return;
    const sh=e.range.getSheet();
    if(sh.getName()!==SHEET_NAME)return;
    const manualCol=col_("Manual Send");
    const statusCol=col_("Status");
    const editedCol=e.range.getColumn();
    const value=String(e.value||"").toUpperCase().trim();
    const viaCheckbox=(editedCol===manualCol && value==="TRUE");
    const viaStatus=(editedCol===statusCol && value==="MANUAL_SEND");
    if(!viaCheckbox && !viaStatus)return;
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
    const taggedSubject="[SJ-"+String(sh.getRange(rowNum,col_("Lead ID")).getValue()||"")+"] "+subject;
    MailApp.sendEmail({to:email,subject:taggedSubject,body:body,name:AGENCY_NAME,replyTo:ownerEmail_()});
    sh.getRange(rowNum,col_("Subject")).setValue(taggedSubject);
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
  if(String(p.check||"").toLowerCase()==="health")return liveHealth_();
  return json_({ok:true,service:"Sonjaya Remote Agency",status:"running",flows:["sales","content"]});
}

function liveHealth_(){
  const props=PropertiesService.getScriptProperties();
  const handlers=ScriptApp.getProjectTriggers().map(function(t){return t.getHandlerFunction();});
  const ss=SpreadsheetApp.getActiveSpreadsheet();
  const names=ss.getSheets().map(function(s){return s.getName();});
  let quota=0; try{quota=MailApp.getRemainingDailyQuota();}catch(e){}
  return json_({
    ok:true,
    service:"Sonjaya Remote Agency",
    version:CODE_VERSION,
    flows:{sales:true,content:true,social_automation:false,social_auto_publish:false},
    sheets:{
      prospects:names.indexOf(SHEET_NAME)>=0,
      content_planning:names.indexOf(CONTENT_PLAN_SHEET)>=0,
      content:names.indexOf(CONTENT_SHEET)>=0,
      automation_log:names.indexOf(AUTOMATION_LOG_SHEET)>=0
    },
    properties:{
      webhook_token:Boolean(props.getProperty("WEBHOOK_TOKEN")),
      wa_number:Boolean(props.getProperty("WA_NUMBER")),
      gemini_api_key:Boolean(props.getProperty("GEMINI_API_KEY"))
    },
    email:{remaining_daily_quota:quota,batch_target:BATCH_SEND_LIMIT,max_daily_target:MAX_DAILY_AUTOMATED_SENDS},
    triggers:{
      githubSalesScheduler:true,
      legacyHourly:handlers.indexOf("hourlyAutomation_")>=0,
      legacyManualSend:handlers.indexOf("manualSendOnEdit_")>=0,
      legacySalesTrigger:handlers.indexOf("salesAutomation_")>=0
    }
  });
}

function doPost(e){
  try{
    const body=JSON.parse((e.postData&&e.postData.contents)||"{}");
    if(!auth_(body))return json_({ok:false,error:"Unauthorized"});
    const action=String(body.action||"healthcheck");
    if(action==="healthcheck")return liveHealth_();
    if(action==="ingest")return ingest_(body.rows||[]);
    if(action==="repair_layout")return repairProspectLayout_();
    if(action==="send_batch")return autoSendBatch_(Number(body.limit||BATCH_SEND_LIMIT));
    if(action==="send_queue")return autoSendBatch_(Number(body.limit||BATCH_SEND_LIMIT));
    if(action==="scan_replies")return scanReplies_(Number(body.limit||40));
    if(action==="process_followups")return processFollowups_(Number(body.limit||MAX_FOLLOWUPS_PER_RUN));
    if(action==="sales_cycle")return salesAutomation_();
    if(action==="setup_automation"){const message=setup();return json_({ok:true,message:message});}
    if(action==="mark_error")return markError_(String(body.id||""),String(body.error||""));
    if(action==="content_ingest")return ingestContent_(body.rows||[]);
    return json_({ok:false,error:"Unknown action"});
  }catch(err){return json_({ok:false,error:String(err)});}
}

function ingest_(rows){
  const sh=sheet_(), existing={};
  if(sh.getLastRow()>=2){
    sh.getRange(2,col_("Email"),sh.getLastRow()-1,1).getValues().forEach(function(r,i){
      const e=String(r[0]||"").toLowerCase().trim(); if(e)existing[e]=i+2;
    });
  }
  let added=0,duplicates=0,noEmail=0,promoted=0;
  const handled=["SENT","FOLLOWUP_1","FOLLOWUP_2","FOLLOWUP_3","FOLLOWUP_DONE","REPLIED","WA_HANDOFF","OPTOUT"];
  rows.forEach(function(row){
    const email=String(row.recipient_email||"").toLowerCase().trim();
    if(!email||email.indexOf("@")===-1){noEmail++;return;}
    const score=Number(row.skor||0);
    if(existing[email]){
      duplicates++;
      const rowNum=existing[email];
      const currentStatus=String(sh.getRange(rowNum,col_("Status")).getValue()||"").toUpperCase().trim();
      if(["","REVIEW"].indexOf(currentStatus)>=0 && score>=75){
        const setIfBlank=function(h,v){
          if(v==null||String(v).trim()==="")return;
          const cell=sh.getRange(rowNum,col_(h));
          if(String(cell.getValue()||"").trim()==="")cell.setValue(v);
        };
        setIfBlank("Nama bisnis",row.nama_bisnis); setIfBlank("Sumber email",row.email_source_url);
        setIfBlank("Website",row.website_url); setIfBlank("Social",row.social_url); setIfBlank("Kota",row.kota);
        setIfBlank("Kategori",row.kategori); setIfBlank("Bukti publik",row.bukti_publik); setIfBlank("Kebutuhan terdeteksi",row.detected_need);
        setIfBlank("Layanan direkomendasikan",row.recommended_service); setIfBlank("Pain point",row.pain_point);
        setIfBlank("Hook personal",row.alasan); setIfBlank("Subject",row.subject); setIfBlank("Body",row.body);
        sh.getRange(rowNum,col_("Skor")).setValue(Math.max(Number(sh.getRange(rowNum,col_("Skor")).getValue()||0),score));
        sh.getRange(rowNum,col_("Prioritas")).setValue(score>=85?"A":"B");
        sh.getRange(rowNum,col_("Status")).setValue("READY");
        sh.getRange(rowNum,col_("Last Error")).clearContent();
        sh.getRange(rowNum,col_("Attempts")).setValue(Number(sh.getRange(rowNum,col_("Attempts")).getValue()||0));
        promoted++;
      }
      return;
    }
    const o=new Array(HEADERS.length).fill("");
    const set=(h,v)=>{const c=col_(h);if(c>0)o[c-1]=v==null?"":v;};
    set("Lead ID",row.lead_id||Utilities.getUuid().replace(/-/g,"").slice(0,12));
    set("Tanggal ditemukan",row.tanggal_ditemukan||Utilities.formatDate(now_(),"Asia/Jakarta","yyyy-MM-dd HH:mm:ss"));
    set("Nama bisnis",row.nama_bisnis); set("Email",email); set("Sumber email",row.email_source_url);
    set("Website",row.website_url); set("Social",row.social_url); set("Kota",row.kota); set("Kategori",row.kategori);
    set("Bukti publik",row.bukti_publik); set("Skor",score); set("Prioritas",score>=85?"A":score>=75?"B":"C");
    set("Kebutuhan terdeteksi",row.detected_need); set("Layanan direkomendasikan",row.recommended_service);
    set("Pain point",row.pain_point); set("Hook personal",row.alasan); set("Subject",row.subject); set("Body",row.body);
    set("Status",row.status||"REVIEW"); set("Opt Out","NO"); set("Attempts",0); set("Catatan",row.catatan);
    set("Manual Send",false); set("Send Result","WAITING_FOR_AUTOMATIC_SEND");
    const newRow=prospectDataLastRow_(sh)+1;
    sh.getRange(newRow,1,1,HEADERS.length).setValues([o]);
    sh.getRange(newRow,col_("Manual Send"))
      .setDataValidation(SpreadsheetApp.newDataValidation().requireCheckbox().build())
      .setValue(false);
    existing[email]=newRow; added++;
  });
  return json_({ok:true,received:rows.length,added:added,duplicates:duplicates,promoted:promoted,no_email:noEmail});
}
function repairProspectLayout_(){
  const sh=sheet_();
  const last=prospectDataLastRow_(sh);
  const manualCol=col_("Manual Send"), resultCol=col_(SEND_RESULT_COL);
  const extraCount=Math.max(0,sh.getMaxRows()-last);
  if(extraCount>0){
    sh.getRange(last+1,manualCol,extraCount,1).clearContent();
    sh.getRange(last+1,resultCol,extraCount,1).clearContent();
  }
  configureProspectControls_(sh);
  backfillProspectControls_(sh);
  return json_({ok:true,data_last_row:last,controls_cleared_below:last});
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

function autoSendBatch_(limit){
  const sh=sheet_(),last=sh.getLastRow();
  const quota=Math.max(0,MailApp.getRemainingDailyQuota());
  if(last<2)return json_({ok:true,sent:0,errors:0,candidates:0,quota_before:quota,quota_after:quota});
  const values=sh.getRange(2,1,last-1,HEADERS.length).getValues();
  const idx={}; HEADERS.forEach(function(h,i){idx[h]=i;});
  const candidates=[];
  for(let i=0;i<values.length;i++){
    const r=values[i];
    const status=String(r[idx["Status"]]||"").toUpperCase().trim();
    const opt=String(r[idx["Opt Out"]]||"").toUpperCase().trim();
    const attempts=Number(r[idx["Attempts"]]||0);
    const email=String(r[idx["Email"]]||"").trim();
    const subject=String(r[idx["Subject"]]||"").trim();
    const body=String(r[idx["Body"]]||"").trim();
    if(status!=="READY"||opt==="YES"||attempts>=MAX_ATTEMPTS||!email||!subject||!body)continue;
    candidates.push({row:i+2,score:Number(r[idx["Skor"]]||0)});
  }
  candidates.sort(function(x,y){return y.score-x.score;});
  const maxToSend=Math.min(BATCH_SEND_LIMIT,Math.max(1,Number(limit||BATCH_SEND_LIMIT)),quota);
  const lock=LockService.getDocumentLock();
  lock.waitLock(20000);
  let sent=0,errors=0;
  try{
    for(let i=0;i<candidates.length&&sent<maxToSend;i++){
      const rowNum=candidates[i].row;
      const status=String(sh.getRange(rowNum,col_("Status")).getValue()||"").toUpperCase().trim();
      if(status!=="READY")continue;
      const email=String(sh.getRange(rowNum,col_("Email")).getValue()||"").trim();
      const subject=String(sh.getRange(rowNum,col_("Subject")).getValue()||"").trim();
      const body=String(sh.getRange(rowNum,col_("Body")).getValue()||"").trim();
      const leadId=String(sh.getRange(rowNum,col_("Lead ID")).getValue()||"");
      if(!email||!subject||!body||!leadId)continue;
      try{
        const tagged=/^\[SJ-[a-f0-9]{12}\]/i.test(subject)?subject:"[SJ-"+leadId+"] "+subject;
        MailApp.sendEmail({to:email,subject:tagged,body:body,name:AGENCY_NAME,replyTo:ownerEmail_()});
        sh.getRange(rowNum,col_("Subject")).setValue(tagged);
        const first=now_();
        sh.getRange(rowNum,col_("Status")).setValue("SENT");
        scheduleAfterManualSend_(rowNum,first);
        sh.getRange(rowNum,col_("Last Error")).clearContent();
        sh.getRange(rowNum,col_(MANUAL_SEND_COL)).setValue(false);
        sh.getRange(rowNum,col_(SEND_RESULT_COL)).setValue("AUTO_SENT "+Utilities.formatDate(first,"Asia/Jakarta","yyyy-MM-dd HH:mm:ss"));
        sent++;
        Utilities.sleep(750);
      }catch(err){
        errors++;
        markError_(leadId,String(err));
      }
    }
  }finally{
    try{lock.releaseLock();}catch(e){}
  }
  return json_({ok:true,requested:BATCH_SEND_LIMIT,candidates:candidates.length,sent:sent,errors:errors,quota_before:quota,quota_after:Math.max(0,MailApp.getRemainingDailyQuota())});
}

function sendQueue_(limit){
  return autoSendBatch_(limit||BATCH_SEND_LIMIT);
}

function findThreadByLeadId_(id){
  const threads=GmailApp.search('subject:"[SJ-'+id+']"',0,10);
  return threads.length?threads[0]:null;
}

function findRowByEmail_(email){
  const target=String(email||"").toLowerCase().trim();
  if(!target)return -1;
  const sh=sheet_();
  if(sh.getLastRow()<2)return -1;
  const values=sh.getRange(2,col_("Email"),sh.getLastRow()-1,1).getValues();
  for(let i=0;i<values.length;i++){
    if(String(values[i][0]||"").toLowerCase().trim()===target)return i+2;
  }
  return -1;
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
  let remaining=Math.max(0,MailApp.getRemainingDailyQuota());
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

function geminiReply_(business,service,pain,originalSubject,originalBody,inboundBody,waNumber){
  const key=String(PropertiesService.getScriptProperties().getProperty("GEMINI_API_KEY")||"").trim();
  if(!key)return "";
  const model=String(PropertiesService.getScriptProperties().getProperty("GEMINI_MODEL")||"gemini-3.8-flash").trim();
  const wa=waNumber?"https://wa.me/"+waNumber+"?text="+encodeURIComponent("Halo Rey, saya dari "+business+". Saya membalas email tentang kebutuhan "+service+". Saya ingin melanjutkan pembahasannya."):"";
  const prompt=[
    "Kamu adalah sales agent Sonjaya AI.",
    "Balas email prospek berdasarkan isi email mereka. Balasan harus terasa benar-benar nyambung dengan apa yang mereka tulis, bukan template generik.",
    "Tujuan akhir: arahkan percakapan ke WhatsApp Rey untuk pembahasan lebih lanjut.",
    "Aturan:",
    "- Jawab pertanyaan/keberatan yang benar-benar ditulis prospek.",
    "- Jangan mengarang harga, hasil, klien, fitur, atau fakta yang tidak tersedia.",
    "- Jika informasi belum cukup, katakan singkat apa yang perlu diketahui.",
    "- Gunakan Bahasa Indonesia yang natural, profesional, ramah, tidak kaku.",
    "- Jangan menyebut bahwa kamu AI.",
    "- Jangan menggunakan heading atau bullet list kecuali memang membantu menjawab.",
    "- Tutup dengan ajakan lanjut ke WhatsApp.",
    "- Sertakan nomor WhatsApp Rey: +"+waNumber+".",
    "- Sertakan link WhatsApp: "+wa+".",
    "- Jangan mengubah URL tersebut.",
    "",
    "DATA LEAD:",
    "Bisnis: "+business,
    "Layanan yang terdeteksi: "+service,
    "Pain point: "+pain,
    "Subject email awal: "+originalSubject,
    "Body email awal: "+originalBody,
    "",
    "REPLY PROSPEK:",
    inboundBody,
    "",
    "Tulis hanya body email balasan yang siap dikirim."
  ].join("\n");

  const url="https://generativelanguage.googleapis.com/v1beta/models/"+encodeURIComponent(model)+":generateContent";
  const payload={
    contents:[{parts:[{text:prompt}]}],
    generationConfig:{maxOutputTokens:700}
  };
  const res=UrlFetchApp.fetch(url,{
    method:"post",
    contentType:"application/json; charset=UTF-8",
    headers:{"x-goog-api-key":key},
    payload:JSON.stringify(payload),
    muteHttpExceptions:true
  });
  const code=res.getResponseCode(),txt=res.getContentText();
  if(code<200||code>=300)throw new Error("Gemini HTTP "+code+": "+txt.slice(0,700));
  const data=JSON.parse(txt||"{}");
  const parts=((data.candidates||[])[0]||{}).content&&((data.candidates||[])[0].content.parts||[]);
  return parts.map(function(p){return String(p.text||"");}).join("").trim();
}

function fallbackReply_(business,service,inboundBody,waNumber){
  const wa=waNumber?"https://wa.me/"+waNumber+"?text="+encodeURIComponent("Halo Rey, saya dari "+business+". Saya membalas email dan ingin melanjutkan pembahasannya tentang "+service+"."):"";
  const context=String(inboundBody||"").replace(/\\s+/g," ").trim().slice(0,500);
  return "Terima kasih sudah membalas, "+business+". Saya sudah membaca pesan Anda: \""+context+"\".\\n\\nAgar saya bisa menyesuaikan pembahasan dengan kebutuhan Anda, kita lanjutkan langsung melalui WhatsApp Rey.\\n\\nNomor WhatsApp Rey: +"+waNumber+"\\n"+wa+"\\n\\nSilakan lanjutkan di sana, nanti kita bahas detailnya.";
}

function scanReplies_(limit){
  const sh=sheet_(),last=sh.getLastRow();
  if(last<2)return json_({ok:true,replied:0});
  const threads=GmailApp.search("in:inbox newer_than:14d -from:me",0,100);
  const owner=ownerEmail_();let replied=0,matched=0,aiReplied=0,aiFallback=0;
  for(let ti=0;ti<threads.length&&replied<limit;ti++){
    const thread=threads[ti],subject=String(thread.getFirstMessageSubject()||"");
    const m=subject.match(/\[SJ-([a-f0-9]{12})\]/i);
    let row=-1;
    if(m)row=findRowById_(m[1]);

    const msgs=thread.getMessages();let inbound=null;
    for(let i=msgs.length-1;i>=0;i--){
      const from=String(msgs[i].getFrom()||"").toLowerCase();
      if(owner && from.indexOf(owner)===-1){inbound=msgs[i];break;}
    }
    if(!inbound)continue;

    if(row<2){
      const fromHeader=String(inbound.getFrom()||"");
      const emailMatch=fromHeader.match(/<([^>]+)>/)||fromHeader.match(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\\.[A-Z]{2,}/i);
      const inboundEmail=(emailMatch?(emailMatch[1]||emailMatch[0]):fromHeader).toLowerCase().trim();
      row=findRowByEmail_(inboundEmail);
    }
    if(row<2)continue;
    matched++;

    const status=String(sh.getRange(row,col_("Status")).getValue()||"").toUpperCase();
    if(["WA_HANDOFF","OPTOUT"].indexOf(status)>=0)continue;

    const body=String(inbound.getPlainBody()||"").slice(0,5000).trim();
    if(!body)continue;
    if(body.toUpperCase().indexOf("UNSUBSCRIBE")!==-1){
      sh.getRange(row,col_("Status")).setValue("OPTOUT");
      sh.getRange(row,col_("Opt Out")).setValue("YES");
      continue;
    }

    const business=String(sh.getRange(row,col_("Nama bisnis")).getValue()||"Perusahaan");
    const email=String(sh.getRange(row,col_("Email")).getValue()||"");
    const service=String(sh.getRange(row,col_("Layanan direkomendasikan")).getValue()||"automation AI");
    const pain=String(sh.getRange(row,col_("Pain point")).getValue()||"");
    const originalSubject=String(sh.getRange(row,col_("Subject")).getValue()||"");
    const originalBody=String(sh.getRange(row,col_("Body")).getValue()||"").slice(0,6000);
    const intent=/harga|price|biaya|cost|tertarik|minat|interested|bisa|boleh|minta|info|detail|contoh|diskusi|call|meeting|whatsapp|wa\\b/i.test(body)?"INTERESTED":"REPLIED";
    const waNumber=String(PropertiesService.getScriptProperties().getProperty("WA_NUMBER")||"").replace(/\\D/g,"");

    let replyText="";
    try{
      replyText=geminiReply_(business,service,pain,originalSubject,originalBody,body,waNumber);
      if(replyText)aiReplied++;
    }catch(err){
      console.log("Gemini reply failed: "+String(err));
    }
    if(!replyText){
      replyText=fallbackReply_(business,service,body,waNumber);
      aiFallback++;
    }

    try{thread.reply(replyText,{name:AGENCY_NAME});}catch(e){continue;}
    sh.getRange(row,col_("Status")).setValue("WA_HANDOFF");
    sh.getRange(row,col_("Reply At")).setValue(now_());
    sh.getRange(row,col_("Reply Intent")).setValue(intent);
    sh.getRange(row,col_("Last Reply")).setValue(body.slice(0,1500));
    sh.getRange(row,col_("WhatsApp Handoff")).setValue(waNumber?"https://wa.me/"+waNumber:"");
    sh.getRange(row,col_("Last Error")).clearContent();
    replied++;
  }
  return json_({ok:true,replied:replied,matched:matched,ai_replied:aiReplied,ai_fallback:aiFallback,scanned_threads:threads.length});
}
function ingestContent_(rows){
  const sh=contentPlanningSheet_(),existing={};
  if(sh.getLastRow()>=2){
    const all=sh.getRange(2,1,sh.getLastRow()-1,2).getValues();
    all.forEach(function(r){existing[String(r[0])+"|"+String(r[1])]=true;});
  }
  const idx={}; CONTENT_PLAN_HEADERS.forEach(function(h,i){idx[h]=i;});
  let added=0,duplicates=0;
  rows.forEach(function(r){
    const key=String(r.date||"")+"|"+String(r.platform||"");
    if(existing[key]){duplicates++;return;}
    const row=new Array(CONTENT_PLAN_HEADERS.length).fill("");
    function set(h,v){if(idx[h]!==undefined)row[idx[h]]=v==null?"":v;}
    set("Tanggal",r.date); set("Platform",r.platform||"Instagram");
    set("Format",r.format||"CAROUSEL_7_SLIDES"); set("Tujuan",r.objective||"");
    set("Topik",r.topic||""); set("Hook",r.hook||""); set("Caption",r.caption||""); set("CTA",r.cta||"");
    set("Slide Count",Number(r.slide_count||7)); set("Carousel PDF URL",r.carousel_pdf_url||"");
    set("Carousel Cover URL",r.carousel_cover_url||""); set("Slides JSON",r.slides_json||"");
    set("Status",r.status||"READY_FOR_MANUAL_UPLOAD"); set("Publish Mode","MANUAL_UPLOAD");
    set("Catatan",r.catatan||"Content Studio | upload manual"); set("Pilar Konten",r.content_pillar||"");
    set("Script Lengkap",r.script||"");
    const urls=Array.isArray(r.slide_urls)?r.slide_urls:[];
    for(let i=0;i<7;i++){
      const url=String(urls[i]||"").trim();
      set("Slide "+(i+1)+" URL",url);
      if(idx["Slide "+(i+1)+" Preview"]!==undefined && url){
        row[idx["Slide "+(i+1)+" Preview"]]="=IMAGE(\""+url.replace(/"/g,'""')+"\")";
      }
    }
    sh.appendRow(row); existing[key]=true; added++;
  });
  return json_({ok:true,added:added,duplicates:duplicates});
}

function urlFetchJson_(url,options){
  const res=UrlFetchApp.fetch(url,options||{muteHttpExceptions:true});
  const code=res.getResponseCode(),txt=res.getContentText();
  let data={};
  try{data=JSON.parse(txt||"{}");}catch(e){data={raw:txt};}
  if(code<200||code>=300)throw new Error("HTTP "+code+": "+txt.slice(0,1000));
  return data;
}

function removeLegacyAutomationTriggers_(){
  ScriptApp.getProjectTriggers().forEach(function(t){
    const fn=t.getHandlerFunction();
    if(["hourlyAutomation_","manualSendOnEdit_","salesAutomation_"].indexOf(fn)>=0)ScriptApp.deleteTrigger(t);
  });
}

function setup(){
  sheet_();contentSheet_();contentPlanningSheet_();automationLogSheet_();
  removeLegacyAutomationTriggers_();
  // Sales scheduling is owned by GitHub Actions every 2 hours.
  // No Apps Script time trigger is created here.
  backfillProspectControls_(SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_NAME));
  return "Sonjaya sheets ready | scheduling: GitHub Actions every 2 hours | version "+CODE_VERSION;
}

function systemStatus(){
  const ui=SpreadsheetApp.getUi();
  ui.alert(liveHealth_().getContent());
}

function logSalesCycle_(replies,sends,followups){
  const sh=automationLogSheet_();
  function obj(v){try{return JSON.parse(v.getContent());}catch(e){return {ok:false,error:String(v&&v.getContent?v.getContent():"unknown")};}}
  const r=obj(replies),s=obj(sends),f=obj(followups);
  const quotaBefore=s.quota_before!==undefined?s.quota_before:"";
  const quotaAfter=s.quota_after!==undefined?s.quota_after:"";
  const errors=(Number(s.errors||0)+(!r.ok?1:0)+(!f.ok?1:0));
  const status=errors===0?"OK":"PARTIAL";
  sh.appendRow([
    now_(),
    "GitHub Actions / 2h",
    Number(s.sent||0),
    Number(f.processed||0),
    Number(r.replied||0),
    errors,
    quotaBefore,
    quotaAfter,
    status,
    JSON.stringify({replies:r,sends:s,followups:f}).slice(0,5000)
  ]);
  return {replies:r,sends:s,followups:f};
}

function salesAutomation_(){
  const lock=LockService.getScriptLock();
  if(!lock.tryLock(1000))return json_({ok:true,skipped:true,reason:"another cycle is running"});
  try{
    removeLegacyAutomationTriggers_();
    let replies,sends,followups;
    // Send first so a slow Gmail reply scan cannot block outbound sales.
    try{sends=autoSendBatch_(BATCH_SEND_LIMIT);}catch(e){sends=json_({ok:false,error:String(e)});}
    try{followups=processFollowups_(MAX_FOLLOWUPS_PER_RUN);}catch(e){followups=json_({ok:false,error:String(e)});}
    // Keep reply scanning bounded; any transient failure is logged and retried next cycle.
    try{replies=scanReplies_(10);}catch(e){replies=json_({ok:false,error:String(e)});}
    const details=logSalesCycle_(replies,sends,followups);
    const cycleOk=Boolean(details && details.replies && details.replies.ok && details.sends && details.sends.ok && details.followups && details.followups.ok);
    return json_({ok:cycleOk,cycle_status:cycleOk?"OK":"PARTIAL_OR_ERROR",replies:details.replies,sends:details.sends,followups:details.followups});
  }finally{
    try{lock.releaseLock();}catch(e){}
  }
}

function hourlyAutomation_(){
  // Legacy trigger compatibility: no-op. New sales cycle runs every 2 hours.
  return;
}
