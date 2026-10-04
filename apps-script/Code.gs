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
    const token = PropertiesService
      .getScriptProperties()
      .getProperty("WEBHOOK_TOKEN");

    const body = JSON.parse(
      e.postData.contents || "{}"
    );

    if (!token || body.token !== token) {
      return json_({
        ok: false,
        error: "Unauthorized"
      });
    }

    const rows = Array.isArray(body.rows)
      ? body.rows
      : [];

    const sh = getSheet_();

    const existing = new Set();

    if (sh.getLastRow() >= 2) {
      const urls = sh
        .getRange(
          2,
          4,
          sh.getLastRow() - 1,
          1
        )
        .getValues();

      urls.forEach(row => {
        if (row[0]) {
          existing.add(
            String(row[0])
              .toLowerCase()
              .trim()
          );
        }
      });
    }

    let added = 0;

    rows.forEach(row => {
      const url = String(
        row.url_instagram || ""
      ).trim();

      if (!url) return;

      const key = url.toLowerCase();

      if (existing.has(key)) {
        return;
      }

      sh.appendRow([
        row.tanggal_ditemukan || "",
        row.nama_bisnis || "",
        row.instagram || "",
        url,
        row.kota || "",
        row.kategori || "",
        row.bukti_publik || "",
        Number(row.skor || 0),
        row.alasan || "",
        row.prioritas || "",
        row.status || "BELUM DI-DM",
        row.catatan_dm || ""
      ]);

      existing.add(key);
      added++;
    });

    sh.getDataRange().setWrap(true);

    return json_({
      ok: true,
      received: rows.length,
      added: added,
      duplicates: rows.length - added
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
    .createTextOutput(
      JSON.stringify(obj)
    )
    .setMimeType(
      ContentService.MimeType.JSON
    );
}
