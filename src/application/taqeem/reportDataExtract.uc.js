const fs = require('fs');
const ExcelJS = require('exceljs/dist/es5');

const HalfReport = require('../../infrastructure/models/halfReport.model');

const reportDataExtract = async (excelFilePath, pdfFilePaths = null, userId) => {
    try {
        const workbook = new ExcelJS.Workbook();
        await workbook.xlsx.readFile(excelFilePath);
        const sheets = workbook.worksheets;

        if (sheets.length < 3) throw new Error("Expected 3 sheets: baseData, marketAssets, costAssets");

        const baseSheet = sheets[0];
        const baseData = {};

        const getCellValue = (cell) => {
            if (!cell) return '';

            const value = cell.value;

            if (value === null || value === undefined) return '';

            if (typeof value === 'object' && value.hasOwnProperty('formula')) {
                return getCellValue({ value: value.result });
            }

            if (value instanceof Date) {
                const yyyy = value.getFullYear();
                const mm = String(value.getMonth() + 1).padStart(2, '0'); // months are 0-indexed
                const dd = String(value.getDate()).padStart(2, '0');
                return `${yyyy}-${mm}-${dd}`; // format: YYYY-MM-DD
            }

            if (typeof value === 'object' && value.hasOwnProperty('text')) {
                return String(value.text);
            }

            return String(value);
        };

        const headerRow = baseSheet.getRow(1);
        const valueRow = baseSheet.getRow(2);

        headerRow.eachCell((cell, colNumber) => {
            const key = String(cell.value).trim().toLowerCase();
            const value = getCellValue(valueRow.getCell(colNumber));

            if (key === 'valuers' || key === 'valuer_name') {
                baseData.valuers = [{
                    valuer_name: valueRow.getCell(headerRow.values.indexOf('valuer_name')).value,
                    contribution_percentage: valueRow.getCell(headerRow.values.indexOf('contribution_percentage')).value
                }];

            } else {
                baseData[key] = value;
            }
        });


        const parseAssetSheet = (sheet, isMarket) => {
            const rows = [];
            const headerRow = sheet.getRow(1);
            const headers = headerRow.values.slice(1).map(h => String(h).trim().toLowerCase());

            for (let rowNum = 2; rowNum <= sheet.rowCount; rowNum++) {
                const row = sheet.getRow(rowNum);
                if (row.actualCellCount === 0) continue;

                const asset = {};
                headers.forEach((header, idx) => {
                    const value = row.getCell(idx + 1).value;
                    asset[header] = value !== undefined && value !== null ? String(value) : "";
                });

                if (isMarket) {
                    asset.market_approach_value = asset.final_value || "0";
                    asset.market_approach  = "1";
                } else {
                    asset.cost_approach_value = asset.final_value || "0";
                    asset.cost_approach  = "1";
                }

                rows.push(asset);
            }
            return rows;
        };

        const marketAssetsSheet = sheets[1];
        const marketAssets = parseAssetSheet(marketAssetsSheet, true);

        const costAssetsSheet = sheets[2];
        const costAssets = parseAssetSheet(costAssetsSheet, false);

        const allAssets = [...marketAssets, ...costAssets];

        

        const halfReportDoc = new HalfReport({
            ...baseData,
            user_id: userId,
            report_asset_file: pdfFilePaths || null,
            asset_data: allAssets
        });

        const saved = await halfReportDoc.save();

        try { if (fs.existsSync(excelFilePath)) fs.unlinkSync(excelFilePath); } catch { }

        return { status: "SUCCESS", data: saved };

    } catch (err) {
        console.error("[reportDataExtract] error:", err);
        return { status: "FAILED", error: err.message };
    }
};

module.exports = reportDataExtract;
