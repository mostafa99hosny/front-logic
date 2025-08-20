const appError = require('../../shared/utils/appError');

class RenewSubscriptionUseCase {
  constructor(paymentRepo, paytabsGateway) {
    this.paymentRepo = paymentRepo;
    this.paytabsGateway = paytabsGateway;
  }

  async execute({ subscriptionId }) {
    // Step 1: Get subscription from DB
    const subscription = await this.paymentRepo.findById(subscriptionId);
    if (!subscription) {
      throw new appError('Subscription not found', 404);
    }

    // Step 2: Charge using stored token
    const paytabsResponse = await this.paytabsGateway.createPayment({
      profile_id: process.env.PAYTABS_PROFILE_ID,
      tran_type: 'sale',
      tran_class: 'recurring',
      cart_id: `renew_${Date.now()}`,
      cart_currency: 'USD',
      cart_amount: subscription.amount,
      cart_description: 'Recurring subscription payment',
      token: subscription.token, // 💡 Use saved token here
    });

    if (!paytabsResponse || paytabsResponse.payment_result.response_status !== 'A') {
      throw new appError('Recurring charge failed', 400);
    }

    // Step 3: Update subscription/payment history
    await this.paymentRepo.addTransaction(subscriptionId, paytabsResponse.tran_ref);

    return paytabsResponse;
  }
}

module.exports = RenewSubscriptionUseCase;
