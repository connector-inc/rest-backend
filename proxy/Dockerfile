FROM nginx:latest

COPY nginx.conf /etc/nginx/conf.d/default.conf

WORKDIR /etc/nginx

RUN mkdir certificates
RUN openssl genrsa -out certificates/key.pem 2048
RUN openssl req -new -key certificates/key.pem -out certificates/csr.pem -subj "/C=VN/ST=Ho Chi Minh City/L=Ho Chi Minh City/O=Connector Inc./CN=www.connector.rocks/emailAddress=powoftech@gmail.com"
RUN openssl x509 -req -days 365 -in certificates/csr.pem -signkey certificates/key.pem -out certificates/cert.pem

