const SHEET_NAME = "Leads";

function getSheet_() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sh = ss.getSheetByName(SHEET_NAME);

  if (!sh) {
    sh = ss.insertSheet(SHEET_NAME);
  }

  if (sh.getLastRow() === 0) {
    sh.appendRow([
      "Tanggal ditemukan",
      "Nama bisnis",
      "Instagram",
      "URL Instagram",
      "Kota",
      "Kategori",
      "Bukti publik",
      "Skor",
      "Alasan",
      "Prioritas",
      "Status",
      "Catatan DM"
    ]);
    sh.setFrozenRows(1);
  }

  return sh;
}

function doPost(e) {
  try {
    const expected = PropertiesService
      .getScriptProperties()
      .getProperty("WEBHOOK_TOKEN");

    const data = JSON.parse(e.postData.contents || "{}");

    if (!expected || data.token !== expected) {
      return json_({ ok: false, error: "Unauthorized" });
    }

    const rows = Array.isArray(data.rows) ? data.rows : [];
    const sh = getSheet_();

    const lastRow = sh.getLastRow();
    const existing = new Set();

    if (lastRow >= 2) {
      sh.getRange(2, 4, lastRow - 1, 1)
        .getValues()
        .forEach(row => {
          if (row[0]) {
            existing.add(
              String(row[0]).toLowerCase().trim()
            );
          }
        });
    }

    let added = 0;

    rows.forEach(x => {
      const url = String(x.url_instagram || "").trim();

      if (!url) return;

      const key = url.toLowerCase();

      if (existing.has(key)) {
        return;
      }

      sh.appendRow([
        x.tanggal_ditemukan || "",
        x.nama_bisnis || "",
        x.instagram || "",
        url,
        x.kota || "",
        x.kategori || "",
        x.bukti_publik || "",
        Number(x.skor || 0),
        x.alasan || "",
        x.prioritas || "",
        x.status || "BELUM DI-DM",
        x.catatan_dm || ""
      ]);

      existing.add(key);
      added++;
    });

    sh.getDataRange().setWrap(true);

    return json_({
      ok: true,
      received: rows.length,
      added: added,
      duplicate_skipped: rows.length - added
    });

  } catch (error) {
    return json_({
      ok: false,
      error: String(error)
    });
  }
}

function doGet() {
  return json_({
    ok: true,
    service: "AI Prospecting Agency",
    sheet: SHEET_NAME
  });
}

function json_(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
