const express = require('express');
const cors = require('cors');
const app = express();
const port = 5001; // 更改端口為 5001

app.use(cors());

app.get('/api', (req, res) => {
  res.send({ message: 'Hello from the backend!' });
});

app.listen(port, () => {
  console.log(`Backend server is running at http://localhost:${port}`);
});