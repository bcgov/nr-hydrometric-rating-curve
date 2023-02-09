from django.db import models


class User(models.Model):
    name = models.CharField(max_length=200)


    def __str__(self):
        return self.name
    

class RatingCurve(models.Model):
    usr = models.ForeignKey(User, on_delete=models.CASCADE)
    location = models.CharField(max_length=300)
    datetime = models.DateField()
    stage = models.FloatField()
    discharge = models.FloatField()

    def __str__(self):
        return self.location
