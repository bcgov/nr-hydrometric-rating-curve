#!/bin/sh

echo "---> Creating nginx.conf from template..."
echo "BACKEND URL IS $BACKEND_URL"

# nginx envars
export host="\$host"
export proxy_add_x_forwarded_for="\$proxy_add_x_forwarded_for"

# Use envsubst to create final nginx.conf from template
envsubst '${BACKEND_URL}' < /app/nginx.conf.template > /tmp/nginx.conf

echo "---> nginx.conf created"
cat /tmp/nginx.conf

echo "---> Checking nginx.conf content:"
cat /tmp/nginx.conf | grep -iEA4 "location / {"

echo "---> Starting nginx..."
nginx -c /tmp/nginx.conf -g 'daemon off;'
