const SHEET_NAME = "Prospects";
const HEADERS = [
  "Lead ID","Tanggal ditemukan","Nama bisnis","Email","Sumber email",
  "Website","Social","Kota","Kategori","Bukti publik","Skor","Alasan",
  "Pain point","Subject","Body","Status","Sent At","Attempts","Last Error",
  "Opt Out","Catatan"
];
const MAX_ATTEMPTS = 3;

function sheet_() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sh = ss.getSheetByName(SHEET_NAME);
  if (!sh) sh = ss.insertSheet(SHEET_NAME);
  if (sh.getLastRow() === 0) {
    sh.getRange(1,1,1,HEADERS.length).setValues([HEADERS]);
  } else {
    const current = sh.getRange(1,1,1,Math.max(sh.getLastColumn(),1)).getValues()[0];
    const missing = HEADERS.filter(function(h){ return current.indexOf(h) === -1; });
    if (missing.length) {
      sh.getRange(1,current.length+1,1,missing.length).setValues([missing]);
    }
  }
  sh.setFrozenRows(1);
  sh.getRange(1,1,1,HEADERS.length).setFontWeight("bold");
  sh.getDataRange().setWrap(true);
  return sh;
}

function col_(name){ return HEADERS.indexOf(name)+1; }

function makeId_(email, website){
  const raw = String(email||"").toLowerCase().trim()+"|"+String(website||"").toLowerCase().trim();
  const bytes = Utilities.computeDigest(Utilities.DigestAlgorithm.MD5, raw);
  return bytes.map(function(b){
    const v = b < 0 ? b+256 : b;
    return ("0"+v.toString(16)).slice(-2);
  }).join("").slice(0,20);
}

function json_(obj){
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

function auth_(body){
  const expected = PropertiesService.getScriptProperties().getProperty("WEBHOOK_TOKEN");
  return Boolean(expected && body && body.token === expected);
}

function doGet(){
  return json_({ok:true,service:"Sonjaya AI Sales Engine",status:"running"});
}

function doPost(e){
  try{
    const body = JSON.parse((e.postData && e.postData.contents) || "{}");
    if(!auth_(body)) return json_({ok:false,error:"Unauthorized"});
    const action = body.action || "ingest";
    if(action === "ingest") return ingest_(body.rows || []);
    if(action === "queue") return queue_(Number(body.limit || 5));
    if(action === "mark_sent") return markSent_(String(body.id||""),String(body.sent_at||""));
    if(action === "mark_error") return markError_(String(body.id||""),String(body.error||""));
    if(action === "opt_out") return optOut_(String(body.id||""));
    return json_({ok:false,error:"Unknown action"});
  }catch(err){
    return json_({ok:false,error:String(err)});
  }
}

function ingest_(rows){
  const sh = sheet_();
  if(!Array.isArray(rows)) rows = [];
  const existing = {};
  if(sh.getLastRow() >= 2){
    const emailCol = col_("Email");
    sh.getRange(2,emailCol,sh.getLastRow()-1,1).getValues().forEach(function(r){
      const email = String(r[0]||"").toLowerCase().trim();
      if(email) existing[email] = true;
    });
  }

  let added=0, duplicates=0, noEmail=0;

  rows.forEach(function(row){
    const email = String(row.recipient_email||"").toLowerCase().trim();
    if(!email || email.indexOf("@") === -1){ noEmail++; return; }
    if(existing[email]){ duplicates++; return; }

    const website = String(row.website_url||"").trim();
    const output = new Array(HEADERS.length).fill("");
    output[col_("Lead ID")-1] = String(row.lead_id||makeId_(email,website));
    output[col_("Tanggal ditemukan")-1] = row.tanggal_ditemukan||"";
    output[col_("Nama bisnis")-1] = row.nama_bisnis||"";
    output[col_("Email")-1] = email;
    output[col_("Sumber email")-1] = row.email_source_url||"";
    output[col_("Website")-1] = website;
    output[col_("Social")-1] = row.social_url||"";
    output[col_("Kota")-1] = row.kota||"";
    output[col_("Kategori")-1] = row.kategori||"";
    output[col_("Bukti publik")-1] = row.bukti_publik||"";
    output[col_("Skor")-1] = Number(row.skor||0);
    output[col_("Alasan")-1] = row.alasan||"";
    output[col_("Pain point")-1] = row.pain_point||"";
    output[col_("Subject")-1] = row.subject||"";
    output[col_("Body")-1] = row.body||"";
    output[col_("Status")-1] = row.status||"REVIEW";
    output[col_("Attempts")-1] = 0;
    output[col_("Opt Out")-1] = "NO";
    output[col_("Catatan")-1] = row.catatan||"";
    sh.appendRow(output);
    existing[email]=true;
    added++;
  });

  return json_({ok:true,received:rows.length,added:added,duplicates:duplicates,no_email:noEmail});
}

function queue_(limit){
  const sh = sheet_();
  const lastRow = sh.getLastRow();
  if(lastRow < 2) return json_({ok:true,sent_today:0,leads:[]});
  limit = Math.max(1,Math.min(limit||5,20));

  const values = sh.getRange(2,1,lastRow-1,HEADERS.length).getValues();
  const idx = {};
  HEADERS.forEach(function(h,i){ idx[h]=i; });

  const today = Utilities.formatDate(new Date(),"Asia/Jakarta","yyyy-MM-dd");
  let sentToday=0;
  const candidates=[];

  values.forEach(function(row){
    const sentAt=String(row[idx["Sent At"]]||"");
    if(sentAt.indexOf(today)===0) sentToday++;

    const status=String(row[idx["Status"]]||"").trim().toUpperCase();
    const email=String(row[idx["Email"]]||"").trim();
    const subject=String(row[idx["Subject"]]||"").trim();
    const body=String(row[idx["Body"]]||"").trim();
    const attempts=Number(row[idx["Attempts"]]||0);
    const optOut=String(row[idx["Opt Out"]]||"").trim().toUpperCase();

    if(!email || !subject || !body || optOut==="YES") return;
    if(!["READY","ERROR"].includes(status)) return;
    if(attempts>=MAX_ATTEMPTS) return;

    candidates.push({
      id:String(row[idx["Lead ID"]]||""),
      recipient_email:email,
      subject:subject,
      body:body,
      score:Number(row[idx["Skor"]]||0)
    });
  });

  candidates.sort(function(a,b){ return b.score-a.score; });
  return json_({ok:true,sent_today:sentToday,leads:candidates.slice(0,limit)});
}

function findRowById_(id){
  const sh=sheet_();
  if(sh.getLastRow()<2) return -1;
  const values=sh.getRange(2,col_("Lead ID"),sh.getLastRow()-1,1).getValues();
  for(let i=0;i<values.length;i++){
    if(String(values[i][0]||"")===id) return i+2;
  }
  return -1;
}

function markSent_(id,sentAt){
  if(!id) return json_({ok:false,error:"Missing id"});
  const sh=sheet_();
  const row=findRowById_(id);
  if(row<2) return json_({ok:false,error:"Lead ID not found"});
  sh.getRange(row,col_("Status")).setValue("SENT");
  sh.getRange(row,col_("Sent At")).setValue(sentAt||new Date());
  sh.getRange(row,col_("Last Error")).clearContent();
  return json_({ok:true,id:id,status:"SENT"});
}

function markError_(id,error){
  if(!id) return json_({ok:false,error:"Missing id"});
  const sh=sheet_();
  const row=findRowById_(id);
  if(row<2) return json_({ok:false,error:"Lead ID not found"});
  const attemptsCell=sh.getRange(row,col_("Attempts"));
  const attempts=Number(attemptsCell.getValue()||0)+1;
  attemptsCell.setValue(attempts);
  sh.getRange(row,col_("Status")).setValue(attempts>=MAX_ATTEMPTS ? "FAILED" : "ERROR");
  sh.getRange(row,col_("Last Error")).setValue(error||"Unknown SMTP error");
  return json_({ok:true,id:id,attempts:attempts});
}

function optOut_(id){
  if(!id) return json_({ok:false,error:"Missing id"});
  const sh=sheet_();
  const row=findRowById_(id);
  if(row<2) return json_({ok:false,error:"Lead ID not found"});
  sh.getRange(row,col_("Opt Out")).setValue("YES");
  sh.getRange(row,col_("Status")).setValue("OPTOUT");
  return json_({ok:true,id:id,status:"OPTOUT"});
}

function setup(){
  const sh=sheet_();
  sh.autoResizeColumns(1,HEADERS.length);
  return sh.getName();
}
