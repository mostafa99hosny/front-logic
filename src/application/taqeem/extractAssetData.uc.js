const fs = require("fs");
const ExcelJS = require("exceljs/dist/es5");

const HalfReport = require("../../infrastructure/models/halfReport.model");
const AssetData = require("../../infrastructure/models/assetData.model");

async function extractAssetData(excelFilePath, pdfFilePath = null, baseData, { mode = "halfReport", reportId = null, userId } = {}) {
  console.log("[extractAssetData] starting with", { excelFilePath, pdfFilePath, mode, reportId });
  
  let parsedBaseData = {};
  if (baseData) {
    try {
      parsedBaseData =
        typeof baseData === "string"
          ? JSON.parse(baseData)
          : baseData;
    } catch (err) {
      throw new Error("Invalid baseData JSON");
    }
  }

  try {
    const workbook = new ExcelJS.Workbook();
    await workbook.xlsx.readFile(excelFilePath);
    
    const worksheet = workbook.worksheets[0];
    if (!worksheet) {
      throw new Error("No worksheet found in Excel file");
    }

    let headerRowNumber = 1;
    let headers = [];
    let foundCorrectHeaders = false;

    for (let rowNum = 1; rowNum <= Math.min(10, worksheet.rowCount); rowNum++) {
      const row = worksheet.getRow(rowNum);
      const potentialHeaders = [];

      row.eachCell({ includeEmpty: false }, (cell) => {
        potentialHeaders.push(String(cell.value).trim().toLowerCase());
      });

      const expectedColumns = ["serial_no", "asset_type", "asset_name", "model", "year_made", "final_value"];
      const foundCount = potentialHeaders.filter(header =>
        expectedColumns.some(expected => header.includes(expected))
      ).length;

      if (foundCount >= 3) {
        headers = potentialHeaders;
        headerRowNumber = rowNum;
        foundCorrectHeaders = true;
        console.log(`✅ Found headers at row ${rowNum}:`, headers);
        break;
      }
    }

    if (!foundCorrectHeaders) {
      const headerRow = worksheet.getRow(1);
      headers = [];
      headerRow.eachCell({ includeEmpty: false }, (cell) => {
        headers.push(String(cell.value).trim().toLowerCase());
      });
      console.warn("⚠️ Could not find expected headers, using row 1:", headers);
    }

    const assetRecords = [];
    for (let rowNumber = headerRowNumber + 1; rowNumber <= worksheet.rowCount; rowNumber++) {
      const row = worksheet.getRow(rowNumber);
      if (row.actualCellCount === 0) continue;

      const record = {};
      let isEmptyRow = true;

      headers.forEach((header, idx) => {
        const cell = row.getCell(idx + 1);
        let value = "";

        if (cell.value && typeof cell.value === "object" && cell.value.result !== undefined) {
          value = String(cell.value.result);
        } else if (cell.value && typeof cell.value === "object" && cell.value.formula) {
          value = String(cell.value.result || cell.value);
        } else {
          value = cell.value !== null && cell.value !== undefined ? String(cell.value) : "";
        }

        record[header] = value;
        if (value) isEmptyRow = false;
      });

      if (!isEmptyRow) {
        assetRecords.push(record);
      }
    }

    console.log(`✅ Parsed ${assetRecords.length} assets`);

    let saved;

    if (mode === "halfReport") {
      const halfReportDoc = new HalfReport({
        ...parsedBaseData,
        report_asset_file: pdfFilePath || null,
        asset_data: assetRecords,
      });
      saved = await halfReportDoc.save();

    } else if (mode === "assetData") {
      if (!reportId) throw new Error("reportId required for assetData mode");

      const docs = assetRecords.map((rec) => ({
        ...rec,
        report_id: reportId,
        user_id: userId,
      }));
      saved = await AssetData.insertMany(docs);
    }

    try {
      if (fs.existsSync(excelFilePath)) {
        fs.unlinkSync(excelFilePath);
      }
    } catch (delErr) {
      return { status: "SUCCESS", data: saved, warning: `Cleanup error: ${delErr.message}` };
    }

    return { status: "SUCCESS", data: saved };

  } catch (err) {
    console.error("[extractAssetData] error", err);
    return { status: "FAILED", error: err.message };
  }
}

module.exports = extractAssetData;
