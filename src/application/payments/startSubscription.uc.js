const appError = require('../../shared/utils/appError');

class StartSubscriptionUseCase {
  constructor(paymentRepo, paytabsGateway) {
    this.paymentRepo = paymentRepo;
    this.paytabsGateway = paytabsGateway;
  }

  async execute({ userId, plan }) {
    if (!plan || !plan.id || !plan.amount || !plan.currency || !plan.description) {
      throw new appError('Invalid plan details', 400);
    }

    const paymentMethods = ['all'];

    const transactionDetails = [
      'sale',
      'ecom',
    ];

    const cartDetails = [
      plan.id,
      plan.currency,
      plan.amount,
      plan.description
    ];

    const customer = {
      name: "Aasim Q",
      email: "sedu321a@gmail.com",
      phone: "+91 60054 46344",
      street1: "Street address",
      city: "Random",
      state: "01",
      country: "IND",
      zip: "110001",
      IP: "49.36.201.12"
    }


    const customerDetails = [
      customer.name,
      customer.email,
      customer.phone,
      customer.street1,
      customer.city,
      customer.state,
      customer.country,
      customer.zip,
      customer.IP
    ];

    const shippingDetails = customerDetails

    let url = {
      callback: "https://example.com/",
      response: "https://example.com/"
    };

    const responseUrls = [
      url.callback,
      url.response
    ];

    const response = await this.paytabsGateway.createPaymentPage({
      paymentMethods,
      transactionDetails,
      cartDetails,
      customerDetails,
      shippingDetails,
      responseUrls,
      lang: 'en',
      framed: false
    });

    if (!response || !response.redirect_url) {
      throw new appError('Failed to create payment page', 500);
    }

    if (response.paymentToken) {
      await this.paymentRepo.createPendingSubscription({
        userId,
        planId: plan.id,
        amount: plan.amount,
        currency: plan.currency,
        paymentToken: response.paymentToken
      });
    }

    return { paymentUrl: response.redirect_url };
  }
}

module.exports = StartSubscriptionUseCase;
