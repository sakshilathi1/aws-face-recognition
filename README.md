# 🔍 AWS Edge Face Recognition

<div align="center">

![AWS](https://img.shields.io/badge/AWS-IoT_Greengrass-orange.svg)
![Lambda](https://img.shields.io/badge/AWS-Lambda-yellow.svg)
![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Status](https://img.shields.io/badge/Status-Complete-brightgreen.svg)
![Grade](https://img.shields.io/badge/Grade-100%2F100-success.svg)

**Distributed face recognition pipeline using AWS IoT Greengrass, Lambda, and Edge Computing**

[Overview](#-overview) • [Architecture](#-architecture) • [Components](#-components) • [Setup](#-setup)

</div>

---

## 📖 Overview

This project implements a **distributed edge computing pipeline** for real-time face recognition using AWS IoT services. The system performs face detection on edge devices (IoT Greengrass) and face recognition in the cloud (AWS Lambda), demonstrating a hybrid edge-cloud architecture.

### Key Features

- 🌐 **Edge Computing** - Face detection runs on IoT Greengrass Core device
- ☁️ **Cloud Processing** - Face recognition via AWS Lambda
- 📡 **MQTT Communication** - Real-time message passing between IoT devices
- 🔄 **Distributed Pipeline** - Efficient workload distribution between edge and cloud
- ⚡ **Low Latency** - < 2.5 seconds average processing time per request

### Performance Results

| Metric | Result |
|--------|--------|
| Requests Processed | 100/100 |
| Classification Accuracy | 100% |
| Average Latency | < 2.5 seconds |
| **Final Score** | **100/100** |

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AWS Cloud                                       │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐          │
│  │  Request Queue  │───▶│  AWS Lambda     │───▶│ Response Queue  │          │
│  │  (SQS)          │    │  (FaceNet)      │    │ (SQS)           │          │
│  └────────▲────────┘    │ Face Recognition│    └────────┬────────┘          │
│           │             └─────────────────┘             │                    │
└───────────┼─────────────────────────────────────────────┼────────────────────┘
            │                                             │
            │ Detected Faces                              │ Recognition Results
            │                                             ▼
┌───────────┴─────────────────────────────────────────────────────────────────┐
│                           On Premises (Edge)                                 │
│                                                                              │
│  ┌─────────────────┐         ┌─────────────────────────────────────┐        │
│  │  Client Device  │  MQTT   │      Greengrass Core Device         │        │
│  │  (IoT Thing)    │────────▶│  ┌─────────────────────────────┐    │        │
│  │                 │         │  │   Face Detection Component  │    │        │
│  │  Video Frames   │         │  │   (MTCNN)                   │    │        │
│  └─────────────────┘         │  └─────────────────────────────┘    │        │
│                              └─────────────────────────────────────┘        │
│         ▲                                                                    │
│         │ Results                                                            │
│         └────────────────────────────────────────────────────────────────────┤
└──────────────────────────────────────────────────────────────────────────────┘
```

### Pipeline Flow

1. **IoT Client Device** captures video frames and publishes to MQTT topic
2. **Face Detection Component** (on Greengrass Core) receives frames via MQTT
3. **MTCNN Model** detects faces in the video frames on the edge
4. Detected faces are sent to **SQS Request Queue**
5. **Lambda Function** triggered by SQS performs face recognition using FaceNet
6. Recognition results sent to **SQS Response Queue**
7. **Client Device** retrieves results from response queue

## 📁 Project Structure

```
aws-face-recognition/
├── face-detection/
│   └── fd_component.py      # Greengrass component for face detection (MTCNN)
├── face-recognition/
│   └── fr_lambda.py         # Lambda function for face recognition (FaceNet)
└── .gitignore
```

## 🔧 Components

### Face Detection (Edge - Greengrass Component)

**File:** `face-detection/fd_component.py`

- Runs on AWS IoT Greengrass Core device
- Subscribes to MQTT topic: `clients/<ASU-ID>-IoTThing`
- Performs face detection using **MTCNN** (Multi-task Cascaded Convolutional Networks)
- Sends detected faces to SQS request queue

**Key Features:**
- Base64 decoding of video frames
- Real-time face detection on edge
- SQS integration for cloud communication

### Face Recognition (Cloud - Lambda Function)

**File:** `face-recognition/fr_lambda.py`

- Triggered by SQS request queue
- Performs face recognition using **FaceNet**
- Returns classification results to response queue

**Key Features:**
- Serverless execution
- Automatic scaling based on workload
- Pre-trained FaceNet model for accurate recognition

## 🚀 Setup

### Prerequisites

- AWS Account with appropriate permissions
- AWS CLI configured
- Python 3.9+

### AWS Services Required

| Service | Purpose |
|---------|---------|
| EC2 (t2.micro) | IoT Greengrass Core & Client devices |
| IoT Greengrass | Edge computing runtime |
| Lambda | Face recognition function |
| SQS | Message queues (request/response) |
| IAM | Access management |

### Infrastructure Setup

#### 1. IoT Greengrass Core (EC2 - Amazon Linux 2023)

```bash
# Install Java runtime
sudo dnf install java-11-amazon-corretto -y

# Create system user for Greengrass
sudo useradd --system --create-home ggc_user
sudo groupadd --system ggc_group

# Install Greengrass Core software
curl -s https://d2s8p88vqu9w66.cloudfront.net/releases/greengrass-nucleus-latest.zip > greengrass-nucleus-latest.zip
unzip greengrass-nucleus-latest.zip -d GreengrassInstaller
```

#### 2. IoT Client Device (EC2 - Ubuntu)

```bash
# Install AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Install AWS IoT Device SDK
git clone https://github.com/aws/aws-iot-device-sdk-python-v2.git
python3 -m pip install --user ./aws-iot-device-sdk-python-v2
```

#### 3. Deploy Face Detection Component

```bash
# Create component directories
mkdir -p ~/greengrassv2/{recipes,artifacts}
mkdir -p ~/greengrassv2/artifacts/com.clientdevices.FaceDetection/1.0.0

# Copy face detection code
cp fd_component.py ~/greengrassv2/artifacts/com.clientdevices.FaceDetection/1.0.0/

# Deploy component
sudo /greengrass/v2/bin/greengrass-cli deployment create \
    --recipeDir ~/greengrassv2/recipes \
    --artifactDir ~/greengrassv2/artifacts \
    --merge "com.clientdevices.FaceDetection=1.0.0"
```

#### 4. Deploy Lambda Function

```bash
# Package and deploy face recognition Lambda
zip -r fr_lambda.zip fr_lambda.py
aws lambda create-function \
    --function-name face-recognition \
    --runtime python3.9 \
    --handler fr_lambda.lambda_handler \
    --zip-file fileb://fr_lambda.zip
```

## 🔬 Technical Details

### Machine Learning Models

| Model | Purpose | Location |
|-------|---------|----------|
| **MTCNN** | Face Detection | Edge (Greengrass) |
| **FaceNet** | Face Recognition | Cloud (Lambda) |

### Communication Protocols

- **MQTT** - IoT device to Greengrass Core communication
- **SQS** - Edge to cloud message passing
- **TCP/IP** - Lambda invocation

### Message Format

```json
{
    "encoded": "<base64-encoded-image>",
    "request_id": "<unique-request-id>",
    "filename": "<image-filename>"
}
```

## 📊 Results

The system successfully:
- ✅ Processes 100 video frames without failures
- ✅ Achieves 100% face classification accuracy
- ✅ Maintains average latency under 2.5 seconds
- ✅ Demonstrates effective edge-cloud workload distribution

## 🔮 Future Improvements

- **Batch Processing** - Process multiple frames simultaneously
- **Model Optimization** - Use quantized models for faster edge inference
- **Real Camera Integration** - Connect actual IoT cameras instead of emulated devices
- **Multi-face Tracking** - Track multiple faces across video frames

## 👤 Author

**Sakshi Lathi**  
Arizona State University  
CSE 546: Cloud Computing - Fall 2025

---

<div align="center">

*This project demonstrates edge computing principles using AWS IoT Greengrass for distributed ML inference.*

</div>
