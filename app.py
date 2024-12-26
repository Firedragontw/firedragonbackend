from flask import Flask, request, jsonify
import requests
import os
from dotenv import load_dotenv
import time
import logging

load_dotenv()

app = Flask(__name__)


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

API_KEY = os.getenv('API_KEY')
ASSISTANT_ID = os.getenv('ASSISTANT_ID')
BASE_URL = 'https://prod.dvcbot.net/api/assts/v1'
AUTH_HEADER = {'Authorization': f'Bearer {API_KEY}', 'Content-Type': 'application/json'}

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message')

    # 添加固定的後綴到用戶的消息中
    message = f"{user_message} 幫我整理成數個 簡單的問題和回答 並 \"問題\": \"答案\": json 換行 排列"

    try:
        # Step 1: Create a thread
        thread_response = requests.post(
            f'{BASE_URL}/threads',
            headers=AUTH_HEADER,
            json={}
        )
        thread_response.raise_for_status()
        thread_id = thread_response.json()['id']

        # Step 2: Add message to the thread
        message_response = requests.post(
            f'{BASE_URL}/threads/{thread_id}/messages',
            headers=AUTH_HEADER,
            json={
                'role': 'user',
                'content': message  # 使用修改後的 message
            }
        )
        message_response.raise_for_status()

        # Step 3: Run the assistant within the thread
        run_response = requests.post(
            f'{BASE_URL}/threads/{thread_id}/runs',
            headers=AUTH_HEADER,
            json={
                'assistant_id': ASSISTANT_ID,
                'additional_instructions': f'The current time is: {time.strftime("%Y-%m-%d %H:%M:%S")}'
            }
        )
        run_response.raise_for_status()
        run_id = run_response.json()['id']

        # Step 4: Poll the run result
        run_status = run_response.json()['status']
        while run_status != 'completed':
            run_status_response = requests.get(
                f'{BASE_URL}/threads/{thread_id}/runs/{run_id}',
                headers=AUTH_HEADER
            )
            run_status_response.raise_for_status()
            run_status = run_status_response.json()['status']
            required_action = run_status_response.json().get('required_action')

            while run_status == 'requires_action' and required_action:
                tool_outputs = []
                tool_calls = required_action['submit_tool_outputs']['tool_calls']
                for tool_call in tool_calls:
                    func_name = tool_call['function']['name']
                    args = tool_call['function']['arguments']
                    pluginapi_url = f'{BASE_URL}/pluginapi?tid={thread_id}&aid={ASSISTANT_ID}&pid={func_name}'
                    output = requests.post(
                        pluginapi_url,
                        headers=AUTH_HEADER,
                        json=args
                    ).text[:8000]
                    tool_outputs.append({
                        'tool_call_id': tool_call['id'],
                        'output': output
                    })

                submit_tool_outputs_url = f'{BASE_URL}/threads/{thread_id}/runs/{run_id}/submit_tool_outputs'
                requests.post(
                    submit_tool_outputs_url,
                    headers=AUTH_HEADER,
                    json={'tool_outputs': tool_outputs}
                )

                run_status_response = requests.get(
                    f'{BASE_URL}/threads/{thread_id}/runs/{run_id}',
                    headers=AUTH_HEADER
                )
                run_status_response.raise_for_status()
                run_status = run_status_response.json()['status']
                required_action = run_status_response.json().get('required_action')
                time.sleep(1)

            time.sleep(1)

        # Step 5: Get the final response message
        messages_response = requests.get(
            f'{BASE_URL}/threads/{thread_id}/messages',
            headers=AUTH_HEADER
        )
        messages_response.raise_for_status()
        
        # Log the raw response for debugging
        logger.debug(f"Raw response: {messages_response.text}")

        try:
            response_data = messages_response.json()
            full_response = response_data['data'][0]['content'][0]['text']['value']
            
            # Extract the JSON array from the full response
            start_index = full_response.find("[")
            end_index = full_response.rfind("]") + 1
            if start_index != -1 and end_index != -1:
                response_message = full_response[start_index:end_index]
            else:
                raise ValueError("JSON array not found in the response")
        except KeyError as key_error:
            logger.error(f"Key Error: {str(key_error)}")
            return jsonify({'error': 'Unexpected response structure from server'}), 500
        except ValueError as value_error:
            logger.error(f"Value Error: {str(value_error)}")
            return jsonify({'error': 'Could not extract JSON array from response'}), 500

        return jsonify({'response': response_message})

    except requests.exceptions.RequestException as e:
        logger.error(f"Request Exception: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(port=3002)