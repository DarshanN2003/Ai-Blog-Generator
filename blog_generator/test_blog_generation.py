import os
from pytube import YouTube
import requests
import time

# AssemblyAI API Key
ASSEMBLYAI_API_KEY = ""
# OpenAI API Key
OPENAI_API_KEY = ""  # Replace with your actual OpenAI API key

def extract_audio_from_youtube(youtube_link):
    try:
        yt = YouTube(youtube_link)
        audio_stream = yt.streams.filter(only_audio=True).first()
        if audio_stream:
            audio_file_path = audio_stream.download()
            return audio_file_path
        else:
            raise Exception("No audio stream found")
    except Exception as e:
        raise Exception(f"Error downloading audio: {e}")

def get_transcription(audio_file_path):
    try:
        assemblyai_endpoint = "https://api.assemblyai.com/v2/upload"
        assemblyai_headers = {"authorization": ASSEMBLYAI_API_KEY}

        with open(audio_file_path, 'rb') as f:
            response = requests.post(assemblyai_endpoint, headers=assemblyai_headers, files={'file': f})
            if response.status_code == 200:
                upload_url = response.json()["upload_url"]
            else:
                raise Exception("Failed to upload audio")

        transcription_endpoint = "https://api.assemblyai.com/v2/transcript"
        transcription_payload = {"audio_url": upload_url}
        response = requests.post(transcription_endpoint, headers=assemblyai_headers, json=transcription_payload)
        if response.status_code == 200:
            transcription_id = response.json()["id"]
        else:
            raise Exception("Failed to start transcription")

        while True:
            response = requests.get(f"{transcription_endpoint}/{transcription_id}", headers=assemblyai_headers)
            if response.status_code == 200:
                status = response.json()["status"]
                if status == "completed":
                    return response.json()["text"]
                elif status == "failed":
                    raise Exception("Transcription failed")
                else:
                    time.sleep(5)  # wait for 5 seconds before checking the status again
            else:
                raise Exception("Failed to get transcription status")
    finally:
        if os.path.exists(audio_file_path):
            os.remove(audio_file_path)

def generate_blog_content(transcription_text):
    openai_endpoint = "https://api.openai.com/v1/engines/davinci-codex/completions"
    openai_headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }
    prompt = f"Generate a blog post based on the following transcription: {transcription_text}"
    payload = {
        "prompt": prompt,
        "max_tokens": 500,
        "temperature": 0.7
    }
    response = requests.post(openai_endpoint, headers=openai_headers, json=payload)
    if response.status_code == 200:
        return response.json()["choices"][0]["text"]
    else:
        raise Exception("Failed to generate blog content")

if __name__ == "__main__":
    youtube_link = input("Enter the YouTube video link: ")
    try:
        audio_file_path = extract_audio_from_youtube(youtube_link)
        transcription_text = get_transcription(audio_file_path)
        blog_content = generate_blog_content(transcription_text)
        print("Generated Blog Content:")
        print(blog_content)
    except Exception as e:
        print(f"Error: {e}")
