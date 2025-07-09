#!/bin/sh

echo "---> Creating nginx.conf from template..."
echo "BACKEND URL IS $BACKEND_URL"

# nginx envars
# Lines removed as they are unused.

# Use envsubst to create final nginx.conf from template
envsubst '${BACKEND_URL}' < /app/nginx.conf.template > /tmp/nginx.conf

echo "---> nginx.conf created"
cat /tmp/nginx.conf

echo "---> Checking nginx.conf content:"
grep -iEA4 "location / {" /tmp/nginx.conf

echo "---> Starting nginx..."
nginx -c /tmp/nginx.conf -g 'daemon off;'
