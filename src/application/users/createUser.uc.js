const User = require('../../infrastructure/models/user.model');
const jwt = require('jsonwebtoken');

class CreateUserUseCase {
  async execute(userData) {
    try {
      // Validate required fields
      const requiredFields = [
        'firstName', 'lastName', 'email', 'phone', 
        'companyName', 'companyType', 'licenseNumber', 
        'city', 'password', 'termsAccepted'
      ];

      for (const field of requiredFields) {
        if (!userData[field]) {
          throw new Error(`${field} is required`);
        }
      }

      // Check if terms are accepted
      if (!userData.termsAccepted) {
        throw new Error('You must accept the terms and conditions');
      }

      // Check if user already exists
      const existingUser = await User.findOne({ email: userData.email });
      if (existingUser) {
        throw new Error('User with this email already exists');
      }

      // Create new user
      const user = new User({
        firstName: userData.firstName,
        lastName: userData.lastName,
        email: userData.email,
        phone: userData.phone,
        companyName: userData.companyName,
        companyType: userData.companyType,
        licenseNumber: userData.licenseNumber,
        city: userData.city,
        password: userData.password,
        newsletter: userData.newsletter || false,
        termsAccepted: userData.termsAccepted
      });

      await user.save();

      // Generate JWT token
      const token = jwt.sign(
        { 
          userId: user._id, 
          email: user.email 
        },
        process.env.JWT_SECRET || 'your-secret-key',
        { expiresIn: '7d' }
      );

      return {
        success: true,
        message: 'Account created successfully',
        user,
        token
      };

    } catch (error) {
      return {
        success: false,
        message: error.message
      };
    }
  }
}

module.exports = new CreateUserUseCase();