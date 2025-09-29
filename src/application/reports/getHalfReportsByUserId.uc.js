const HalfReport = require('../../infrastructure/models/halfReport.model');

const getHalfReportsByUserIdUC = async (userId) => {
    try {
        const reports = await HalfReport.find({ user_id: userId });
        return reports;
    } catch (error) {
        throw new Error(error.message);
    }
};

module.exports = {
    getHalfReportsByUserIdUC,
}