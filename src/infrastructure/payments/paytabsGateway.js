const paytabs = require('paytabs_pt2');

class PayTabsGateway {
  constructor({ profileID, serverKey, region }) {
    paytabs.setConfig(profileID, serverKey, region);
  }

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
        paymentMethods,       // Array of methods
        transactionDetails,   // Object
        cartDetails,          // Object
        customerDetails,      // Object
        shippingDetails,      // Object
        responseUrls,         // Object
        language,             // String
        (result) => {         // Callback
          console.log('PayTabs raw response:', result);
          const responseCode = result.response_code || result['response_code:'];

          if (responseCode && responseCode >= 400) {
            const reason = result.result || result.message || 'Unknown error';
            console.error('Failed to create payment page:', reason);
            return reject(new Error(reason));
          }

          resolve(result);
        },
        framed                 // Boolean
      );
    });
  }

  createPayment(paymentDetails) {
    return new Promise((resolve, reject) => {
      paytabs.createPayment(paymentDetails, (result) => {
        console.log('PayTabs raw response:', result);
        if (result.response_code && result.response_code >= 400) {
          const reason = result.result || result.message || 'Payment creation failed';
          console.error('Failed to create payment:', reason);
          return reject(new Error(reason));
        }
        resolve(result);
      });
    });
  }

  validatePayment(tranRef) {
    return new Promise((resolve, reject) => {
      paytabs.validatePayment(tranRef, (result) => {
        console.log('PayTabs raw response:', result);
        if (result.response_code && result.response_code >= 400) {
          const reason = result.result || result.message || 'Payment validation failed';
          console.error('Failed to validate payment:', reason);
          return reject(new Error(reason));
        }
        resolve(result);
      });
    });
  }
}

module.exports = PayTabsGateway;
