const express = require('express');
const {
  startSubscription,
  webhook,
  renewSubscription
} = require('../controllers/payment.controller');

const paymentRouter = express.Router();

paymentRouter.post('/start', startSubscription);
paymentRouter.post('/webhook/paytabs', webhook);
paymentRouter.post('/renew', renewSubscription);

module.exports = paymentRouter;
