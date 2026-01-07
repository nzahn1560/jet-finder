#!/usr/bin/env sh
set -eu

API_TARGET="${API_UPSTREAM:-http://localhost:8000}"
export API_TARGET

envsubst '${API_TARGET}' < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf

exec nginx -g "daemon off;"

