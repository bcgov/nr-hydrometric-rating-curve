#!/bin/sh

echo "---> Creating nginx.conf ..."
echo "BACKEND URL IS $BACKEND_URL"
export host="\$host"
export proxy_add_x_forwarded_for="\$proxy_add_x_forwarded_for"
envsubst < /app/nginx.conf >  /etc/nginx/nginx.conf
echo "---> nginx.conf created"
cat /etc/nginx/nginx.conf
nginx -g 'daemon off;'

