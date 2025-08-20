const appError = require('../../shared/utils/appError');

class StartSubscriptionUseCase {
  constructor(paymentRepo, paytabsGateway) {
    this.paymentRepo = paymentRepo;
    this.paytabsGateway = paytabsGateway;
  }

  async execute({ userId, plan }) {
    if (!plan || !plan.id || !plan.amount || !plan.currency) {
      throw new appError('Invalid plan details', 400);
    }

    const paymentMethods = ['creditcard'];

    const transactionDetails = {
      profile_id: process.env.PAYTABS_PROFILE_ID,
      tran_type: 'sale',
      tran_class: 'recurring',
      cart_id: `sub_${Date.now()}`,
      cart_currency: plan.currency,
      cart_amount: plan.amount,
      cart_description: `Subscription for ${plan.name}`,
      tokenise: 2
    };

    const cartDetails = {
      id: plan.id,
      description: plan.name,
      amount: plan.amount,
      currency: plan.currency
    };

    const customerDetails = {
      name: 'John Doe',
      email: 'john@example.com',
      phone: '+966123456789'
    };

    const shippingDetails = {
      name: 'John Doe',
      email: 'john@example.com',
      phone: '+966123456789',
      address: 'Some Street',
      city: 'Some City',
      state: 'Some State',
      country: 'SA'
    };

    const responseUrls = {
      return: `${process.env.APP_URL}/payments/success`,
      callback: `${process.env.API_URL}/webhooks/paytabs`
    };

    const transaction = [
      'sale', // tran_class
      'recurring',      // tran_type
      {
        profile_id: process.env.PAYTABS_PROFILE_ID,
        cart_id: `sub${Date.now()}`,
        cart_currency: plan.currency,
        cart_amount: plan.amount,
        cart_description: `Subscription for ${plan.name}`,
        tokenise: 2
      }
    ];


    const response = await this.paytabsGateway.createPaymentPage({
      paymentMethods,
      transactionDetails: transaction,
      cartDetails,
      customerDetails,
      shippingDetails,
      responseUrls,
      language: 'en',
      framed: false
    });

    if (!response || !response.redirect_url) {
      throw new appError('Failed to create payment page', 500);
    }

    return { paymentUrl: response.redirect_url };
  }
}

module.exports = StartSubscriptionUseCase;
