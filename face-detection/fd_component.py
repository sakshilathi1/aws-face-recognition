import json
import base64
import boto3
import sys
import traceback
from io import BytesIO
from PIL import Image
from facenet_pytorch import MTCNN
import awsiot.greengrasscoreipc
from awsiot.greengrasscoreipc.model import (
    SubscribeToTopicRequest,
    SubscriptionResponseMessage
)

ASU_ID = "1234549838"
MQTT_TOPIC = f"clients/{ASU_ID}-IoTThing"
SQS_REQUEST_QUEUE = f"https://sqs.us-east-1.amazonaws.com/660309491405/{ASU_ID}-req-queue"
SQS_RESPONSE_QUEUE = f"https://sqs.us-east-1.amazonaws.com/660309491405/{ASU_ID}-resp-queue"

processed_ids = set()
mtcnn = MTCNN(image_size=240, margin=0, min_face_size=20, keep_all=False, device='cpu')
sqs = boto3.client('sqs', region_name='us-east-1')

print(f"Face Detection Component initialized. Subscribing to: {MQTT_TOPIC}", flush=True)


class StreamHandler(awsiot.greengrasscoreipc.client.SubscribeToTopicStreamHandler):
    def __init__(self):
        super().__init__()

    def on_stream_event(self, event: SubscriptionResponseMessage) -> None:
        try:
            message_string = str(event.binary_message.message, "utf-8")
            print(f"Received message on topic {MQTT_TOPIC}", flush=True)

            message_data = json.loads(message_string)
            encoded_image = message_data.get('encoded')
            request_id = message_data.get('request_id')
            filename = message_data.get('filename')

            if not all([encoded_image, request_id, filename]):
                print(f"Missing required fields in message: {message_data}", flush=True)
                return

            if request_id in processed_ids:
                print(f"Duplicate request {request_id}, skipping", flush=True)
                return

            processed_ids.add(request_id)
            print(f"Processing request {request_id} for {filename}", flush=True)

            image_bytes = base64.b64decode(encoded_image)
            image = Image.open(BytesIO(image_bytes))

            if image.mode != 'RGB':
                image = image.convert('RGB')

            face_tensor = mtcnn(image)

            if face_tensor is None:
                print(f"No face detected for request {request_id}", flush=True)
                response_message = {
                    'request_id': request_id,
                    'result': 'No-Face'
                }
                sqs.send_message(
                    QueueUrl=SQS_RESPONSE_QUEUE,
                    MessageBody=json.dumps(response_message)
                )
                print(f"Sent No-Face result for {request_id}", flush=True)
                return

            face_array = face_tensor - face_tensor.min()
            face_array = face_array / face_array.max()
            face_array = (face_array * 255).byte().permute(1, 2, 0).numpy()
            face_image = Image.fromarray(face_array, mode="RGB")

            buffered = BytesIO()
            face_image.save(buffered, format="JPEG")
            face_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

            sqs_message = {
                'request_id': request_id,
                'filename': filename,
                'face_image': face_base64
            }

            sqs.send_message(
                QueueUrl=SQS_REQUEST_QUEUE,
                MessageBody=json.dumps(sqs_message)
            )

            print(f"Face detected and sent to SQS for request {request_id}", flush=True)

        except Exception as e:
            print(f"Error processing message: {str(e)}", flush=True)
            traceback.print_exc()

    def on_stream_error(self, error: Exception) -> bool:
        print(f"Stream error: {error}", flush=True)
        return True

    def on_stream_closed(self) -> None:
        print("Stream closed", flush=True)


def main():
    try:
        ipc_client = awsiot.greengrasscoreipc.connect()
        request = SubscribeToTopicRequest()
        request.topic = MQTT_TOPIC
        handler = StreamHandler()
        operation = ipc_client.new_subscribe_to_topic(handler)
        operation.activate(request)

        print(f"Successfully subscribed to topic: {MQTT_TOPIC}", flush=True)

        try:
            while True:
                import time
                time.sleep(10)
        except InterruptedError:
            print("Subscription interrupted", flush=True)

    except Exception as e:
        print(f"Error in main: {str(e)}", flush=True)
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
