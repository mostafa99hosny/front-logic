const fs = require("fs");
const ExcelJS = require("exceljs/dist/es5");

const HalfReport = require("../../infrastructure/models/halfReport.model");
const AssetData = require("../../infrastructure/models/assetData.model");

const {
  checkMissingColumns,
  validateAll,
} = require("./validator");

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
    if (!worksheet) throw new Error("No worksheet found in Excel file");

    let headerRowNumber = 1;
    let headers = [];
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
        break;
      }
    }

    if (headers.length === 0) {
      headers = worksheet.getRow(1).values.slice(1).map(h => String(h).trim().toLowerCase());
      console.warn("⚠️ Could not auto-detect headers, falling back to row 1:", headers);
    }

    const rows = [];
    for (let rowNumber = headerRowNumber + 1; rowNumber <= worksheet.rowCount; rowNumber++) {
      const row = worksheet.getRow(rowNumber);
      if (row.actualCellCount === 0) continue;

      const values = headers.map((header, idx) => {
        const cell = row.getCell(idx + 1);
        if (cell.value && typeof cell.value === "object" && cell.value.result !== undefined) {
          return String(cell.value.result);
        } else if (cell.value && typeof cell.value === "object" && cell.value.formula) {
          return String(cell.value.result || cell.value);
        }
        return cell.value !== null && cell.value !== undefined ? String(cell.value) : "";
      });

      if (values.some(v => v !== "")) rows.push(values);
    }

    console.log(`✅ Parsed ${rows.length} data rows`);

    // --- VALIDATION ---
    // --- VALIDATION ---
    const missing = checkMissingColumns(headers);
    if (missing.length) {
      console.error("❌ Missing required columns:", missing);
      return {
        status: "FAILED",
        error: "Missing required columns",
        details: missing
      };
    }

    const { rows: validatedRows, highlights, summary } = validateAll(rows, headers);

    // Collect detailed error logs
    const errorDetails = [];
    Object.keys(highlights).forEach(key => {
      const [rowIdx, col] = key.split(",");
      const header = col; // already column name
      const cellValue = validatedRows[rowIdx][headers.indexOf(header)];
      errorDetails.push({
        row: parseInt(rowIdx) + 2, // +2 because headerRowNumber + 1 is first data row
        column: header,
        value: cellValue
      });
    });

    const hasErrors = summary.some(msg => msg.startsWith("❌"));
    if (hasErrors) {
      console.error("❌ Validation errors found:");
      errorDetails.forEach(err => {
        console.error(
          `Row ${err.row}, Column "${err.column}": Problematic value -> ${JSON.stringify(err.value)}`
        );
      });

      return {
        status: "FAILED",
        error: "Validation failed",
        highlights
      };
    }


    const assetRecords = validatedRows.map(r => {
      const rec = {};
      headers.forEach((h, i) => rec[h] = r[i]);
      return rec;
    });

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

    try { if (fs.existsSync(excelFilePath)) fs.unlinkSync(excelFilePath); } catch { }
    return { status: "SUCCESS", data: saved, summary };

  } catch (err) {
    console.error("[extractAssetData] error", err);
    return { status: "FAILED", error: err.message };
  }
}


module.exports = extractAssetData;
