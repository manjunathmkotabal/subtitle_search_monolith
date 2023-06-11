from celery import shared_task
from .models import Video
import boto3
import subprocess
import re
from botocore.exceptions import ClientError
from django.conf import settings

@shared_task
def process_video(video_id):
    # Create an S3 client
    s3 = boto3.client('s3', region_name=settings.AWS_S3_REGION_NAME,aws_access_key_id =settings.AWS_ACCESS_KEY_ID,aws_secret_access_key =settings.AWS_SECRET_ACCESS_KEY)

    # Create an S3 bucket if it doesn't already exist
    try:
        s3.create_bucket(Bucket=settings.AWS_S3_BUCKET_NAME)
    except ClientError as e:
        # If the bucket already exists, ignore the exception
        if e.response['Error']['Code'] != 'BucketAlreadyOwnedByYou':
            print(f'Error creating bucket: {e}')

    try:
        s3.head_bucket(Bucket=settings.AWS_S3_BUCKET_NAME)
        print(f"The bucket '{settings.AWS_S3_BUCKET_NAME}' already exists.")
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            s3.create_bucket(Bucket=settings.AWS_S3_BUCKET_NAME)
            print(f"The bucket '{settings.AWS_S3_BUCKET_NAME}' was created successfully.")
        else:
            print(f"An error occurred while checking the bucket: {e}")
            
    # Retrieve the Video object from the database
    video = Video.objects.get(id=video_id)

    # Get the path of the video file
    video_file_path = video.file.path

    # Extract subtitles using CCExtractor or ffmpeg
    subtitles_file_path = f'{video_file_path}.vtt'
    ccextractor_command = f'ffmpeg -i "{video_file_path}" -map 0:s:0 "{subtitles_file_path}" -y'
    subprocess.run(ccextractor_command, shell=True)

    # Upload the video file to S3
    video_object_key = f'{video_id}/video.mp4'
    s3.upload_file(video_file_path,settings.AWS_S3_BUCKET_NAME, video_object_key, ExtraArgs={'ACL': 'public-read'})

    # Upload the subtitles file to S3
    subtitles_object_key = f'{video_id}/subtitles.vtt'
    s3.upload_file(subtitles_file_path,settings.AWS_S3_BUCKET_NAME, subtitles_object_key, ExtraArgs={'ACL': 'public-read'})

    # Create a DynamoDB resource
    # Create a DynamoDB resource
    dynamodb_resource = boto3.resource('dynamodb', region_name=settings.AWS_S3_REGION_NAME,aws_access_key_id =settings.AWS_ACCESS_KEY_ID,aws_secret_access_key =settings.AWS_SECRET_ACCESS_KEY)
    # Specify the table name
    table_name = settings.AWS_DYNAMODB_TABLE_NAME

    try:
        # Create the DynamoDB table
        table = dynamodb_resource.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'video_id',
                    'KeyType': 'HASH'
                },
                {
                    'AttributeName': 'subtitle_id',
                    'KeyType': 'RANGE'
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'video_id',
                    'AttributeType': 'N'
                },
                {
                    'AttributeName': 'subtitle_id',
                    'AttributeType': 'N'
                }
            ],

            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )

        # Wait until the table is created
        table.meta.client.get_waiter('table_exists').wait(TableName=table_name)
    except dynamodb_resource.meta.client.exceptions.ResourceInUseException:
        # Table already exists, use the existing table
        table = dynamodb_resource.Table(table_name)

    # Read the subtitles from the file
    with open(subtitles_file_path, 'r') as subtitles_file:
        # Skip the first line as it contains the WEBVTT header
        subtitles_file.readline()
        # Read the subtitles from the file
        subtitles = subtitles_file.read().strip().split('\n\n')

    with table.batch_writer(overwrite_by_pkeys=False) as batch:
        subtitle_id = 1  # Initialize subtitle ID
        for subtitle in subtitles:
            subtitle_lines = subtitle.strip().split('\n')
            time_line = subtitle_lines[0]
            content_lines = subtitle_lines[1:]

            start_time, end_time = time_line.split(' --> ')

            # Extract the content without HTML tags
            content = ' '.join(content_lines)

            video_id = int(video_id)

            item = {
                'video_id': video_id,
                'subtitle_id': subtitle_id,
                'start_time': start_time,
                'end_time': end_time,
                'content': content
            }

            try:
                # Put the item into DynamoDB with a conditional expression to insert only if the item doesn't exist
                response = table.put_item(
                    Item=item,
                    ConditionExpression='attribute_not_exists(video_id) AND attribute_not_exists(subtitle_id)'
                )
                print(f"inserting ...{subtitle_id}")
            except dynamodb_resource.meta.client.exceptions.ConditionalCheckFailedException:
                # Item already exists, skip insertion
                print(f'Subtitle with ID {subtitle_id} for video {video_id} already exists')
            except ClientError as e:
                # Handle other exceptions
                print(f'Error inserting subtitle: {subtitle_id} for video {video_id}')
                print(e)

            subtitle_id += 1  # Increment subtitle ID

    # Clean up the temporary subtitles file
    subprocess.run(f'rm "{subtitles_file_path}"', shell=True)
    subprocess.run(f'rm "{video_file_path}"', shell=True)

    return f"Done processing video-id -- {video_id}"
