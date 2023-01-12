# syntax=docker/dockerfile:1
FROM python:3.10.2-bullseye

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# dockeruser:
ENV DOCKERUSER=rctool

# create the rctool user
RUN useradd -m $DOCKERUSER

# create directory for the vfpa user
ENV HOME=/home/$DOCKERUSER
ENV APP_HOME=/home/$DOCKERUSER/djangoserver/mysite
RUN mkdir -p $APP_HOME
RUN mkdir -p $APP_HOME/staticfiles

# set workdir
WORKDIR $APP_HOME
COPY ./requirements.txt $APP_HOME

# install python packages
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# copy project
COPY . $APP_HOME
RUN chown -R $DOCKERUSER:$DOCKERUSER $APP_HOME

# change to the app user
USER $DOCKERUSER