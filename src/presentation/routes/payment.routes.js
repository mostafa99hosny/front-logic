const express = require('express');
const {
  startSubscription,
  webhook,
  renewSubscription,
  findAllSubscriptions
} = require('../controllers/payment.controller');

const paymentRouter = express.Router();

paymentRouter.post('/start', startSubscription);
paymentRouter.post('/webhook/paytabs', webhook);
paymentRouter.post('/renew', renewSubscription);

paymentRouter.get('/subscriptions', findAllSubscriptions);

module.exports = paymentRouter;
