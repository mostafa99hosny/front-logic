const mongoose = require('mongoose');

const assetDataSchema = new mongoose.Schema({
    report_id: { type: String },
    id: { type: String },
    serial_no: { type: String },
    asset_type: { type: String },
    asset_name: { type: String },
    model: { type: String },
    year_made: { type: String },
    final_value: { type: String },
    asset_usage_id: { type: String }, // Changed from asset_usage to match Excel
    value_base: { type: String },
    inspection_date: { type: String },
    production_capacity: { type: String },
    production_capacity_measuring_unit: { type: String },
    owner_name: { type: String },
    product_type: { type: String },
    market_approach: { type: String },
    market_approach_value: { type: String },
    cost_approach: { type: String },
    cost_approach_value: { type: String },
    country: { type: String },
    region: { type: String },
    city: { type: String }
});

const AssetData = mongoose.model('AssetData', assetDataSchema);

module.exports = AssetData;