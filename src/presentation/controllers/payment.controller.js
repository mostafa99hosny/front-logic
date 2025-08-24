const catchAsync = require('../../shared/utils/catchAsync');
const responseHandler = require('../../shared/utils/responseHandler');
const appError = require('../../shared/utils/appError');

const StartSubscriptionUseCase = require('../../application/payments/startSubscription.uc');
const RenewSubscriptionUseCase = require('../../application/payments/renewSubscription.uc');
const FindAllSubscriptionsUseCase = require('../../application/payments/findAllSubscriptions.uc');

const PaymentRepo = require('../../infrastructure/repos/payment.repo');
const PaytabsGateway = require('../../infrastructure/payments/paytabsGateway');

const paymentRepo = new PaymentRepo();

const paytabsGateway = new PaytabsGateway({
    profileID: process.env.PAYTABS_PROFILE_ID,
    serverKey: process.env.PAYTABS_SERVER_KEY,
    region: process.env.PAYTABS_REGION || 'india'
});

const startSubscriptionUC = new StartSubscriptionUseCase(paymentRepo, paytabsGateway);
const renewSubscriptionUC = new RenewSubscriptionUseCase(paymentRepo, paytabsGateway);
const findAllSubscriptionsUC = new FindAllSubscriptionsUseCase(paymentRepo);

const startSubscription = catchAsync(async (req, res) => {
    const { userId, plan } = req.body;

    if (!userId || !plan || !plan.id || !plan.amount || !plan.currency) {
        throw new appError('Missing required fields', 400);
    }

    const { paymentUrl } = await startSubscriptionUC.execute({ userId, plan });

    responseHandler(res, 201, { paymentUrl });
});


const webhook = catchAsync(async (req, res) => {
    const { tranRef, cartId } = req.body;

    if (!tranRef || !cartId) {
        throw new appError('tranRef and cartId are required', 400);
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
        initialTranRef: tranRef
    });

    if (!subscription) {
        throw new appError('Pending subscription not found', 404);
    }

    responseHandler(res, 200, { success: true });
});

const renewSubscription = catchAsync(async (req, res) => {
    const { subscriptionId } = req.body;

    if (!subscriptionId) {
        throw new appError('subscriptionId is required', 400);
    }

    const paymentResult = await renewSubscriptionUC.execute({ subscriptionId });

    responseHandler(res, 200, paymentResult);
});

const findAllSubscriptions = catchAsync(async (req, res) => {
    const subscriptions = await findAllSubscriptionsUC.execute();

    responseHandler(res, 200, subscriptions);
});

module.exports = {
    startSubscription,
    webhook,
    renewSubscription,
    findAllSubscriptions
};
