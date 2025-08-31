// front-logic/src/infrastructure/models/report.model.js
const mongoose = require('mongoose');

const reportSchema = new mongoose.Schema({
  reportName: {
    type: String,
    required: true
  },
  reportType: {
    type: String,
    required: true,
    default: 'XLSX'
  },
  source: {
    type: String,
    required: true
  },
  size: {
    type: String,
    default: ''
  },
  date: {
    type: Date,
    default: Date.now
  },
  status: {
    type: String,
    enum: ['مكتمل', 'معلق', 'قيد المعالجة', 'فشل'], // completed, pending, processing, failed
    default: 'مكتمل'
  },
  equipmentType: {
    type: String,
    default: ''
  },
  location: {
    type: String,
    default: ''
  },
  referenceNo: {
    type: String,
    required: true,
    unique: true
  },
  quantity: {
    type: String,
    default: '1'
  },
  condition: {
    type: String,
    default: ''
  },
  propertyType: {
    type: String,
    default: ''
  },
  reference: {
    type: String,
    default: null
  },
  site: {
    type: String,
    default: null
  },
  name: {
    type: String,
    default: null
  },
  area: {
    type: String,
    default: '1 م²'
  },
  value: {
    type: Number,
    default: 0
  },
  priority: {
    type: String,
    enum: ['High', 'middle', 'low'],
    default: 'middle'
  },
  procedures: {
    type: [String],
    default: []
  },
  presentedBy: {
    type: String,
    default: 'نظام المعلومات'
  }
}, {
  timestamps: true
});

// Create indexes for better query performance
reportSchema.index({ date: -1 });
reportSchema.index({ referenceNo: 1 });
reportSchema.index({ reportName: 'text' });
reportSchema.index({ site: 1 });
reportSchema.index({ propertyType: 1 });
reportSchema.index({ condition: 1 });

module.exports = mongoose.model('Report', reportSchema);