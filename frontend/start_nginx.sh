#!/bin/sh

echo "---> Creating nginx.conf from template..."
echo "BACKEND URL IS $BACKEND_URL"

# Use envsubst to create final nginx.conf from template
envsubst '${BACKEND_URL}' < /app/nginx.conf.template > /app/nginx.conf

echo "---> Checking nginx.conf content:"
cat /app/nginx.conf | grep -A5 -B5 proxy_pass

echo "---> Starting nginx..."
nginx -c /app/nginx.conf -g 'daemon off;'
