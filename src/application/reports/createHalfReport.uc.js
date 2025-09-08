const HalfReport = require("../../infrastructure/models/halfReport.model");
const AppError = require("../../shared/utils/appError");

const createHalfReportUC = async ({form}) => {
  try {
    // 1️⃣ Validate required fields
    if (!form.reportTitle || form.reportTitle.trim() === "") {
      throw new AppError("Report title is required", 400);
    }

    if (!form.clients || !Array.isArray(form.clients) || form.clients.length === 0) {
      throw new AppError("At least one client is required", 400);
    }

    if (!form.valuers || !Array.isArray(form.valuers) || form.valuers.length === 0) {
      throw new AppError("At least one valuer is required", 400);
    }

    // 2️⃣ Validate valuers' total share
    const totalShare = form.valuers.reduce((acc, v) => acc + Number(v.share), 0);
    if (totalShare > 100) {
      throw new AppError("Total valuer share cannot exceed 100%", 400);
    }

    // 3️⃣ Construct the HalfReport document
    const halfReportData = {
      reportTitle: form.reportTitle,
      purposeOfAssessment: form.purpose || "",
      valueAssumption: form.valueAssumption || "",
      type: form.reportType || "",
      reviewDate: form.valueDate || "",
      issueDate: form.issueDate || "",
      assumptions: form.assumptions || "",
      specialAssumptions: form.specialAssumptions || "",
      finalValue: form.finalOpinion || "",
      valuationCurrency: form.currency || "",
      assetFile: form.file || "",

      clients: form.clients,
      hasOtherUsers: form.reportUsers && form.reportUsers.length > 0,
      reportUsers: form.reportUsers || [],

      valuers: form.valuers,
    };

    // 4️⃣ Save to MongoDB
    const newHalfReport = await HalfReport.create(halfReportData);

    return { success: true, data: newHalfReport };
  } catch (error) {
    if (error instanceof AppError) {
      return { success: false, message: error.message, statusCode: error.statusCode };
    }
    // System error (unexpected)
    console.error(error);
    return { success: false, message: "Something went wrong", statusCode: 500 };
  }
};

module.exports = createHalfReportUC;
