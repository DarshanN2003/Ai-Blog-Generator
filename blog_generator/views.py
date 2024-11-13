from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.conf import settings
import json
from pytube import YouTube
import os
import requests
from requests import get, post, HTTPError
import logging
import assemblyai as aai
import openai
from .models import BlogPost

# Create your views here.
@login_required
def index(request):
    return render(request, 'index.html')

logger = logging.getLogger(__name__)

@csrf_exempt
def generate_blog(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=405)

    try:
        data = json.loads(request.body)
        yt_link = data['link']
    except (KeyError, json.JSONDecodeError) as e:
        logger.error(f"Invalid data sent: {e}")
        return JsonResponse({'error': 'Invalid data sent'}, status=400)

    try:
        title = yt_title(yt_link)
    except Exception as e:
        logger.error(f"Failed to get YouTube title: {e}")
        return JsonResponse({'error': f"Failed to get YouTube title: {e}"}, status=500)

    try:
        transcription = get_transcription(yt_link)
        if not transcription:
            logger.error("Failed to get transcript")
            return JsonResponse({'error': "Failed to get transcript"}, status=500)
    except Exception as e:
        logger.error(f"Failed to get transcript: {e}")
        return JsonResponse({'error': f"Failed to get transcript: {e}"}, status=500)

    try:
        blog_content = generate_blog_from_transcription(transcription)
        if not blog_content:
            logger.error("Failed to generate blog article")
            return JsonResponse({'error': "Failed to generate blog article"}, status=500)
    except Exception as e:
        logger.error(f"Failed to generate blog article: {e}")
        return JsonResponse({'error': f"Failed to generate blog article: {e}"}, status=500)

    new_blog_article = BlogPost.objects.create(
        user=request.user,
        youtube_title=title,
        youtube_link=yt_link,
        generated_content=blog_content,
    )
    new_blog_article.save()

    return JsonResponse({'content': blog_content})

def yt_title(link):
    yt = YouTube(link)
    title = yt.title
    return title

def download_audio(link):
    yt = YouTube(link)
    stream = yt.streams.filter(only_audio=True).first()
    audio_file = stream.download(output_path='temp')
    return audio_file

def get_transcription(yt_link):
    audio_file = download_audio(yt_link)
    aai_api = aai.Client(token="6df1a7f5660d464daf670e6b54414ee6")

    try:
        upload_response = aai_api.upload_file(audio_file)
        transcript_id = upload_response.id
        poll_response = aai_api.get_transcript(transcript_id)
        while poll_response.status != 'completed':
            poll_response = aai_api.get_transcript(transcript_id)
        transcription = poll_response.text
        return transcription
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 400:
            logger.error(f"Bad request error: {e}")
            return None
        else:
            logger.error(f"HTTP error: {e}")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error: {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to get transcript: {e}")
        return None

def generate_blog_from_transcription(transcription):
    openai.api_key = "YOUR_OPENAI_API_KEY"

    prompt = f"Based on the following transcript from a YouTube video, write a comprehensive blog article, write it based on the transcript, but dont make it look like a youtube video, make it look like a proper blog article:\n\n{transcription}\n\nArticle:"

    try:
        response = openai.Completion.create(
            model="text-davinci-003",
            prompt=prompt,
            max_tokens=1000
        )
        generated_content = response.choices[0].text.strip()
        return generated_content
    except openai.error.APIError as e:
        logger.error(f"OpenAI API error: {e}")
        return None
    except openai.error.RateLimitError as e:
        logger.error(f"OpenAI API rate limit error: {e}")
        return None
    except openai.error.AuthenticationError as e:
        logger.error(f"OpenAI API authentication error: {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to generate blog: {e}")
        return None

@login_required
def blog_list(request):
    blog_articles = BlogPost.objects.filter(user=request.user)
    return render(request, "all-blogs.html", {'blog_articles': blog_articles})

@login_required
def blog_details(request, pk):
    blog_article_detail = BlogPost.objects.get(id=pk)
    if request.user == blog_article_detail.user:
        return render(request, 'blog-details.html', {'blog_article_detail': blog_article_detail})
    else:
        return redirect('/')
def user_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('/')
        else:
            error_message = "Invalid username or password"
            return render(request, 'login.html', {'error_message': error_message})
        
    return render(request, 'login.html')

def user_signup(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        repeatPassword = request.POST['repeatpassword']

        if password == repeatPassword:
            try:
                user = User.objects.create_user(username, email, password)
                user.save()
                login(request, user)
                return redirect('/')
            except:
                error_message = 'Error creating account'
                return render(request, 'signup.html', {'error_message':error_message})
        else:
            error_message = 'Password do not match'
            return render(request, 'signup.html', {'error_message':error_message})
        
    return render(request, 'signup.html')

def user_logout(request):
    logout(request)
    return redirect('/')