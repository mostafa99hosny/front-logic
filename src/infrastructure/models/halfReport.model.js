const mongoose = require('mongoose');

const clientSchema = new mongoose.Schema({
  name: { type: String, required: true },
  phone: { type: String, required: true },
  email: { type: String, required: true },
});

const valuerSchema = new mongoose.Schema({
  name: { type: String, required: true },
  share: { type: Number, required: true }, // percentage
});

const halfReportSchema = new mongoose.Schema({
  reportTitle: { type: String, required: true },
  purposeOfAssessment: { type: String },
  valueAssumption: { type: String },
  type: { type: String }, // reportType
  reviewDate: { type: String }, // valueDate
  issueDate: { type: String },
  assumptions: { type: String },
  specialAssumptions: { type: String },
  finalValue: { type: String }, // finalOpinion
  valuationCurrency: { type: String },
  assetFile: { 
    data: Buffer,
    contentType: String
   },

  clients: { type: [clientSchema], required: true }, // array of clients
  hasOtherUsers: { type: Boolean, default: false },
  reportUsers: { type: [String], default: [] }, // other beneficiaries

  valuers: { type: [valuerSchema], required: true }, // array of valuers
}, { timestamps: true });

const HalfReport = mongoose.model('HalfReport', halfReportSchema);

module.exports = HalfReport;
