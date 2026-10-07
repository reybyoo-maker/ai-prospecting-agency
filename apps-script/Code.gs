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
const CODE_VERSION = "2026-10-07.7";
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


function setupSocialAutomation_(){
  const props=PropertiesService.getScriptProperties();
  if(!props.getProperty("IG_COMMENT_KEYWORD"))props.setProperty("IG_COMMENT_KEYWORD","REY MAU");
  if(!props.getProperty("IG_PUBLIC_COMMENT_REPLY"))props.setProperty("IG_PUBLIC_COMMENT_REPLY","Siap! 👋 Cek DM ya.");
  if(!props.getProperty("TIKTOK_COMMENT_KEYWORD"))props.setProperty("TIKTOK_COMMENT_KEYWORD","REY MAU");
  if(!props.getProperty("TIKTOK_PUBLIC_COMMENT_REPLY"))props.setProperty("TIKTOK_PUBLIC_COMMENT_REPLY","Siap! 👋 Cek DM ya.");
  if(!props.getProperty("TIKTOK_API_VERSION"))props.setProperty("TIKTOK_API_VERSION","v1.3");
  socialLeadsSheet_();
  return json_({ok:true,message:"Social automation defaults ready. Add platform credentials in Script Properties."});
}

function socialReplyText_(platform,username){
  const who=username?(" @"+String(username).replace(/^@/,"")):"";
  const wa=socialWaLink_(username||("lead "+platform));
  return "Halo"+who+"! 👋 Makasih sudah tertarik dengan Sonjaya. Kami bantu bisnis dengan remote support dan automation berbasis AI. Kalau mau lanjut, chat WhatsApp di sini:"+(wa?"\n"+wa:"");
}

function sendInstagramDm_(recipientId,text){
  const token=PropertiesService.getScriptProperties().getProperty("IG_ACCESS_TOKEN")||"";
  const igUserId=PropertiesService.getScriptProperties().getProperty("IG_USER_ID")||"";
  const version=PropertiesService.getScriptProperties().getProperty("IG_API_VERSION")||"v26.0";
  const host=PropertiesService.getScriptProperties().getProperty("IG_GRAPH_HOST") ||
    PropertiesService.getScriptProperties().getProperty("IG_MESSAGING_HOST") ||
    "https://graph.instagram.com";
  if(!token||!igUserId)throw new Error("INSTAGRAM_MESSAGING_NOT_CONFIGURED");
  return urlFetchJson_(host+"/"+version+"/"+encodeURIComponent(igUserId)+"/messages",{
    method:"post",
    contentType:"application/json",
    headers:{Authorization:"Bearer "+token},
    payload:JSON.stringify({recipient:{id:String(recipientId)},message:{text:String(text||"").slice(0,1000)}}),
    muteHttpExceptions:true
  });
}

function handleInstagramMessages_(body){
  let processed=0,replied=0,errors=0;
  const entries=Array.isArray(body&&body.entry)?body.entry:[];
  entries.forEach(function(entry){
    const messaging=Array.isArray(entry&&entry.messaging)?entry.messaging:[];
    messaging.forEach(function(item){
      const sender=item&&item.sender||{}, recipient=item&&item.recipient||{};
      const senderId=String(sender.id||""), recipientId=String(recipient.id||"");
      const msg=item&&item.message||{};
      const text=String(msg.text||"").trim();
      if(!senderId||!text)return;
      const ownId=String(PropertiesService.getScriptProperties().getProperty("IG_USER_ID")||"");
      if(ownId&&senderId===ownId)return;
      processed++;
      try{
        const username=String(msg.username||sender.username||"");
        const reply=socialReplyText_("Instagram",username);
        const result=sendInstagramDm_(senderId,reply);
        replied++;
        logSocialLead_({
          "Tanggal":Utilities.formatDate(now_(),"Asia/Jakarta","yyyy-MM-dd HH:mm:ss"),
          "Platform":"Instagram",
          "Keyword":"",
          "Username":username,
          "User ID":senderId,
          "Comment ID":"",
          "Comment":text,
          "Post ID":"",
          "DM Status":"DM_AUTO_REPLY_SENT",
          "WhatsApp Link":socialWaLink_(username||"Instagram lead"),
          "Catatan":"Inbound DM auto-reply | "+JSON.stringify(result).slice(0,700)
        });
      }catch(err){
        errors++;
        logSocialLead_({
          "Tanggal":Utilities.formatDate(now_(),"Asia/Jakarta","yyyy-MM-dd HH:mm:ss"),
          "Platform":"Instagram",
          "Keyword":"",
          "Username":"",
          "User ID":senderId,
          "Comment ID":"",
          "Comment":text,
          "Post ID":"",
          "DM Status":"DM_AUTO_REPLY_ERROR",
          "WhatsApp Link":"",
          "Catatan":String(err).slice(0,700)
        });
      }
    });
  });
  return json_({ok:true,platform:"instagram",processed:processed,replied:replied,errors:errors});
}

function handleInstagramWebhook_(body){
  let result={comments:null,messages:null};
  result.comments=handleInstagramCommentsOnly_(body);
  result.messages=handleInstagramMessages_(body);
  return json_({ok:true,platform:"instagram",comments:result.comments,messages:result.messages});
}

function handleInstagramCommentsOnly_(body){
  let processed=0,matched=0,dmSent=0,publicReply=0,errors=0;
  const entries=Array.isArray(body&&body.entry)?body.entry:[];
  entries.forEach(function(entry){
    const changes=Array.isArray(entry&&entry.changes)?entry.changes:[];
    changes.forEach(function(change){
      const field=String(change.field||"").toLowerCase();
      if(field!=="comments")return;
      const v=change.value||{}, commentId=String(v.id||v.comment_id||""), text=String(v.text||"");
      const from=v.from||{}, userId=String(from.id||""), username=String(from.username||from.name||"");
      const media=v.media||{}, postId=String(media.id||v.media_id||"");
      processed++;
      if(!commentId||!commentMatchesKeyword_(text)||socialCommentExists_(commentId))return;
      matched++;
      const wa=socialWaLink_(username||"Instagram lead");
      let dmStatus="NO_WA_NUMBER",note="Keyword cocok.";
      try{
        const msg=socialReplyText_("Instagram",username);
        const result=sendInstagramPrivateReply_(commentId,msg);
        dmStatus="DM_SENT";
        note="DM="+JSON.stringify(result).slice(0,500);
        dmSent++;
        const publicText=PropertiesService.getScriptProperties().getProperty("IG_PUBLIC_COMMENT_REPLY")||"Siap! 👋 Cek DM ya.";
        try{
          const publicResult=sendInstagramPublicReply_(commentId,publicText);
          publicReply++;
          dmStatus="DM_SENT_PUBLIC_REPLY_SENT";
          note+=" | PUBLIC="+JSON.stringify(publicResult).slice(0,500);
        }catch(publicErr){
          dmStatus="DM_SENT_PUBLIC_REPLY_ERROR";
          note+=" | PUBLIC_ERROR="+String(publicErr).slice(0,500);
          errors++;
        }
      }catch(err){
        dmStatus="DM_ERROR";
        note=String(err).slice(0,800);
        errors++;
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
  return {processed:processed,matched:matched,dm_sent:dmSent,public_reply:publicReply,errors:errors};
}

function tiktokBaseUrl_(){
  const v=PropertiesService.getScriptProperties().getProperty("TIKTOK_API_VERSION")||"v1.3";
  return "https://business-api.tiktok.com/open_api/"+v;
}

function tiktokToken_(){
  const token=PropertiesService.getScriptProperties().getProperty("TIKTOK_ACCESS_TOKEN")||"";
  if(!token)throw new Error("TIKTOK_ACCESS_TOKEN_NOT_CONFIGURED");
  return token;
}

function tiktokBusinessId_(){
  const id=PropertiesService.getScriptProperties().getProperty("TIKTOK_BUSINESS_ID")||"";
  if(!id)throw new Error("TIKTOK_BUSINESS_ID_NOT_CONFIGURED");
  return id;
}

function tiktokJson_(path,payload,method){
  const opts={
    method:method||"post",
    contentType:"application/json",
    headers:{"Access-Token":tiktokToken_()},
    muteHttpExceptions:true
  };
  if(payload)opts.payload=JSON.stringify(payload);
  return urlFetchJson_(tiktokBaseUrl_()+path,opts);
}

function tiktokKeywordMatch_(text){
  const keyword=PropertiesService.getScriptProperties().getProperty("TIKTOK_COMMENT_KEYWORD")||"REY MAU";
  const hay=normalizeKeyword_(text), needle=normalizeKeyword_(keyword);
  return Boolean(needle && (hay===needle || hay.indexOf(needle)!==-1));
}

function tiktokMessageText_(content){
  if(content==null)return "";
  if(typeof content==="string"){
    try{return tiktokMessageText_(JSON.parse(content));}catch(e){return String(content);}
  }
  if(typeof content!=="object")return String(content);
  return String(
    content.text ||
    (content.message&&content.message.text&&content.message.text.body) ||
    (content.text&&content.text.body) ||
    content.body ||
    content.comment_text ||
    ""
  );
}

function tiktokUserName_(content){
  if(!content||typeof content!=="object")return "";
  const u=content.from_user||content.from||content.user||content.sender||{};
  return String(u.username||u.nickname||u.name||"");
}

function tiktokSendDm_(conversationId,text){
  return tiktokJson_("/business/message/send/",{
    business_id:tiktokBusinessId_(),
    recipient_type:"CONVERSATION",
    recipient:String(conversationId),
    message_type:"TEXT",
    text:{body:String(text||"").slice(0,6000)}
  },"post");
}

function tiktokSendCommentDm_(commentId,text){
  return tiktokJson_("/business/message/send/",{
    business_id:tiktokBusinessId_(),
    message_type:"TEXT",
    text:{body:String(text||"").slice(0,6000)},
    direct_reply:{
      reply_type:"COMMENT_REPLY",
      comment_reply:{comment_id:String(commentId)}
    }
  },"post");
}

function tiktokGetComment_(commentId,videoId){
  const businessId=tiktokBusinessId_();
  const ids=encodeURIComponent(JSON.stringify([String(commentId)]));
  const url=tiktokBaseUrl_()+"/business/comment/list/?business_id="+encodeURIComponent(businessId)+
    "&video_id="+encodeURIComponent(String(videoId))+
    "&comment_ids="+ids+
    "&max_count=1";
  const data=urlFetchJson_(url,{
    method:"get",
    headers:{"Access-Token":tiktokToken_()},
    muteHttpExceptions:true
  });
  const list=data&&data.data&&data.data.comments;
  const item=Array.isArray(list)&&list.length?list[0]:null;
  return item||null;
}

function tiktokReplyComment_(videoId,commentId,text){
  return tiktokJson_("/business/comment/reply/create/",{
    business_id:tiktokBusinessId_(),
    video_id:String(videoId),
    comment_id:String(commentId),
    text:String(text||"").slice(0,1500)
  },"post");
}

function tiktokEventObject_(body){
  if(!body)return {};
  if(body.content&&typeof body.content==="string"){
    try{return JSON.parse(body.content||"{}");}catch(e){}
  }
  if(body.content&&typeof body.content==="object")return body.content;
  return body;
}

function socialEventKey_(platform,eventId){
  return String(platform)+":"+String(eventId||"");
}

function socialEventExists_(eventKey){
  const sh=socialLeadsSheet_(),last=sh.getLastRow();
  if(last<2)return false;
  const col=colSocial_("Catatan");
  return sh.getRange(2,col,last-1,1).getValues().some(r=>String(r[0]||"").indexOf("EVENT_KEY="+eventKey)===0);
}

function handleTikTokWebhook_(body){
  const event=String(body&&body.event||body&&body.webhook_event_type||"").toLowerCase();
  const content=tiktokEventObject_(body);
  const eventId=String(body&&body.event_id||body&&body.request_id||content.event_id||content.message_id||content.comment_id||Utilities.getUuid());
  const key=socialEventKey_("tiktok",eventId);
  if(socialEventExists_(key))return json_({ok:true,platform:"tiktok",duplicate:true,event:event});

  let dmSent=0,publicReply=0,errors=0;
  try{
    if(event==="im_receive_high_intent_comment" || event.indexOf("high_intent_comment")>=0){
      const commentId=String(content.comment_id||"");
      const username=tiktokUserName_(content);
      if(commentId){
        const result=tiktokSendCommentDm_(commentId,socialReplyText_("TikTok",username));
        dmSent++;
        logSocialLead_({
          "Tanggal":Utilities.formatDate(now_(),"Asia/Jakarta","yyyy-MM-dd HH:mm:ss"),
          "Platform":"TikTok",
          "Keyword":"HIGH_INTENT",
          "Username":username,
          "User ID":String(content.unique_identifier||""),
          "Comment ID":commentId,
          "Comment":String(content.comment_text||""),
          "Post ID":String(content.video_id||""),
          "DM Status":"DM_SENT",
          "WhatsApp Link":socialWaLink_(username),
          "Catatan":"EVENT_KEY="+key+" | "+JSON.stringify(result).slice(0,700)
        });
      }
    } else if(event==="im_receive_message" || event.indexOf("receive_message")>=0){
      const conversationId=String(content.conversation_id||content.conversation||"");
      const textIn=String(tiktokMessageText_(content)||"").trim();
      const fromUser=content&&content.from_user||{};
      const fromRole=String(fromUser.role||"personal_account");
      if(conversationId && textIn && fromRole!=="business_account"){
        const username=tiktokUserName_(content);
        const result=tiktokSendDm_(conversationId,socialReplyText_("TikTok",username));
        dmSent++;
        logSocialLead_({
          "Tanggal":Utilities.formatDate(now_(),"Asia/Jakarta","yyyy-MM-dd HH:mm:ss"),
          "Platform":"TikTok",
          "Keyword":"",
          "Username":username,
          "User ID":String(fromUser.id||""),
          "Comment ID":"",
          "Comment":textIn,
          "Post ID":"",
          "DM Status":"DM_AUTO_REPLY_SENT",
          "WhatsApp Link":socialWaLink_(username),
          "Catatan":"EVENT_KEY="+key+" | "+JSON.stringify(result).slice(0,700)
        });
      }
    } else if(event==="comment.update" || event.indexOf("comment")>=0){
      const commentId=String(content.comment_id||content.id||"");
      const videoId=String(content.video_id||content.item_id||"");
      let commentText=String(content.comment_text||content.text||"").trim();
      const action=String(content.comment_action||content.action||"").toLowerCase();

      // TikTok comment.update webhook does not include comment text.
      if(!commentText && commentId && videoId && action!=="delete"){
        const item=tiktokGetComment_(commentId,videoId);
        commentText=String(item&&item.text||"").trim();
      }
      if(commentId && videoId && commentText && tiktokKeywordMatch_(commentText)){
        const username=tiktokUserName_(content);
        const msg=socialReplyText_("TikTok",username);
        const dmResult=tiktokSendCommentDm_(commentId,msg);
        dmSent++;
        let publicText="Siap! 👋 Cek DM ya, gue kirim info lanjut.";
        try{
          const publicResult=tiktokReplyComment_(videoId,commentId,publicText);
          publicReply++;
          logSocialLead_({
            "Tanggal":Utilities.formatDate(now_(),"Asia/Jakarta","yyyy-MM-dd HH:mm:ss"),
            "Platform":"TikTok",
            "Keyword":PropertiesService.getScriptProperties().getProperty("TIKTOK_COMMENT_KEYWORD")||"REY MAU",
            "Username":username,
            "User ID":String(content.unique_identifier||""),
            "Comment ID":commentId,
            "Comment":commentText,
            "Post ID":videoId,
            "DM Status":"DM_SENT_PUBLIC_REPLY_SENT",
            "WhatsApp Link":socialWaLink_(username),
            "Catatan":"EVENT_KEY="+key+" | DM="+JSON.stringify(dmResult).slice(0,500)+" | PUBLIC="+JSON.stringify(publicResult).slice(0,500)
          });
        }catch(publicErr){
          logSocialLead_({
            "Tanggal":Utilities.formatDate(now_(),"Asia/Jakarta","yyyy-MM-dd HH:mm:ss"),
            "Platform":"TikTok",
            "Keyword":PropertiesService.getScriptProperties().getProperty("TIKTOK_COMMENT_KEYWORD")||"REY MAU",
            "Username":username,
            "User ID":String(content.unique_identifier||""),
            "Comment ID":commentId,
            "Comment":commentText,
            "Post ID":videoId,
            "DM Status":"DM_SENT_PUBLIC_REPLY_ERROR",
            "WhatsApp Link":socialWaLink_(username),
            "Catatan":"EVENT_KEY="+key+" | DM="+JSON.stringify(dmResult).slice(0,500)+" | PUBLIC_ERROR="+String(publicErr).slice(0,500)
          });
        }
      }
    }
  }catch(err){
    errors++;
    logSocialLead_({
      "Tanggal":Utilities.formatDate(now_(),"Asia/Jakarta","yyyy-MM-dd HH:mm:ss"),
      "Platform":"TikTok",
      "Keyword":"",
      "Username":tiktokUserName_(content),
      "User ID":String(content.unique_identifier||""),
      "Comment ID":String(content.comment_id||""),
      "Comment":String(content.comment_text||content.text||""),
      "Post ID":String(content.video_id||""),
      "DM Status":"AUTOMATION_ERROR",
      "WhatsApp Link":"",
      "Catatan":"EVENT_KEY="+key+" | "+String(err).slice(0,900)
    });
  }
  return json_({ok:true,platform:"tiktok",event:event,dm_sent:dmSent,public_reply:publicReply,errors:errors});
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

function sendInstagramPublicReply_(commentId,text){
  const token=PropertiesService.getScriptProperties().getProperty("IG_ACCESS_TOKEN")||"";
  const version=PropertiesService.getScriptProperties().getProperty("IG_API_VERSION")||"v26.0";
  const host=PropertiesService.getScriptProperties().getProperty("IG_MESSAGING_HOST")||"https://graph.instagram.com";
  if(!token)throw new Error("INSTAGRAM_NOT_CONFIGURED");
  return urlFetchJson_(host+"/"+version+"/"+encodeURIComponent(commentId)+"/replies",{
    method:"post",
    payload:{message:String(text||"").slice(0,1000)},
    headers:{Authorization:"Bearer "+token},
    muteHttpExceptions:true
  });
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

function socialWaLink_(username){
  const number=String(PropertiesService.getScriptProperties().getProperty("WA_NUMBER")||"").replace(/\D/g,"");
  if(!number)return "";
  const name=String(username||"Instagram lead").replace(/^@/,"");
  const text="Halo Rey, saya dari Instagram @"+name+". Saya komen REY MAU dan ingin info tentang jasa Sonjaya.";
  return "https://wa.me/"+number+"?text="+encodeURIComponent(text);
}

function onOpen(){
  SpreadsheetApp.getUi().createMenu("Sonjaya")
    .addItem("Kirim Lead Terpilih","sendSelectedRows_")
    .addItem("Pasang Kontrol Manual Send","setup")
    .addItem("Setup Social Automation","setupSocialAutomation_")
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
  if(String(p.check||"").toLowerCase()==="social"){
    return socialHealth_();
  }
  const verify=PropertiesService.getScriptProperties().getProperty("META_VERIFY_TOKEN")||"";
  if(p["hub.mode"]==="subscribe" && p["hub.verify_token"]===verify && p["hub.challenge"]){
    return ContentService.createTextOutput(p["hub.challenge"]);
  }
  return json_({ok:true,service:"Sonjaya Remote Agency",status:"running"});
}

function liveHealth_(){
  const props=PropertiesService.getScriptProperties();
  const triggers=ScriptApp.getProjectTriggers();
  const handlers=triggers.map(t=>t.getHandlerFunction());
  const ss=SpreadsheetApp.getActiveSpreadsheet();
  const names=ss.getSheets().map(s=>s.getName());
  return json_({
    ok:true,
    service:"Sonjaya Remote Agency",
    version:CODE_VERSION,
    sheets:{
      prospects:names.indexOf(SHEET_NAME)>=0,
      content_planning:names.indexOf(CONTENT_PLAN_SHEET)>=0,
      social_leads:names.indexOf(SOCIAL_LEADS_SHEET)>=0
    },
    properties:{
      webhook_token:Boolean(props.getProperty("WEBHOOK_TOKEN")),
      wa_number:Boolean(props.getProperty("WA_NUMBER")),
      meta_verify_token:Boolean(props.getProperty("META_VERIFY_TOKEN")),
      ig_user_id:Boolean(props.getProperty("IG_USER_ID")),
      ig_access_token:Boolean(props.getProperty("IG_ACCESS_TOKEN")),
      ig_comment_keyword:Boolean(props.getProperty("IG_COMMENT_KEYWORD")),
      ig_content_publish:Boolean(props.getProperty("IG_ACCESS_TOKEN")),
      tiktok_business_id:Boolean(props.getProperty("TIKTOK_BUSINESS_ID")),
      tiktok_access_token:Boolean(props.getProperty("TIKTOK_ACCESS_TOKEN")),
      tiktok_comment_keyword:Boolean(props.getProperty("TIKTOK_COMMENT_KEYWORD")),
      tiktok_publish_note:"TikTok photo auto-posting requires a verified public URL prefix and video.publish authorization."
    },
    triggers:{
      hourlyAutomation:handlers.indexOf("hourlyAutomation_")>=0,
      manualSendOnEdit:handlers.indexOf("manualSendOnEdit_")>=0
    }
  });
}

function socialHealth_(){
  const props=PropertiesService.getScriptProperties();
  const configuredHost=props.getProperty("IG_GRAPH_HOST") ||
    props.getProperty("IG_MESSAGING_HOST") || "";
  const hosts=[
    configuredHost,
    "https://graph.instagram.com",
    "https://graph.facebook.com"
  ].filter(Boolean).filter(function(v,i,a){return a.indexOf(v)===i;});

  const out={
    ok:true,
    version:CODE_VERSION,
    webhook:{
      meta_verify_token:Boolean(props.getProperty("META_VERIFY_TOKEN")),
      webhook_token:Boolean(props.getProperty("WEBHOOK_TOKEN")),
      deployed_web_app:"doGet/doPost handlers present"
    },
    instagram:{
      configured:Boolean(props.getProperty("IG_ACCESS_TOKEN")),
      host:configuredHost||"auto-detect",
      api_version:props.getProperty("IG_API_VERSION")||"v26.0",
      user_id_configured:Boolean(props.getProperty("IG_USER_ID")),
      token_configured:Boolean(props.getProperty("IG_ACCESS_TOKEN")),
      api_ok:false,
      account:null,
      error:null
    },
    tiktok:{
      configured:Boolean(props.getProperty("TIKTOK_ACCESS_TOKEN")),
      business_id_configured:Boolean(props.getProperty("TIKTOK_BUSINESS_ID")),
      token_configured:Boolean(props.getProperty("TIKTOK_ACCESS_TOKEN")),
      api_ok:false,
      creator:null,
      error:null
    }
  };

  if(out.instagram.configured){
    let lastError="";
    const knownIgId=String(props.getProperty("IG_USER_ID")||"");
    for(let i=0;i<hosts.length;i++){
      const host=hosts[i];
      try{
        let me=null;
        if(host==="https://graph.instagram.com"){
          me=instagramGetHost_(host,"/me",{fields:"id,username"});
        }else if(host==="https://graph.facebook.com"){
          if(knownIgId){
            me=instagramGetHost_(host,"/"+encodeURIComponent(knownIgId),{fields:"id,username,name"});
          }else{
            const pages=instagramGetHost_(host,"/me/accounts",{
              fields:"id,name,instagram_business_account{id,username}"
            });
            const data=Array.isArray(pages&&pages.data)?pages.data:[];
            for(let j=0;j<data.length;j++){
              const iga=data[j]&&data[j].instagram_business_account;
              if(iga&&iga.id){
                me={id:iga.id,username:iga.username||"",source:"instagram_business_account",page_id:data[j].id};
                break;
              }
            }
            if(!me)lastError="Facebook /me/accounts returned no instagram_business_account: "+JSON.stringify(pages||{}).slice(0,900);
          }
        }
        if(me&&me.id){
          out.instagram.api_ok=true;
          out.instagram.host=host;
          out.instagram.account={
            id:String(me.id),
            username:String(me.username||me.name||"")
          };
          props.setProperty("IG_USER_ID",String(me.id));
          props.setProperty("IG_GRAPH_HOST",host);
          props.setProperty("IG_MESSAGING_HOST",host);
          break;
        }
        if(!lastError)lastError=JSON.stringify(me||{}).slice(0,900);
      }catch(err){
        lastError=String(err).slice(0,900);
      }
    }
    if(!out.instagram.api_ok){
      out.instagram.error="Instagram API probe gagal pada semua host. "+lastError;
    }
  }else{
    out.instagram.error="IG_ACCESS_TOKEN belum diisi di Script Properties.";
  }

  if(out.tiktok.configured){
    try{
      const creator=tiktokPublishRequest_("/post/publish/creator_info/query/",{});
      const code=String(creator&&creator.error&&creator.error.code||"");
      out.tiktok.api_ok=code==="ok" && Boolean(creator&&creator.data);
      if(out.tiktok.api_ok){
        out.tiktok.creator={
          username:String(creator.data.creator_username||""),
          privacy_level_options:Array(creator.data.privacy_level_options||[])
        };
      }else{
        out.tiktok.error="TikTok creator_info failed: "+JSON.stringify(creator).slice(0,900);
      }
    }catch(err){
      out.tiktok.error=String(err).slice(0,900);
    }
  }else{
    out.tiktok.error="TIKTOK_ACCESS_TOKEN belum diisi.";
  }

  out.ok=Boolean(out.webhook.meta_verify_token && out.instagram.api_ok);
  return json_(out);
}

function instagramGetHost_(host,path,params){
  const version=PropertiesService.getScriptProperties().getProperty("IG_API_VERSION")||"v26.0";
  const qs=Object.keys(params||{}).map(function(k){
    return encodeURIComponent(k)+"="+encodeURIComponent(String(params[k]));
  }).join("&");
  return urlFetchJson_(host+"/"+version+path+(qs?"?"+qs:""),{
    method:"get",
    headers:{Authorization:"Bearer "+instagramToken_()},
    muteHttpExceptions:true
  });
}

function socialHealth(){
  const result = socialHealth_();
  try {
    SpreadsheetApp.getUi().alert("SOCIAL HEALTH RESULT\n\n" + result);
  } catch (e) {
    console.log(result);
  }
  return result;
}

function doPost(e){
  try{
    const body=JSON.parse((e.postData&&e.postData.contents)||"{}");
    if(body && body.object==="instagram")return handleInstagramWebhook_(body);
    if(body && (body.event || body.webhook_event_type || body.client_key) && !body.action)return handleTikTokWebhook_(body);
    if(!auth_(body))return json_({ok:false,error:"Unauthorized"});
    const a=body.action||"ingest";
    if(a==="healthcheck")return liveHealth_();
    if(a==="social_health")return socialHealth_();
    if(a==="ingest")return ingest_(body.rows||[]);
    if(a==="repair_layout")return repairProspectLayout_();
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
    const newRow=prospectDataLastRow_(sh)+1;
    sh.getRange(newRow,1,1,HEADERS.length).setValues([o]);
    sh.getRange(newRow,col_("Manual Send"))
      .setDataValidation(SpreadsheetApp.newDataValidation().requireCheckbox().build())
      .setValue(false);
    existing[email]=true; added++;
  });
  return json_({ok:true,received:rows.length,added:added,duplicates:duplicates,no_email:noEmail});
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
  const planningRows=rows.filter(function(r){
    const mode=String(r.publish_mode||"");
    return mode==="PLANNING_ONLY" || mode==="AUTO_PUBLISH_DAILY";
  });
  const legacyRows=rows.filter(function(r){
    const mode=String(r.publish_mode||"");
    return mode!=="PLANNING_ONLY" && mode!=="AUTO_PUBLISH_DAILY";
  });
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
        r.slides_json||"",r.status||"PLANNED",String(r.publish_mode||"PLANNING_ONLY"),
        r.catatan||"Content plan"
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

function instagramGraphBase_(){
  const version=PropertiesService.getScriptProperties().getProperty("IG_API_VERSION")||"v26.0";
  const host=PropertiesService.getScriptProperties().getProperty("IG_GRAPH_HOST") ||
    PropertiesService.getScriptProperties().getProperty("IG_MESSAGING_HOST") ||
    "https://graph.instagram.com";
  return host+"/"+version;
}

function instagramToken_(){
  const token=PropertiesService.getScriptProperties().getProperty("IG_ACCESS_TOKEN")||"";
  if(!token)throw new Error("INSTAGRAM_ACCESS_TOKEN_NOT_CONFIGURED");
  return token;
}

function instagramUserId_(){
  const id=PropertiesService.getScriptProperties().getProperty("IG_USER_ID")||"";
  if(!id)throw new Error("IG_USER_ID_NOT_CONFIGURED");
  return id;
}

function instagramPost_(path,params){
  return urlFetchJson_(instagramGraphBase_()+path,{
    method:"post",
    payload:params||{},
    headers:{Authorization:"Bearer "+instagramToken_()},
    muteHttpExceptions:true
  });
}

function instagramGet_(path,params){
  const qs=Object.keys(params||{}).map(function(k){
    return encodeURIComponent(k)+"="+encodeURIComponent(String(params[k]));
  }).join("&");
  return urlFetchJson_(instagramGraphBase_()+path+(qs?"?"+qs:""),{
    method:"get",
    headers:{Authorization:"Bearer "+instagramToken_()},
    muteHttpExceptions:true
  });
}

function waitInstagramContainers_(ids){
  const pending=(ids||[]).map(String);
  if(!pending.length)return;
  for(let attempt=0;attempt<20;attempt++){
    let allReady=true;
    for(let i=0;i<pending.length;i++){
      const status=instagramGet_("/"+encodeURIComponent(pending[i]),{fields:"status_code,status"});
      const code=String(status.status_code||"").toUpperCase();
      if(code==="FINISHED")continue;
      if(code==="ERROR" || code==="EXPIRED")throw new Error("Instagram container "+pending[i]+" status="+JSON.stringify(status));
      allReady=false;
    }
    if(allReady)return;
    Utilities.sleep(3000);
  }
  throw new Error("Instagram media containers did not finish processing in time.");
}

function publishInstagramCarousel_(imageUrls,caption){
  const urls=(imageUrls||[]).map(String).filter(Boolean).slice(0,10);
  if(urls.length<2)throw new Error("Instagram carousel requires at least 2 image URLs.");
  if(urls.length>10)throw new Error("Instagram carousel supports at most 10 items.");
  const childIds=[];
  urls.forEach(function(url){
    const child=instagramPost_("/"+encodeURIComponent(instagramUserId_())+"/media",{
      image_url:url,
      is_carousel_item:"true"
    });
    if(!child.id)throw new Error("Instagram child container missing id: "+JSON.stringify(child));
    childIds.push(String(child.id));
  });
  waitInstagramContainers_(childIds);
  const parent=instagramPost_("/"+encodeURIComponent(instagramUserId_())+"/media",{
    media_type:"CAROUSEL",
    children:childIds.join(","),
    caption:String(caption||"").slice(0,2200)
  });
  if(!parent.id)throw new Error("Instagram carousel container missing id: "+JSON.stringify(parent));
  waitInstagramContainers_([String(parent.id)]);
  const published=instagramPost_("/"+encodeURIComponent(instagramUserId_())+"/media_publish",{
    creation_id:String(parent.id)
  });
  if(!published.id)throw new Error("Instagram carousel publish failed: "+JSON.stringify(published));
  return {ok:true,platform:"instagram",media_id:String(published.id),container_id:String(parent.id),children:childIds};
}

function publishInstagramPhoto_(imageUrl,caption){
  const url=String(imageUrl||"").trim();
  if(!url)throw new Error("Missing image_url");
  const container=instagramPost_("/"+encodeURIComponent(instagramUserId_())+"/media",{
    image_url:url,
    caption:String(caption||"").slice(0,2200)
  });
  if(!container.id)throw new Error("Instagram container not created: "+JSON.stringify(container));
  waitInstagramContainers_([String(container.id)]);
  const published=instagramPost_("/"+encodeURIComponent(instagramUserId_())+"/media_publish",{
    creation_id:String(container.id)
  });
  if(!published.id)throw new Error("Instagram publish failed: "+JSON.stringify(published));
  return {ok:true,platform:"instagram",media_id:String(published.id),container_id:String(container.id)};
}

function tiktokBaseUrl_(){
  return "https://open.tiktokapis.com/v2";
}

function tiktokPublishRequest_(path,payload){
  const token=tiktokToken_();
  return urlFetchJson_(tiktokBaseUrl_()+path,{
    method:"post",
    contentType:"application/json; charset=UTF-8",
    headers:{Authorization:"Bearer "+token},
    payload:JSON.stringify(payload),
    muteHttpExceptions:true
  });
}

function publishTikTokPhoto_(imageUrls,caption,title){
  const urls=(imageUrls||[]).map(String).filter(Boolean).slice(0,35);
  if(!urls.length)throw new Error("Missing TikTok photo URLs.");
  let creator=tiktokPublishRequest_("/post/publish/creator_info/query/",{});
  const options=((creator.data&&creator.data.privacy_level_options)||[]);
  const privacy=options.indexOf("PUBLIC_TO_EVERYONE")>=0
    ? "PUBLIC_TO_EVERYONE" : (options[0]||"SELF_ONLY");
  const payload={
    post_info:{
      title:String(title||"Sonjaya").slice(0,150),
      description:String(caption||"").slice(0,2200),
      privacy_level:privacy,
      disable_comment:false,
      auto_add_music:false,
      brand_organic_toggle:true
    },
    source_info:{
      source:"PULL_FROM_URL",
      photo_images:urls,
      photo_cover_index:0
    },
    post_mode:"DIRECT_POST",
    media_type:"PHOTO"
  };
  const result=tiktokPublishRequest_("/post/publish/content/init/",payload);
  if(result.error && result.error.code && result.error.code!=="ok"){
    throw new Error("TikTok publish failed: "+JSON.stringify(result.error));
  }
  const publishId=String(result.data&&result.data.publish_id||"");
  if(!publishId)throw new Error("TikTok publish_id missing: "+JSON.stringify(result));
  return {ok:true,platform:"tiktok",publish_id:publishId};
}

function contentPlanFindRow_(date,platform){
  const sh=contentPlanningSheet_(),last=sh.getLastRow();
  if(last<2)return -1;
  const vals=sh.getRange(2,1,last-1,CONTENT_PLAN_HEADERS.length).getValues();
  const dateKey=String(date||"");
  const platformKey=String(platform||"").toLowerCase();
  for(let i=0;i<vals.length;i++){
    const rowDate=String(vals[i][0]||"").slice(0,10);
    const rowPlatform=String(vals[i][1]||"").toLowerCase();
    if(rowDate===dateKey && rowPlatform.indexOf(platformKey)>=0)return i+2;
  }
  return -1;
}

function markContentPlanningPublished_(date,platform,result){
  const row=contentPlanFindRow_(date,platform);
  if(row<2)return;
  const sh=contentPlanningSheet_();
  sh.getRange(row,CONTENT_PLAN_HEADERS.indexOf("Status")+1).setValue(result.ok?"PUBLISHED":"PUBLISH_ERROR");
  sh.getRange(row,CONTENT_PLAN_HEADERS.indexOf("Catatan")+1).setValue(JSON.stringify(result).slice(0,1500));
}

function publishSocial_(body){
  const platform=String(body.platform||"").toLowerCase().trim();
  const dateKey=String(body.date||"").slice(0,10);
  const caption=String(body.caption||"").trim();
  const title=String(body.title||"Sonjaya").trim();
  const urls=Array.isArray(body.image_urls)?body.image_urls.map(String).filter(Boolean):[];
  if(!platform)return json_({ok:false,error:"Unsupported platform"});
  if(!dateKey)throw new Error("Missing date");
  if(!urls.length)throw new Error("Missing image_urls");
  const lock=LockService.getScriptLock();
  lock.waitLock(20000);
  try{
    const key="AUTO_PUBLISH:"+platform+":"+dateKey;
    const props=PropertiesService.getScriptProperties();
    const prior=props.getProperty(key);
    if(prior){
      return json_({ok:true,platform:platform,date:dateKey,duplicate:true,result:JSON.parse(prior)});
    }
    let result;
    if(platform==="instagram"){
      result=urls.length>=2?publishInstagramCarousel_(urls,caption):publishInstagramPhoto_(urls[0],caption);
    }else if(platform==="tiktok"){
      result=publishTikTokPhoto_(urls,caption,title);
    }else{
      return json_({ok:false,error:"Unsupported platform"});
    }
    props.setProperty(key,JSON.stringify(result));
    markContentPlanningPublished_(dateKey,platform,result);
    return json_({ok:true,platform:platform,date:dateKey,result:result});
  }catch(err){
    markContentPlanningPublished_(dateKey,platform,{ok:false,error:String(err)});
    throw err;
  }finally{
    try{lock.releaseLock();}catch(e){}
  }
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

function refreshTikTok_(){
  const clientId=PropertiesService.getScriptProperties().getProperty("TIKTOK_CLIENT_ID")||"";
  const clientSecret=PropertiesService.getScriptProperties().getProperty("TIKTOK_CLIENT_SECRET")||"";
  const refresh=PropertiesService.getScriptProperties().getProperty("TIKTOK_REFRESH_TOKEN")||"";
  if(!clientId||!clientSecret||!refresh)throw new Error("TIKTOK_REFRESH_NOT_CONFIGURED");
  const res=UrlFetchApp.fetch("https://business-api.tiktok.com/open_api/v1.3/tt_user/oauth2/refresh_token/",{
    method:"post",
    contentType:"application/json",
    payload:JSON.stringify({
      grant_type:"refresh_token",
      refresh_token:refresh,
      client_id:clientId,
      client_secret:clientSecret
    }),
    muteHttpExceptions:true
  });
  const code=res.getResponseCode(),txt=res.getContentText();
  let data={}; try{data=JSON.parse(txt||"{}");}catch(e){}
  if(code<200||code>=300||!data.data||!data.data.access_token){
    throw new Error("TikTok refresh HTTP "+code+": "+txt.slice(0,700));
  }
  const d=data.data;
  PropertiesService.getScriptProperties().setProperty("TIKTOK_ACCESS_TOKEN",d.access_token);
  if(d.refresh_token)PropertiesService.getScriptProperties().setProperty("TIKTOK_REFRESH_TOKEN",d.refresh_token);
  if(d.open_id)PropertiesService.getScriptProperties().setProperty("TIKTOK_BUSINESS_ID",d.open_id);
  return d.access_token;
}

function setup(){
  sheet_();contentSheet_();contentPlanningSheet_();socialLeadsSheet_();setupSocialAutomation_();
  const props=PropertiesService.getScriptProperties();
  if(!props.getProperty("IG_COMMENT_KEYWORD"))props.setProperty("IG_COMMENT_KEYWORD","REY MAU");
  if(!props.getProperty("IG_API_VERSION"))props.setProperty("IG_API_VERSION","v26.0");
  if(!props.getProperty("IG_MESSAGING_HOST"))props.setProperty("IG_MESSAGING_HOST","https://graph.facebook.com");
  if(!props.getProperty("IG_GRAPH_HOST"))props.setProperty("IG_GRAPH_HOST","https://graph.facebook.com");
  if(!props.getProperty("IG_COMMENT_KEYWORD"))props.setProperty("IG_COMMENT_KEYWORD","REY MAU");
  if(!props.getProperty("IG_PUBLIC_COMMENT_REPLY"))props.setProperty("IG_PUBLIC_COMMENT_REPLY","Siap! 👋 Cek DM ya.");
  if(!props.getProperty("TIKTOK_COMMENT_KEYWORD"))props.setProperty("TIKTOK_COMMENT_KEYWORD","REY MAU");
  if(!props.getProperty("TIKTOK_PUBLIC_COMMENT_REPLY"))props.setProperty("TIKTOK_PUBLIC_COMMENT_REPLY","Siap! 👋 Cek DM ya.");
  const triggers=ScriptApp.getProjectTriggers();
  if(!triggers.some(t=>t.getHandlerFunction()==="hourlyAutomation_")){
    ScriptApp.newTrigger("hourlyAutomation_").timeBased().everyHours(1).create();
  }
  const spreadsheetId=SpreadsheetApp.getActiveSpreadsheet().getId();
  if(!triggers.some(t=>t.getHandlerFunction()==="manualSendOnEdit_")){
    ScriptApp.newTrigger("manualSendOnEdit_").forSpreadsheet(spreadsheetId).onEdit().create();
  }
  backfillProspectControls_(SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_NAME));
  return "Sonjaya system ready | version "+CODE_VERSION;
}

function systemStatus(){
  return liveHealth_();
}

function hourlyAutomation_(){
  try{scanReplies_(20);}catch(e){console.log(e);}
  try{processFollowups_(MAX_FOLLOWUPS_PER_RUN);}catch(e){console.log(e);}
}

