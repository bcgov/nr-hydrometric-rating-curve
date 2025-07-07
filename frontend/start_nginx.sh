#!/bin/sh

echo "---> Creating nginx.conf ..."
echo "BACKEND URL IS $BACKEND_URL"

# Convert BACKEND_URL to lowercase for nginx
export backend_url="$BACKEND_URL"

export host="\$host"
export proxy_add_x_forwarded_for="\$proxy_add_x_forwarded_for"
echo "---> Checking nginx.conf content:"
cat /app/nginx.conf | grep -A5 -B5 proxy_pass
echo "---> Starting nginx..."
nginx -c /app/nginx.conf -g 'daemon off;'
