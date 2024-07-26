from django.shortcuts import render, redirect
from django.http import StreamingHttpResponse
from .models import MotionAlert
import cv2
import time
from datetime import datetime
import smtplib
from django.utils import timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from .forms import SignupForm
from django.contrib.auth import login
import os
from django.conf import settings

# Constants for distance calculation
KNOWN_WIDTH = 0.2  # Known width of the object in meters (example: 20 cm)
FOCAL_LENGTH = 615  # Focal length of the camera (adjust based on your camera)

def detect_motion(frame1, frame2):
    # Convert frames to grayscale
    gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
    
    # Apply Gaussian blur to the frames
    gray1 = cv2.GaussianBlur(gray1, (21, 21), 0)
    gray2 = cv2.GaussianBlur(gray2, (21, 21), 0)
    
    # Compute the absolute difference between the two frames
    frame_delta = cv2.absdiff(gray1, gray2)
    thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
    thresh = cv2.dilate(thresh, None, iterations=2)
    
    # Find contours on the thresholded image
    contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Check if any contour area is significant
    motion_detected = any(cv2.contourArea(c) > 500 for c in contours)
    
    return motion_detected, contours

def calculate_distance(known_width, focal_length, perceived_width):
    if perceived_width == 0:
        return None
    return (known_width * focal_length) / perceived_width

def send_email_alert(alert_time, image_path, distance):
    smtp_server = 'smtp.office365.com'
    smtp_port = 587
    sender_email = 'homesec0530@outlook.com'  # Replace with your email address
    sender_password = ''  # Replace with your email password
    recipient_email = 'homes52257@gmail.com'  # Replace with recipient email address

    # Create the email
    message = MIMEMultipart()
    message['From'] = sender_email
    message['To'] = recipient_email
    message['Subject'] = 'Motion Detected Alert'

    body = f"Alert! Unsafe condition occur.\nMotion detected at {alert_time}.\nDistance to object: {distance:.2f} meters."
    message.attach(MIMEText(body, 'plain'))

    # Attach the image
    with open(image_path, 'rb') as attachment:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename={image_path}')
        message.attach(part)

    # Connect to the SMTP server and send the email
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        text = message.as_string()
        server.sendmail(sender_email, recipient_email, text)
        server.quit()
        print(f"Alert email sent to {recipient_email}.")
    except Exception as e:
        print(f"Failed to send email alert: {e}")

def gen(camera):
    time.sleep(2)  # Warm up the camera
    last_frame = None
    alert_issued = False
    alert_interval = 10  # seconds
    last_alert_time = 0
    frame_rate = 30  # frames per second
    prev_time = 0

    while True:
        ret, frame = camera.read()
        if not ret:
            break

        # Resize the frame to reduce data size
        frame = cv2.resize(frame, (640, 480))

        # Get the current time
        current_time = time.time()

        # Skip frames to achieve the desired frame rate
        if current_time - prev_time > 1.0 / frame_rate:
            prev_time = current_time

            if last_frame is None:
                last_frame = frame
                continue

            motion_detected, contours = detect_motion(last_frame, frame)

            if motion_detected and (current_time - last_alert_time > alert_interval):
                alert_time = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
                image_path = f"motion_{alert_time.replace(':', '-').replace(' ', '_')}.jpg"
                image_full_path = os.path.join(settings.MEDIA_ROOT, 'motion_images', image_path)
                cv2.imwrite(image_full_path, frame)
                print(f"Motion detected at {alert_time}! Alert issued. Image saved as {image_full_path}.")
                for contour in contours:
                    if cv2.contourArea(contour) > 500:
                        (x, y, w, h) = cv2.boundingRect(contour)
                        distance = calculate_distance(KNOWN_WIDTH, FOCAL_LENGTH, w)
                        if distance is not None and 0 <= distance <= 3:
                            cv2.line(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                            cv2.putText(frame, f"Distance: {distance:.2f}m", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                            send_email_alert(alert_time, image_full_path, distance)
                            MotionAlert.objects.create(image_path=f'motion_images/{image_path}', distance=distance)
                            last_alert_time = current_time
                            break  # Only send one email per alert

            # Update the last frame
            last_frame = frame

            # Convert the frame to JPEG format
            ret, jpeg = cv2.imencode('.jpg', frame)
            if not ret:
                continue
            frame = jpeg.tobytes()

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')

def video_feed(request):
    url = 'http://192.168.29.104:8080/video'  # Replace with your URL
    cap = cv2.VideoCapture(url)
    return StreamingHttpResponse(gen(cap), content_type="multipart/x-mixed-replace;boundary=frame")

def signup(request):
    if request.method == "POST":
        form = SignupForm(request.POST)
        
        if form.is_valid():
            user = form.save()
            login(request, user)  # Log the user in after signup
            return redirect('home')  # Redirect to the home page
    else:
        form = SignupForm()
    return render(request, 'signup.html', {'form': form})

def home(request):
    alerts = MotionAlert.objects.all().order_by('-timestamp')
    return render(request, 'home.html', {'alerts': alerts})

def index(request):
    return render(request, 'index.html')

def object_detection(request):
    return render(request, 'object_detection.html')
