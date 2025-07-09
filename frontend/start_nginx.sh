#!/bin/sh

# Config vars
CONF="/tmp/nginx.conf"

# Create config
echo "---> Creating ${CONF} from template"
echo "BACKEND_URL=$BACKEND_URL"
envsubst '${BACKEND_URL}' < /app/nginx.conf.template > ${CONF}

# Log config
echo
echo "---> ${CONF}:"
sed 's/^/nginx.conf | /' ${CONF}
sed -e 's/^/nginx.conf | /' -e 's/^\(nginx.conf | \) */\1/' /tmp/nginx.conf | sed 's/ /·/g'
sed 's/^/nginx.conf | /; s/ /·/g' /tmp/nginx.conf
# Create temp dirs
mkdir -p /tmp/nginx-proxy-temp /tmp/nginx-client-temp /tmp/nginx-fastcgi-temp /tmp/nginx-uwsgi-temp /tmp/nginx-scgi-temp

# Startup (foreground, daemon off)
echo
echo "---> Starting nginx..."
nginx -c ${CONF} -g 'daemon off;'
