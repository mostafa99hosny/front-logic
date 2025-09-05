// front-logic/src/infrastructure/models/report.model.js
const mongoose = require('mongoose');

// Schema for the offers array within payload
const offerSchema = new mongoose.Schema({
  sell_date: String,
  subject_type: String,
  comp_type: String,
  land_area: String,
  build_area: String,
  total_price: String,
  source: String,
  streets_count: Number,
  street_width: String,
  description: String,
  coordinates: String
}, { _id: false });

// Main payload schema matching the new DB structure
const payloadSchema = new mongoose.Schema({
  estimation_reason: String,
  estimation_base: String,
  actual_evaluation_date_m: String,
  actual_inspection_date_m: String,
  client_name: String,
  property_type: String,
  property_use: String,
  location: String,
  approach_market: String,
  approach_income: String,
  approach_cost: String,
  final_valuation_value: String,
  latitude: String,
  longitude: String,
  plan_no: String,
  parcel_no: String,
  title_deed_no: String,
  land_area: String,
  street_view: String,
  offers: [offerSchema],
  ownership_type: String,
  scraped_at: String
}, { _id: false });

// Main report schema matching the new simplified structure
const reportSchema = new mongoose.Schema({
  type: {
    type: String,
    required: true,
    default: "eval_model_scraped"
  },
  query: {
    type: String,
    required: true
  },
  payload: {
    type: payloadSchema,
    required: true
  },
  ts: {
    type: Date,
    default: Date.now
  }
}, {
  timestamps: false, // Using ts field instead
  collection: 'reports'
});

// Add indexes for better query performance
reportSchema.index({ 'type': 1 });
reportSchema.index({ 'query': 1 });
reportSchema.index({ 'payload.client_name': 'text' });
reportSchema.index({ 'payload.location': 'text' });
reportSchema.index({ 'payload.property_type': 1 });
reportSchema.index({ 'payload.property_use': 1 });
reportSchema.index({ 'payload.actual_evaluation_date_m': -1 });
reportSchema.index({ 'payload.actual_inspection_date_m': -1 });
reportSchema.index({ 'payload.final_valuation_value': 1 });
reportSchema.index({ 'payload.title_deed_no': 1 });
reportSchema.index({ 'payload.latitude': 1, 'payload.longitude': 1 });
reportSchema.index({ 'ts': -1 });

module.exports = mongoose.model('Report', reportSchema);