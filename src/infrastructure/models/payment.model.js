const mongoose = require('mongoose');

const paymentSchema = new mongoose.Schema({
  userId: { type: String, required: true, index: true },
  planId: { type: String },
  cartId: { type: String, index: true },
  token: { type: String },
  initialTranRef: { type: String },
  amount: { type: Number, required: true },
  currency: { type: String, default: 'USD' },
  lastBilled: { type: Date, default: Date.now },
  status: { type: String, enum: ['pending', 'active', 'paused', 'canceled'], default: 'pending' },
  paymentToken: { type: String, required: true } // New field
}, { timestamps: true });


const Payment = mongoose.model('Payment', paymentSchema);

module.exports = Payment;
