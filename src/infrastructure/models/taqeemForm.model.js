const mongoose = require('mongoose');

const taqeemFormSchema = new mongoose.Schema({
  batchId: { type: String, index: true }, 
  status: { 
    type: String, 
    enum: ['pending', 'in_progress', 'filled', 'failed'], 
    default: 'pending',
    index: true
  },
  retries: { type: Number, default: 0 },
  formId: { type: String }, 
  lastError: { type: String },

  reportTitle: String,
  valuationPurpose: String,
  valuePremise: String,
  valueBase: String,
  reportType: String,
  valuationDate: String,
  reportIssuingDate: String,
  assumptions: String,
  specialAssumptions: String,
  finalValue: String,
  valuationCurrency: String,
  reportAssetFile: String, 
  clientName: String,
  telephoneNumber: String,
  emailAddress: String,
  hasOtherUsers: String,
  reportUser: String,
  valuerName: String,
  contributionPercentage: String,

  assetType: String,
  inspectionDate: String,
  assetUsageSector: String,
  marketApproach: String,
  comparableTransactionsMethod: String,
  incomeApproach: String,
  profitMethod: String,
  costApproach: String,
  summationMethod: String,
  country: String,
  region: String,
  city: String,
  longitude: String,
  latitude: String,

  blockNumber: String,
  propertyNumber: String,
  certificateNumber: String,
  ownershipType: String,
  ownershipPercentage: String,
  rentalDuration: String,
  rentalEndDate: String,
  streetFacingFronts: String,
  distanceFromCityCenter: String,
  facilities: String, 
  landArea: String,
  buildingArea: String,
  authorizedLandCoverPercentage: String,
  authorizedHeight: String,
  landLeased: String,
  buildingStatus: String,
  finishingStatus: String,
  furnishingStatus: String,
  airConditioning: String,
  buildingType: String,
  otherFeatures: String, 
  bestUse: String,
  assetAge: String,
  streetWidth: String

}, { timestamps: true });

const TaqeemForm = mongoose.model('TaqeemForm', taqeemFormSchema);

module.exports = TaqeemForm;
