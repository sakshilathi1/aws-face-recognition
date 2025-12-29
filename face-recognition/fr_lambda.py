import json
import base64
import boto3
import os
import torch
from io import BytesIO
from PIL import Image
from facenet_pytorch import InceptionResnetV1
import numpy as np

resnet = InceptionResnetV1(pretrained='vggface2').eval()

WEIGHTS_PATH = '/var/task/resnetV1_video_weights.pt'
if os.path.exists(WEIGHTS_PATH):
    weights = torch.load(WEIGHTS_PATH, map_location=torch.device('cpu'))
else:
    weights = None
    print("Warning: Weights file not found. Using default matching.")

sqs = boto3.client('sqs', region_name='us-east-1')
RESPONSE_QUEUE_URL = os.environ.get('RESPONSE_QUEUE_URL')


def get_embedding(face_image):
    face_numpy = np.array(face_image, dtype=np.float32)
    face_numpy /= 255.0
    face_numpy = np.transpose(face_numpy, (2, 0, 1))
    face_tensor = torch.tensor(face_numpy, dtype=torch.float32)

    with torch.no_grad():
        embedding = resnet(face_tensor.unsqueeze(0)).detach()

    return embedding


def recognize_face(embedding, saved_data):
    if saved_data is None:
        return "unknown"

    embedding_list = saved_data[0]
    name_list = saved_data[1]
    dist_list = []

    for idx, emb_db in enumerate(embedding_list):
        dist = torch.dist(embedding, emb_db).item()
        dist_list.append(dist)

    idx_min = dist_list.index(min(dist_list))
    return name_list[idx_min]


def handler(event, context):
    try:
        for record in event['Records']:
            message_body = json.loads(record['body'])

            request_id = message_body.get('request_id')
            filename = message_body.get('filename')
            face_base64 = message_body.get('face_image')

            if not all([request_id, filename, face_base64]):
                print(f"Missing required fields in message: {message_body}")
                continue

            face_bytes = base64.b64decode(face_base64)
            face_image = Image.open(BytesIO(face_bytes))

            if face_image.mode != 'RGB':
                face_image = face_image.convert('RGB')

            embedding = get_embedding(face_image)
            result = recognize_face(embedding, weights)

            response_message = {
                'request_id': request_id,
                'result': result
            }

            if RESPONSE_QUEUE_URL:
                sqs.send_message(
                    QueueUrl=RESPONSE_QUEUE_URL,
                    MessageBody=json.dumps(response_message)
                )

            print(f"Processed request {request_id}: {result}")

        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Processing completed'})
        }

    except Exception as e:
        print(f"Error in face recognition: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
