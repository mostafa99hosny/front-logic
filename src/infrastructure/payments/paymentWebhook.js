const appError = require('../../shared/utils/appError');

module.exports = (paytabsGateway, paymentRepo) => async (req, res, next) => {
  try {
    const { tranRef, cartId } = req.body; 

    if (!cartId) {
      throw new appError('Missing cartId in webhook payload', 400);
    }

    const result = await paytabsGateway.validatePayment(tranRef);

    if (!result || result.payment_result.response_status !== 'A') {
      throw new appError('Payment not approved', 400);
    }

    const { token } = result;

    if (!token) {
      throw new appError('No token returned from PayTabs', 400);
    }

    const subscription = await paymentRepo.activateSubscription(cartId, {
      token,
      initialTranRef: tranRef,
    });

    if (!subscription) {
      throw new appError('Pending subscription not found', 404);
    }

    res.status(200).json({ success: true });
  } catch (err) {
    next(err);
  }
};
