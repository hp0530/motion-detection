from django.db import models

class MotionAlert(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    image_path = models.ImageField(upload_to='motion_images/')
    distance = models.FloatField()

    def __str__(self):
        return f"{self.timestamp} - {self.distance} meters"

