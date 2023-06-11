from django.shortcuts import render
from .tasks import process_video
from .models import Video
import boto3
import requests
from django.http import HttpResponse


def get_videos_from_s3():
    s3 = boto3.client('s3')
    response = s3.list_objects_v2(Bucket='ecowiser-videos')

    if 'Contents' in response:
        videos = []
        for obj in response['Contents']:
            key = obj['Key']
            if key.endswith('.mp4'):
                video_id = key.split('/')[0]
                video_key = f"{video_id}/video.mp4"
                video_url = f"https://ecowiser-videos.s3.amazonaws.com/{video_key}"
                vtt_key = f"{video_id}/subtitles.vtt"
                vtt_url = f"https://ecowiser-videos.s3.amazonaws.com/{vtt_key}"
                videos.append({'video_url': video_url, 'vtt_url': vtt_url,'video_id':video_id})

        return videos
    else:
        return []  # Return an empty list if the bucket is empty


# Create a DynamoDB client
dynamodb = boto3.client('dynamodb',region_name = "ap-south-1")

def query_subtitles_by_keyword(keyword):
    # Define the DynamoDB table name
    table_name = 'Subtitles'

    # Create a DynamoDB client
    dynamodb = boto3.client('dynamodb', region_name='ap-south-1')

    # Define the search parameters
    expression_attribute_values = {
        ':kw': {'S': keyword}
    }
    filter_expression = 'contains(content, :kw)'
    projection_expression = 'video_id, start_time, end_time'

    # Scan the DynamoDB table
    response = dynamodb.scan(
        TableName=table_name,
        FilterExpression=filter_expression,
        ProjectionExpression=projection_expression,
        ExpressionAttributeValues=expression_attribute_values
    )

    # Extract the video IDs and timestamps from the response
    video_ids = set()
    timestamps = []

    for item in response['Items']:
        video_id = item['video_id']['N']
        start_time = item['start_time']['S']
        end_time = item['end_time']['S']

        video_ids.add(video_id)
        timestamps.append({'video_id': video_id, 'start_time': start_time, 'end_time': end_time})

        # Print the video ID and timestamps
        print(f"Video ID: {video_id}, Start Time: {start_time}, End Time: {end_time}")

    return video_ids, timestamps



def proxy_resource(request, url):
    try:
        # Send a GET request to the requested URL
        response = requests.get(url)

        # Create an HttpResponse object with the response content and headers
        proxy_response = HttpResponse(response.content, content_type=response.headers['Content-Type'])

        # Copy the response headers from the original response to the HttpResponse object
        for header, value in response.headers.items():
            proxy_response[header] = value

        return proxy_response

    except requests.exceptions.RequestException:
        # Handle any exceptions that may occur during the request
        return HttpResponse(status=500)



# Create your views here.

def upload_video(request):
    if request.method == 'POST':
        # Handle the video upload and save the file
        video_file = request.FILES['video']
        video = Video.objects.create(file=video_file)

        # Trigger the background task to process the video asynchronously
        process_video.delay(video.id)

        # Handle the uploaded video file here
        # Save the video file to the desired location or process it as required
        success_message = 'Upload successful!'
        return render(request, 'videoapp/upload.html', {'success_message': success_message})

    return render(request, 'videoapp/upload.html', {'success_message': None}) # Render the upload form template for GET requests 


import requests

PROXY_URL = 'http://127.0.0.1:8000'  # Replace with your actual proxy URL

def search_videos(request):
    keyword = request.POST.get('keyword', '').upper()
    videos = get_videos_from_s3()  # Get all videos initially

    if keyword:
        video_ids, timestamps = query_subtitles_by_keyword(keyword)

        if len(video_ids) > 0:
            videos = [video for video in videos if video['video_id'] in video_ids]

            for video in videos:
                video['timestamps'] = []  # Initialize an empty list for timestamps

                for timestamp in timestamps:
                    if video['video_id'] == timestamp['video_id']:
                        video['timestamps'].append({
                            'start_time': timestamp['start_time'],
                            'end_time': timestamp['end_time']
                        })

    if not videos:
        message = "No videos found in the bucket. If uploaded just now, it's probably being processed. Please wait for a minute."
    else:
        message = ""

    for video in videos:
        if 'vtt_url' in video:
            print(video['vtt_url'])
            video['vtt_url'] = f"{PROXY_URL}/proxy/{video['vtt_url']}"
        else:
            print("vtt_file error")

    context = {'videos': videos, 'keyword': keyword, 'message': message}
    return render(request, 'videoapp/search.html', context)
