#!/bin/sh

echo "---> Creating nginx.conf ..."
echo "BACKEND URL IS $BACKEND_URL"

# Replace $BACKEND_URL in nginx.conf with the actual URL
sed -i "s|\$BACKEND_URL|$BACKEND_URL|g" /app/nginx.conf

echo "---> Checking nginx.conf content:"
cat /app/nginx.conf | grep -A5 -B5 proxy_pass

echo "---> Starting nginx..."
nginx -c /app/nginx.conf -g 'daemon off;'
