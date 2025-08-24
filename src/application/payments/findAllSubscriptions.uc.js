const AppError = require('../../shared/utils/appError');

class FindAllSubscriptionsUseCase {
  constructor(paymentRepo) {
    this.paymentRepo = paymentRepo;
  }

  async execute() {
    const subscriptions = await this.paymentRepo.findAll();

    if (!subscriptions) {
      throw new AppError('No subscriptions found', 404);
    }

    return subscriptions;
  }
}

module.exports = FindAllSubscriptionsUseCase;