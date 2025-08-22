const Payment = require('../models/payment.model');

class PaymentRepo {
  async createPendingSubscription({ userId, planId, amount, currency }) {
    const payment = new Payment({
      userId,
      planId,
      amount,
      currency,
      status: 'pending'
    });
    return await payment.save();
  }

  async activateSubscription(cartId, { token, initialTranRef }) {
    return await Payment.findOneAndUpdate(
      { cartId },
      { token, initialTranRef, status: 'active', lastBilled: new Date() },
      { new: true }
    );
  }

  async findByToken(token) {
    return await Payment.findOne({ token });
  }

  async findAll() {
    return await Payment.find();
  }

  async findByUserId(userId) {
    return await Payment.find({ userId });
  }

  async findById(id) {
    return await Payment.findById(id);
  }

  async update(id, data) {
    return await Payment.findByIdAndUpdate(id, data, { new: true });
  }

  async delete(id) {
    return await Payment.findByIdAndDelete(id);
  }

  async setStatus(id, status) {
    if (!['pending', 'active', 'paused', 'canceled'].includes(status)) {
      throw new Error('Invalid status value');
    }
    return await Payment.findByIdAndUpdate(id, { status }, { new: true });
  }

  async updateLastBilled(id) {
    return await Payment.findByIdAndUpdate(id, { lastBilled: new Date() }, { new: true });
  }
}

module.exports = PaymentRepo;
