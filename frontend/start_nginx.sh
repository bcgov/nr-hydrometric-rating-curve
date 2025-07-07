#!/bin/sh

echo "---> Creating nginx.conf ..."
echo "BACKEND URL IS $BACKEND_URL"
export host="\$host"
export proxy_add_x_forwarded_for="\$proxy_add_x_forwarded_for"
cat /app/nginx.conf
nginx -c /app/nginx.conf -g 'daemon off;'
