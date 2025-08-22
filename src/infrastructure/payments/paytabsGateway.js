const paytabs = require('paytabs_pt2');
const AppError = require('../../shared/utils/appError');

class PayTabsGateway {
  constructor({ profileID, serverKey, region }) {
    if (!profileID || !serverKey) {
      throw new AppError('PayTabs profileID and serverKey are required', 400);
    }
    paytabs.setConfig(profileID, serverKey, region || 'india');
  }

  // Create payment page
  createPaymentPage({
    paymentMethods,
    transactionDetails,
    cartDetails,
    customerDetails,
    shippingDetails,
    responseUrls,
    language = 'en',
    framed = false
  }) {
    return new Promise((resolve, reject) => {
      paytabs.createPaymentPage(
        paymentMethods,
        transactionDetails,
        cartDetails,
        customerDetails,
        shippingDetails,
        responseUrls,
        language,
        (result) => {
          console.log('PayTabs createPaymentPage response:', result);

          if (!result || result.response_code >= 400) {
            const reason = result.result || result.message || 'Payment page creation failed';
            return reject(new AppError(reason, 500));
          }

          resolve(result);
        },
        framed
      );
    });
  }

  // Create one-time payment
  createPayment(paymentDetails) {
    return new Promise((resolve, reject) => {
      paytabs.createPayment(paymentDetails, (result) => {
        console.log('PayTabs createPayment response:', result);

        if (!result || result.response_code >= 400) {
          const reason = result.result || result.message || 'Payment creation failed';
          return reject(new AppError(reason, 500));
        }

        resolve(result);
      });
    });
  }

  // Validate payment
  validatePayment(tranRef) {
    return new Promise((resolve, reject) => {
      paytabs.validatePayment(tranRef, (result) => {
        console.log('PayTabs validatePayment response:', result);

        if (!result || result.response_code >= 400) {
          const reason = result.result || result.message || 'Payment validation failed';
          return reject(new AppError(reason, 500));
        }

        resolve(result);
      });
    });
  }
}

module.exports = PayTabsGateway;
