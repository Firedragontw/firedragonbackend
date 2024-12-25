const express = require('express');
const axios = require('axios');
const dotenv = require('dotenv');

dotenv.config();

const app = express();
const port = process.env.PORT || 3002;

app.use(express.json());

app.post('/api/chat', async (req, res) => {
  const { message } = req.body;

  try {
    // Step 1: Create a thread
    const threadResponse = await axios.post('https://prod.dvcbot.net/api/assts/v1/threads', {}, {
      headers: {
        'Authorization': `Bearer ${process.env.API_KEY}`,
        'Content-Type': 'application/json'
      }
    });

    const threadId = threadResponse.data.id;

    // Step 2: Add message to the thread
    await axios.post(`https://prod.dvcbot.net/api/assts/v1/threads/${threadId}/messages`, {
      role: 'user',
      content: message
    }, {
      headers: {
        'Authorization': `Bearer ${process.env.API_KEY}`,
        'Content-Type': 'application/json'
      }
    });

    // Step 3: Run the assistant within the thread
    const runResponse = await axios.post(`https://prod.dvcbot.net/api/assts/v1/threads/${threadId}/runs`, {
      assistant_id: process.env.ASSISTANT_ID
    }, {
      headers: {
        'Authorization': `Bearer ${process.env.API_KEY}`,
        'Content-Type': 'application/json'
      }
    });

    const runId = runResponse.data.id;

    // Step 4: Call plugin API (if needed)
    // This step is optional and depends on your specific use case
    // const pluginResponse = await axios.post(`https://prod.dvcbot.net/api/assts/v1/pluginapi`, {
    //   tid: threadId,
    //   aid: process.env.ASSISTANT_ID,
    //   pid: 'function_name' // Replace with actual function name
    // }, {
    //   headers: {
    //     'Authorization': `Bearer ${process.env.API_KEY}`,
    //     'Content-Type': 'application/json'
    //   },
    //   data: {} // Replace with actual function arguments
    // });

    // Step 5: Submit tool outputs to run (if needed)
    // This step is optional and depends on your specific use case
    // await axios.post(`https://prod.dvcbot.net/api/assts/v1/threads/${threadId}/runs/${runId}/submit_tool_outputs`, {
    //   tool_outputs: [
    //     {
    //       tool_call_id: 'call_abc123', // Replace with actual tool call ID
    //       output: '28C' // Replace with actual output
    //     }
    //   ]
    // }, {
    //   headers: {
    //     'Authorization': `Bearer ${process.env.API_KEY}`,
    //     'Content-Type': 'application/json'
    //   }
    // });

    // Step 6: Get the final response message
    const messagesResponse = await axios.get(`https://prod.dvcbot.net/api/assts/v1/threads/${threadId}/messages`, {
      headers: {
        'Authorization': `Bearer ${process.env.API_KEY}`,
        'Content-Type': 'application/json'
      }
    });

    const responseMessage = messagesResponse.data.data[0].content[0].text.value;

    res.json({ response: responseMessage });
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: error.message });
  }
});

app.listen(port, () => {
  console.log(`Server is running on http://localhost:${port}`);
});