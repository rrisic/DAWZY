import requests
# Path to the file you want to upload
file_path = '../recording/Melody.wav'
# Your ngrok URL
url = 'http://panda-humble-amoeba.ngrok-free.app/transcribe'
# Open the file in binary mode and send POST request
with open(file_path, 'rb') as f:
    files = {'file': f}
    response = requests.post(url, files=files)
# Print the response from the server
print("Response Text:", response.text)
if response.status_code == 200:
    # Save the response content to a file
    output_path = 'transcribed.mid'
    with open(output_path, 'wb') as out_file:
        out_file.write(response.content)
    print(f":white_check_mark: MIDI file downloaded and saved as: {output_path}")
else:
    print(":x: Failed to get file")
    print("Status Code:", response.status_code)
    print("Response Text:", response.text)