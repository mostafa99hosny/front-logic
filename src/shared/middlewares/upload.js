const multer = require('multer');
const path = require('path');
const fs = require('fs');

// Get the project root directory (adjust the number of '..' as needed)
const projectRoot = path.resolve(__dirname, '..', '..', '..');
const uploadDir = path.join(projectRoot, 'uploads');

// Ensure uploads folder exists
if (!fs.existsSync(uploadDir)) {
  fs.mkdirSync(uploadDir, { recursive: true });
}

console.log('Upload directory:', uploadDir); // Debug log to verify path

const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    cb(null, uploadDir);
  },
  filename: (req, file, cb) => {
    // PDFs keep original name, others get timestamp + extension
    const safeName =
      file.mimetype === 'application/pdf'
        ? path.basename(file.originalname) // strip directory info if any
        : Date.now() + path.extname(file.originalname);

    cb(null, safeName);
  },
});

const upload = multer({
  storage,
  limits: {
    fileSize: 10 * 1024 * 1024, // 10MB
  },
});

module.exports = upload;