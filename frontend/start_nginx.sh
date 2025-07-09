#!/bin/sh

echo "---> Creating nginx.conf from template..."
echo "BACKEND URL IS $BACKEND_URL"

# Use envsubst to create final nginx.conf from template
envsubst '${BACKEND_URL}' < /app/nginx.conf.template > /tmp/nginx.conf

echo "---> nginx.conf created"
sed 's/^/nginx.conf | /' /tmp/nginx.conf

echo "---> Starting nginx..."
nginx -c /tmp/nginx.conf -g 'daemon off;'
