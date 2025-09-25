const User = require('../../infrastructure/models/user.model');
const createUserUseCase = require('../../application/users/createUser.uc');
const jwt = require('jsonwebtoken');
const bcrypt = require('bcryptjs');

class UserController {
  // Register new user
  async register(req, res) {
    try {
      const result = await createUserUseCase.execute(req.body);

      if (!result.success) {
        return res.status(400).json({
          success: false,
          message: result.message
        });
      }

      res.status(201).json({
        success: true,
        message: result.message,
        user: result.user,
        token: result.token
      });

    } catch (error) {
      console.error('Registration error:', error);
      res.status(500).json({
        success: false,
        message: 'Internal server error'
      });
    }
  }

  // Login user
  async login(req, res) {
    try {
      const { email, password } = req.body;

      // Validate input
      if (!email || !password) {
        return res.status(400).json({
          success: false,
          message: 'Email and password are required'
        });
      }

      // Find user
      const user = await User.findOne({ email: email.toLowerCase() });
      if (!user) {
        return res.status(401).json({
          success: false,
          message: 'Invalid email or password'
        });
      }

      // Check password
      const isPasswordValid = await user.comparePassword(password);
      if (!isPasswordValid) {
        return res.status(401).json({
          success: false,
          message: 'Invalid email or password'
        });
      }

      // Check if account is active
      if (!user.isActive) {
        return res.status(401).json({
          success: false,
          message: 'Account is deactivated'
        });
      }

      // Generate token
      const token = jwt.sign(
        {
          userId: user._id,
          email: user.email
        },
        process.env.JWT_SECRET || 'your-secret-key',
        { expiresIn: '7d' }
      );

      res.json({
        success: true,
        message: 'Login successful',
        user,
        token
      });

    } catch (error) {
      console.error('Login error:', error);
      res.status(500).json({
        success: false,
        message: 'Internal server error'
      });
    }
  }

  // Get current user profile
  async getProfile(req, res) {
    try {
      const user = await User.findById(req.user.userId);
      if (!user) {
        return res.status(404).json({
          success: false,
          message: 'User not found'
        });
      }
      // Debug: طباعة بيانات المستخدم قبل الإرسال
      console.log('USER PROFILE DATA:', user);
      // تحويل المستخدم إلى كائن عادي وإزالة كلمة المرور فقط
      const userObj = user.toObject();
      delete userObj.password;
      // إضافة القيم الافتراضية للحقول إذا كانت غير موجودة
      userObj.firstName = userObj.firstName || "";
      userObj.lastName = userObj.lastName || "";
      userObj.email = userObj.email || "";
      userObj.phone = userObj.phone || "";
      userObj.companyName = userObj.companyName || "";
      userObj.companyType = userObj.companyType || "";
      userObj.licenseNumber = userObj.licenseNumber || "";
      userObj.city = userObj.city || "";
      res.json({
        success: true,
        user: userObj
      });
    } catch (error) {
      console.error('Get profile error:', error);
      res.status(500).json({
        success: false,
        message: 'Internal server error'
      });
    }
  }

  // Verify token
  async verifyToken(req, res) {
    try {
      const user = await User.findById(req.user.userId);
      if (!user) {
        return res.status(404).json({
          success: false,
          message: 'User not found'
        });
      }

      res.json({
        success: true,
        message: 'Token is valid',
        user
      });

    } catch (error) {
      console.error('Verify token error:', error);
      res.status(500).json({
        success: false,
        message: 'Internal server error'
      });
    }
  }
   // Update profile
  async updateProfile(req, res) {
    try {
      const updates = { ...req.body };

      // If password provided, hash it
      if (updates.password) {
        const salt = await bcrypt.genSalt(10);
        updates.password = await bcrypt.hash(updates.password, salt);
      }

      const user = await User.findByIdAndUpdate(req.user.userId, updates, {
        new: true,
        runValidators: true
      });

      if (!user) {
        return res.status(404).json({
          success: false,
          message: 'User not found'
        });
      }

      res.json({
        success: true,
        message: 'Profile updated successfully',
        user
      });

    } catch (error) {
      console.error('Update profile error:', error);
      res.status(500).json({
        success: false,
        message: 'Internal server error'
      });
    }
  }
}

module.exports = new UserController();