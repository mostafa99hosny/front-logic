const mongoose = require('mongoose');
const bcrypt = require('bcryptjs');

const userSchema = new mongoose.Schema({
  // Personal Information
  firstName: {
    type: String,
    required: true,
    trim: true
  },
  lastName: {
    type: String,
    required: true,
    trim: true
  },
  email: {
    type: String,
    required: true,
    unique: true,
    lowercase: true,
    trim: true
  },
  phone: {
    type: String,
    required: true,
    trim: true
  },
  
  // Company Information
  companyName: {
    type: String,
    required: true,
    trim: true
  },
  companyType: {
    type: String,
    required: true,
    enum: ['real-estate', 'construction', 'property-management'],
    default: 'real-estate'
  },
  licenseNumber: {
    type: String,
    required: true,
    trim: true
  },
  city: {
    type: String,
    required: true,
    enum: ['riyadh', 'jeddah', 'dammam', 'mecca', 'medina']
  },
  
  // Account Information
  password: {
    type: String,
    required: true,
    minlength: 6
  },
  
  // Account Status
  isActive: {
    type: Boolean,
    default: true
  },
  
  // Newsletter subscription
  newsletter: {
    type: Boolean,
    default: false
  },
  
  // Terms acceptance
  termsAccepted: {
    type: Boolean,
    required: true,
    default: false
  }
}, {
  timestamps: true
});

// Hash password before saving
userSchema.pre('save', async function(next) {
  if (!this.isModified('password')) return next();
  
  try {
    const salt = await bcrypt.genSalt(10);
    this.password = await bcrypt.hash(this.password, salt);
    next();
  } catch (error) {
    next(error);
  }
});

// Compare password method
userSchema.methods.comparePassword = async function(candidatePassword) {
  return await bcrypt.compare(candidatePassword, this.password);
};

// Remove password from JSON output
userSchema.methods.toJSON = function() {
  const user = this.toObject();
  delete user.password;
  return user;
};

module.exports = mongoose.model('User', userSchema);