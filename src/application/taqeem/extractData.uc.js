const fs = require("fs");
const path = require("path");
const ExcelJS = require('exceljs/dist/es5');
const TaqeemForm = require("../../infrastructure/models/taqeemForm.model");
const { v4: uuidv4 } = require("uuid");

const headerMap = {
  "Report Title": "reportTitle",
  "Valuation Purpose": "valuationPurpose",
  "Value Premise": "valuePremise",
  "Value Base": "valueBase",
  "Report Type": "reportType",
  "Valuation Date": "valuationDate",
  "Report Issuing Date": "reportIssuingDate",
  "Assumptions": "assumptions",
  "Special Assumptions": "specialAssumptions",
  "Final Value": "finalValue",
  "Valuation Currency": "valuationCurrency",
  "Report Asset File": "reportAssetFile",
  "Client Name": "clientName",
  "Telephone Number": "telephoneNumber",
  "E-mail Address": "emailAddress",
  "The report has other users": "hasOtherUsers",
  "Report User Name": "reportUser",
  "Valuer Name": "valuerName",
  "Contribution Percentage": "contributionPercentage",
  "Type of Asset Being Valued": "assetType",
  "Asset Being Valued Usage\\Sector": "assetUsageSector",
  "Inspection Date": "inspectionDate",
  "Market Approach": "marketApproach",
  "Comparable Transactions Method": "comparableTransactionsMethod",
  "Income Approach": "incomeApproach",
  "Profit Method": "profitMethod",
  "Cost Approach": "costApproach",
  "Summation Method": "summationMethod",
  "Country": "country",
  "Region": "region",
  "City": "city",
  "Latitude": "latitude",
  "Longitude": "longitude",
  "Certificate Number": "certificateNumber",
  "Ownership Type": "ownershipType",
  "Street facing fronts": "streetFacingFronts",
  "Facilities": "facilities",
  "Land Area": "landArea",
  "Building Area": "buildingArea",
  "Authorized Land Cover Percentage": "authorizedLandCoverPercentage",
  "Authorized height": "authorizedHeight",
  "The land of this building is leased": "landLeased",
  "Building Status": "buildingStatus",
  "Finishing Status": "finishingStatus",
  "Furnishing Status": "furnishingStatus",
  "Air Conditioning": "airConditioning",
  "Building Type": "buildingType",
  "Other Features": "otherFeatures",
  "The current use is considered the best use": "bestUse",
  "Asset Age": "assetAge",
  "Street width": "streetWidth"
};

async function extractData(filePath, pdfPaths) {
  console.log("[extractData] starting with", { filePath, pdfCount: pdfPaths?.length });
  try {

    console.log("Entering try block");

    const workbook = new ExcelJS.Workbook();
    await workbook.xlsx.readFile(filePath);

    const worksheet = workbook.worksheets[0];
    if (!worksheet) {
      throw new Error("No worksheet found in Excel file");
    }

    console.log("checking worksheet");

    const headers = worksheet.getRow(1).values
      .slice(1)
      .map(h => String(h || "").trim());

    console.log("headers", headers);

    const records = [];
    worksheet.eachRow((row, rowNumber) => {
      if (rowNumber === 1) return;
      const values = row.values.slice(1);
      const record = {};
      headers.forEach((header, idx) => {
        const key = headerMap[header];
        if (key) {
          record[key] = values[idx] ?? "";
        }
      });
      records.push(record);
    });

    console.log("records", records);

    const pdfLookup = {};
    pdfPaths.forEach(pdfPath => {
      pdfLookup[path.basename(pdfPath)] = path.resolve(pdfPath);
    });

    console.log("pdfLookup", pdfLookup);

    const batchId = uuidv4();

    const enriched = records.map(record => {
      const pdfName = String(record["reportAssetFile"] || "").trim();
      return {
        ...record,
        batchId,
        reportAssetFile: pdfName && pdfLookup[pdfName] ? path.normalize(pdfLookup[pdfName]) : ""
      };
    });

    const inserted = await TaqeemForm.insertMany(enriched);

    console.log(`✅ Inserted ${inserted.length} records with batchId=${batchId}`);

    const check = await TaqeemForm.find({ batchId });
    console.log("check", check);

    try {
      if (fs.existsSync(filePath)) {
        fs.unlinkSync(filePath);
      }
    } catch (delErr) {
      return {
        status: "SUCCESS",
        batchId,
        data: inserted,
        warning: `Cleanup error: ${delErr.message}`
      };
    }

    return { status: "SUCCESS", batchId, data: inserted };

  } catch (err) {
    return { status: "FAILED", error: err.message };
  }
}

module.exports = extractData;
