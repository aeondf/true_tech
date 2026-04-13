FROM nginx:alpine

# Copy static assets
COPY index.html         /usr/share/nginx/html/index.html
COPY brain.svg          /usr/share/nginx/html/brain.svg
COPY logo.svg           /usr/share/nginx/html/logo.svg
COPY js/                /usr/share/nginx/html/js/
COPY styles/            /usr/share/nginx/html/styles/

# nginx config: serve on port 80, proxy /v1/* to backend
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
