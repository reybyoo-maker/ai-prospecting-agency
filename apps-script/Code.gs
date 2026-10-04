const SHEET_NAME = "Leads";
const HEADERS = [
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
  "Catatan DM",
  "Template Chat"
];

function setupHeaders_() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sh = ss.getSheetByName(SHEET_NAME);

  if (!sh) {
    sh = ss.insertSheet(SHEET_NAME);
  }

  const lastColumn = Math.max(
    sh.getLastColumn(),
    1
  );

  const currentHeaders = sh
    .getRange(
      1,
      1,
      1,
      lastColumn
    )
    .getValues()[0];

  if (
    sh.getLastRow() === 0 ||
    !currentHeaders[0]
  ) {
    sh.getRange(
      1,
      1,
      1,
      HEADERS.length
    ).setValues([HEADERS]);
  } else {
    const needed = [];

    HEADERS.forEach(header => {
      if (!currentHeaders.includes(header)) {
        needed.push(header);
      }
    });

    if (needed.length) {
      sh.getRange(
        1,
        currentHeaders.length + 1,
        1,
        needed.length
      ).setValues([needed]);
    }
  }

  sh.setFrozenRows(1);
  sh.getRange(1, 1, 1, HEADERS.length)
    .setFontWeight("bold");

  return sh;
}


function makeChatTemplate_(business, instagram, category, city) {
  business = String(business || instagram || "kak").trim();
  instagram = String(instagram || "").trim();
  category = String(category || "bisnis kakak").trim();
  city = String(city || "").trim();

  const location = city ? ` di ${city}` : "";

  return (
    `Halo kak, izin kenalan. Saya Rey. ` +
    `Saya menemukan akun @${instagram} dan melihat ${business} ` +
    `punya potensi bagus untuk diarahkan ke landing page yang lebih rapi. ` +
    `Untuk ${category}${location}, landing page bisa membantu calon customer ` +
    `melihat layanan, promo, dan langsung chat tanpa harus mencari-cari informasi. ` +
    `Saya menyediakan jasa landing page yang bisa disesuaikan dengan kebutuhan bisnis. ` +
    `Boleh saya kirim contoh portofolionya kak?`
  );
}

function backfillChatTemplates_() {
  const sh = setupHeaders_();
  const lastRow = sh.getLastRow();

  if (lastRow < 2) {
    SpreadsheetApp.getUi().alert(
      "Belum ada data prospek."
    );
    return;
  }

  const rows = sh.getRange(
    2,
    1,
    lastRow - 1,
    HEADERS.length
  ).getValues();

  const index = {};
  HEADERS.forEach((h, i) => {
    index[h] = i;
  });

  let changed = 0;

  rows.forEach(row => {
    const existing = String(
      row[index["Template Chat"]] || ""
    ).trim();

    if (existing) return;

    const business = row[index["Nama bisnis"]];
    const instagram = row[index["Instagram"]];
    const category = row[index["Kategori"]];
    const city = row[index["Kota"]];

    if (!business && !instagram) return;

    row[index["Template Chat"]] =
      makeChatTemplate_(
        business,
        instagram,
        category,
        city
      );

    changed++;
  });

  sh.getRange(
    2,
    1,
    rows.length,
    HEADERS.length
  ).setValues(rows);

  sh.getDataRange().setWrap(true);

  SpreadsheetApp.getUi().alert(
    `${changed} template chat berhasil dibuat.`
  );
}

function onOpen() {
  setupHeaders_();

  SpreadsheetApp.getUi()
    .createMenu("Prospecting")
    .addItem(
      "Setup / Perbaiki Kolom",
      "setupHeaders_"
    )
    .addItem(
      "Buat Template Chat Semua Baris",
      "backfillChatTemplates_"
    )
    .addItem(
      "📋 Copy Template Chat",
      "showChatSidebar"
    )
    .addToUi();
}

function doPost(e) {
  try {
    const expected = PropertiesService
      .getScriptProperties()
      .getProperty("WEBHOOK_TOKEN");

    const body = JSON.parse(
      e.postData.contents || "{}"
    );

    if (
      !expected ||
      body.token !== expected
    ) {
      return json_({
        ok: false,
        error: "Unauthorized"
      });
    }

    const rows = Array.isArray(body.rows)
      ? body.rows
      : [];

    const sh = setupHeaders_();

    const existing = new Set();

    if (sh.getLastRow() >= 2) {
      const urlColumn = HEADERS.indexOf(
        "URL Instagram"
      ) + 1;

      sh.getRange(
        2,
        urlColumn,
        sh.getLastRow() - 1,
        1
      ).getValues().forEach(row => {
        if (row[0]) {
          existing.add(
            String(row[0])
              .toLowerCase()
              .trim()
          );
        }
      });
    }

    const rowIndex = {};
    HEADERS.forEach(
      (header, index) => {
        rowIndex[header] = index;
      }
    );

    let added = 0;

    rows.forEach(row => {
      const url = String(
        row.url_instagram || ""
      ).trim();

      if (!url) return;

      const key = url.toLowerCase();

      if (existing.has(key)) return;

      const output = new Array(
        HEADERS.length
      ).fill("");

      output[
        rowIndex["Tanggal ditemukan"]
      ] = row.tanggal_ditemukan || "";

      output[
        rowIndex["Nama bisnis"]
      ] = row.nama_bisnis || "";

      output[
        rowIndex["Instagram"]
      ] = row.instagram || "";

      output[
        rowIndex["URL Instagram"]
      ] = url;

      output[
        rowIndex["Kota"]
      ] = row.kota || "";

      output[
        rowIndex["Kategori"]
      ] = row.kategori || "";

      output[
        rowIndex["Bukti publik"]
      ] = row.bukti_publik || "";

      output[
        rowIndex["Skor"]
      ] = Number(row.skor || 0);

      output[
        rowIndex["Alasan"]
      ] = row.alasan || "";

      output[
        rowIndex["Prioritas"]
      ] = row.prioritas || "";

      output[
        rowIndex["Status"]
      ] = row.status || "BELUM DI-DM";

      output[
        rowIndex["Catatan DM"]
      ] = row.catatan_dm || "";

      output[
        rowIndex["Template Chat"]
      ] = row.template_chat || "";

      sh.appendRow(output);

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

  } catch (err) {
    return json_({
      ok: false,
      error: String(err)
    });
  }
}

function showChatSidebar() {
  const sh = setupHeaders_();
  const row = sh.getActiveRange().getRow();

  if (row < 2) {
    SpreadsheetApp.getUi().alert(
      "Pilih satu baris prospek terlebih dahulu."
    );
    return;
  }

  const values = sh
    .getRange(
      row,
      1,
      1,
      HEADERS.length
    )
    .getValues()[0];

  const data = {};

  HEADERS.forEach(
    (header, index) => {
      data[header] =
        values[index] == null
          ? ""
          : String(values[index]);
    }
  );

  const template = data["Template Chat"];

  if (!template) {
    SpreadsheetApp.getUi().alert(
      "Template Chat masih kosong. Jalankan agent versi terbaru terlebih dahulu."
    );
    return;
  }

  const html = HtmlService.createTemplateFromFile(
    "ChatSidebar"
  );

  html.chat = template;
  html.business =
    data["Nama bisnis"] || data["Instagram"] || "";

  SpreadsheetApp.getUi().showSidebar(
    html.evaluate()
      .setTitle("Template Chat")
      .setWidth(360)
  );
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
