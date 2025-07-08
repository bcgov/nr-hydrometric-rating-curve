#!/bin/sh

echo "---> Creating nginx.conf from template..."
echo "BACKEND URL IS $BACKEND_URL"

# Use envsubst to create final nginx.conf from template in /tmp
envsubst '${BACKEND_URL}' < /app/nginx.conf.template > /tmp/nginx.conf

echo "---> Checking nginx.conf content:"
cat /tmp/nginx.conf | grep -A5 -B5 proxy_pass

echo "---> Starting nginx..."
nginx -c /tmp/nginx.conf -g 'daemon off;'
