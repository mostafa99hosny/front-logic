const corsOptions = {
  origin: ['https://front-ui-five.vercel.app', 'http://localhost:5173'],
  methods: ['GET','POST','PUT','PATCH','DELETE','OPTIONS'],
  allowedHeaders: ['Content-Type','Authorization'],
  credentials: true,
};

module.exports = corsOptions;