#!/bin/sh

# Config file
CONF="/tmp/nginx.conf"

# Create and log
echo "---> Creating ${CONF}"
echo "BACKEND_URL=$BACKEND_URL"
envsubst '${BACKEND_URL}' < /app/nginx.conf.template > ${CONF}
echo
cat /tmp/nginx.conf | sed 's/ /·/g'

# Create temp dirs
mkdir -p /tmp/nginx-proxy-temp /tmp/nginx-client-temp /tmp/nginx-fastcgi-temp /tmp/nginx-uwsgi-temp /tmp/nginx-scgi-temp

# Touch log files to ensure they exist for tail
touch /tmp/access.log /tmp/error.log

# Stream logs to stdout and stderr in background for container observability
tail -F /tmp/access.log &
tail -F /tmp/error.log >&2 &

# Startup (daemon off = foreground)
echo
echo "---> Starting nginx"
nginx -c ${CONF} -g 'daemon off;'
