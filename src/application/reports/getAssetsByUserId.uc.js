const AssetData = require('../../infrastructure/models/assetData.model');

const getAssetsByUserIdUC = async (userId) => {
    try {
        const assets = await AssetData.find({ user_id: userId });
        return assets;
    } catch (error) {
        throw new Error(error.message);
    }
};

module.exports = {
    getAssetsByUserIdUC,
}