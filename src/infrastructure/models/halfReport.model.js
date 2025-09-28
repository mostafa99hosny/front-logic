const mongoose = require('mongoose');

const clientSchema = new mongoose.Schema({
  client_name: { type: String, required: true },
  telephone: { type: String, required: true },
  email: { type: String, required: true },
});

const valuerSchema = new mongoose.Schema({
  valuer_name: { type: String, required: true },
  contribution_percentage: { type: Number, required: true }, // percentage
});

const halfReportSchema = new mongoose.Schema({
  user_id: { type: String },
  report_id: { type: String },
  title: { type: String, required: true },
  purpose_id: { type: String },
  value_premise_id: { type: String },
  report_type: { type: String },
  valued_at: { type: String },
  submitted_at: { type: String },
  inspection_date: { type: String },
  assumptions: { type: String },
  special_assumptions: { type: String },
  value: { type: String },
  valuation_currency: { type: String },

  report_asset_file: { type: String },
  owner_name: { type: String },
  client_name: { type: String, required: true },

  telephone: { type: String, required: true },
  email: { type: String, required: true },
  has_other_users: { type: Boolean, default: false },
  report_users: { type: [String], default: [] },
  valuers: { type: [valuerSchema], required: true },
  country: { type: String, default: "المملكة العربية السعودية" },
  region: { type: String },
  city: { type: String },

  asset_data: [{
    id: { type: String },
    serial_no: { type: String },
    asset_type: { type: String, default: "0" },
    asset_name: { type: String },
    model: { type: String },
    year_made: { type: String },
    final_value: { type: String },
    asset_usage_id: { type: String },
    value_base: { type: String },
    inspection_date: { type: String },
    production_capacity: { type: String, default: "0" },
    production_capacity_measuring_unit: { type: String, default: "0" },
    owner_name: { type: String },
    product_type: { type: String, default: "0" },
    market_approach: { type: String },
    market_approach_value: { type: String },
    cost_approach: { type: String },
    cost_approach_value: { type: String },
  }],
}, { timestamps: true });

const HalfReport = mongoose.model('HalfReport', halfReportSchema);

// asset_type	asset_name	final_value	asset_usage_id	value_base	inspection_date	production_capacity	production_capacity_measuring_unit	owner_name	product_type	market_approach	market_approach_value	cost_approach	cost_approach_value	country	region	city

module.exports = HalfReport;

// const mongoose = require('mongoose');

// const clientSchema = new mongoose.Schema({
//   client_name: { type: String, required: true },
//   telephone_number: { type: String, required: true },
//   email_address: { type: String, required: true },
// });

// const valuerSchema = new mongoose.Schema({
//   valuer_name: { type: String, required: true },
//   contribution_percentage: { type: Number, required: true }, // percentage
// });

// const halfReportSchema = new mongoose.Schema({
//   report_id: { type: String },
//   report_title: { type: String, required: true },
//   valuation_purpose: { type: String },
//   value_premise: { type: String },
//   report_type: { type: String },
//   valuation_date: { type: String },
//   report_issuing_date: { type: String },
//   assumptions: { type: String },
//   special_assumptions: { type: String },
//   final_value: { type: String },
//   valuation_currency: { type: String },

//   report_asset_file: { type: String }, 

//   clients: { type: [clientSchema], required: true },
//   has_other_users: { type: Boolean, default: false },
//   report_users: { type: [String], default: [] },
//   valuers: { type: [valuerSchema], required: true },

//   asset_data: [{
//     id: { type: String },
//     serial_no: { type: String },
//     asset_type: { type: String },
//     asset_name: { type: String },
//     model: { type: String },
//     year_made: { type: String },
//     final_value: { type: String },
//     asset_usage_id: { type: String }, // Changed from asset_usage to match Excel
//     value_base: { type: String },
//     inspection_date: { type: String },
//     production_capacity: { type: String },
//     production_capacity_measuring_unit: { type: String },
//     owner_name: { type: String },
//     product_type: { type: String },
//     market_approach: { type: String },
//     market_approach_value: { type: String },
//     cost_approach: { type: String },
//     cost_approach_value: { type: String },
//     country: { type: String },
//     region: { type: String },
//     city: { type: String }
//   }],
// }, { timestamps: true });

// const HalfReport = mongoose.model('HalfReport', halfReportSchema);
